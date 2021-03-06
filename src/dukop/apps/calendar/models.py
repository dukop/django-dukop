import os
import random
import string
import uuid
from builtins import staticmethod
from functools import lru_cache

from django.contrib.sites.models import Site
from django.db import models
from django.urls.base import reverse
from django.utils.functional import cached_property
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from dukop.apps.calendar.utils import display_datetime
from dukop.apps.calendar.utils import display_time
from sorl.thumbnail import get_thumbnail

from . import utils


def image_upload_to(instance, filename):
    ext = filename.split(".")[-1]
    filename = "%s.%s" % (uuid.uuid4(), ext)
    return os.path.join("uploads/events", filename)


def sluggify_instance(instance, ModelClass, name_field, slug_field):
    """
    Auto-populates a slug field if it isn't filled in.
    """
    if not instance.pk and not getattr(instance, slug_field, None):
        proposal = slugify(getattr(instance, name_field))[:50]

        def _proposal_exists():
            return ModelClass.objects.filter(**{slug_field: proposal}).exists()

        proposal_exists = _proposal_exists()
        while proposal_exists:
            to_append = "".join(
                random.choice(string.ascii_uppercase + string.digits) for _ in range(10)
            )
            proposal = proposal[:40] + to_append
            proposal_exists = _proposal_exists()
        setattr(instance, slug_field, proposal)


class EventManager(models.Manager):
    def get_queryset(self):
        return (
            super().get_queryset().prefetch_related("times").prefetch_related("images")
        )


class EventTimeQuerySet(models.QuerySet):
    def future(self):
        now = utils.get_now()
        return self.filter(start__gte=now)


class EventTimeManager(models.Manager):
    def get_queryset(self):
        return EventTimeQuerySet(self.model, using=self._db)

    def future(self):
        return self.get_queryset().future()


class Sphere(models.Model):
    """
    Spheres are local versions of a site containing sets of events. Over time,
    they may change and define their own themes, priorities etc. We don't know.
    """

    name = models.CharField(max_length=255)

    slug = models.SlugField(
        null=True,
        blank=True,
        verbose_name=_("slug"),
        help_text=_("The part of a URL that is displayed in dukop.dk/sphere/<slug>/"),
    )

    default = models.BooleanField(default=False)

    admins = models.ManyToManyField(
        "users.User",
        limit_choices_to={"is_staff": True},
    )

    class Meta:
        ordering = ("-default", "name")
        verbose_name = _("Sphere")
        verbose_name_plural = _("Spheres")

    def save(self, *args, **kwargs):
        sluggify_instance(self, Sphere, "name", "slug")
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    @staticmethod
    def get_default():
        """
        This can be cached in-memory insofar that we don't do any more funky
        stuff with the Spheres, like related querysets etc.
        """
        try:
            return Sphere.objects.get(default=True)
        except Sphere.DoesNotExist:
            return Sphere.objects.create(
                name="Auto-created sphere", slug="auto", default=True
            )

    @staticmethod
    @cached_property
    def get_default_cached():
        """
        This can be cached in-memory insofar that we don't do any more funky
        stuff with the Spheres, like related querysets etc.
        """
        return Sphere.get_default()

    @staticmethod
    def get_by_id_or_default(sphere_id=None):
        """
        Fetches a sphere by its ID or returns the default sphere
        """
        if not sphere_id:
            return Sphere.get_default()
        try:
            return Sphere.get_by_id_or_default(sphere_id=sphere_id)
        except Sphere.DoesNotExist:
            return Sphere.get_default()

    @staticmethod
    @lru_cache(maxsize=128)
    def get_by_id_or_default_cached(sphere_id=None):
        """
        Fetches a sphere by its ID or returns the default sphere
        """
        return Sphere.get_by_id_or_default(sphere_id=sphere_id)


class Event(models.Model):
    """
    Recurrence:

    An event can be ascribed as many EventTime instances as necessary to express
    recurrence.

    Once in a while, we need to maintain this information, though. But we do not
    auto-create EventTime objects way into the future - there is no need for
    that.

    Calendars have "Edit this occurrence" or "Edit all occurrences"

    Likewise, we also need a way for events that have occurred to remain
    untouched, while future events can be edited.

    https://github.com/bmoeskau/Extensible/blob/master/recurrence-overview.md
    """

    spheres = models.ManyToManyField(
        Sphere,
        blank=True,
    )

    name = models.CharField(
        max_length=255,
        verbose_name=_("name"),
    )
    short_description = models.TextField(
        blank=True,
        verbose_name=_("short description"),
        help_text=_(
            "A special short version of the event description, leave blank to auto-generate. Text-only, no Markdown."
        ),
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("description"),
        help_text=_(
            "Enter details, which will be displayed on the event's own page. You can use Markdown."
        ),
    )

    slug = models.SlugField(
        null=True,
        blank=True,
        verbose_name=_("slug"),
        help_text=_("The part of a URL that is displayed in dukop.dk/event/<slug>/"),
    )

    host = models.ForeignKey(
        "users.Group",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="events",
        help_text=_(
            "A group may host an event and be displayed as the author of the event text."
        ),
    )

    featured = models.BooleanField(default=False)
    published = models.BooleanField(default=True)

    is_cancelled = models.BooleanField(default=False)

    venue_name = models.CharField(
        max_length=255,
        verbose_name=_("venue name"),
        blank=True,
        null=True,
        help_text=_("If left blank, will be copied from host group"),
    )
    street = models.CharField(
        max_length=255,
        verbose_name=_("street"),
        blank=True,
        null=True,
        help_text=_("If left blank, will be copied from host group"),
    )
    city = models.CharField(
        max_length=255,
        verbose_name=_("city"),
        blank=True,
        null=True,
        help_text=_("If left blank, will be copied from host group"),
    )
    zip_code = models.CharField(
        verbose_name=_("zip code"),
        blank=True,
        null=True,
        max_length=16,
        help_text=_("If left blank, will be copied from host group"),
    )

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    owner_user = models.ForeignKey(
        "users.User",
        verbose_name=_("owner (user)"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="owned_events",
    )
    owner_group = models.ForeignKey(
        "users.Group",
        verbose_name=_("owner (group)"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="owned_events",
    )

    edit_secret = models.CharField(
        max_length=255,
        verbose_name=_("edit secret"),
        blank=True,
        null=True,
        editable=False,
    )

    view_secret = models.CharField(
        max_length=255,
        verbose_name=_("view secret"),
        blank=True,
        null=True,
        editable=False,
    )

    objects = EventManager()

    class Meta:
        verbose_name = _("Event")

    def save(self, *args, **kwargs):
        """
        Auto-populates the slug field if it isn't filled in.
        """
        sluggify_instance(self, Event, "name", "slug")
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def share_link(self):
        current_site = Site.objects.get_current()
        domain = current_site.domain
        return "https://{}{}".format(
            domain, reverse("calendar:event_detail", kwargs={"pk": self.pk})
        )


class EventTime(models.Model):
    """
    Allows an event to take place at many different times
    """

    event = models.ForeignKey(Event, related_name="times", on_delete=models.CASCADE)
    start = models.DateTimeField(
        verbose_name=_("start"),
    )
    end = models.DateTimeField(
        verbose_name=_("end"),
        blank=True,
        null=True,
    )
    comment = models.CharField(
        max_length=255,
        verbose_name=_("comment"),
        help_text=_("Leave blank and nothing will be shown to readers"),
        blank=True,
        null=True,
    )
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    is_cancelled = models.BooleanField(default=False)

    interval_auto = models.BooleanField(
        default=False,
        verbose_name=_("automatic recurrence"),
        help_text=_(
            "If true, this interval is currently maintained automatically and "
            "has not been rescheduled. If the interval is edited, it may be "
            "changed automatically"
        ),
    )

    objects = EventTimeManager()

    class Meta:
        verbose_name = _("Event time")
        ordering = ("start", "end")

    def __str__(self):
        representation = display_datetime(self.start)
        if self.end:
            if self.end.date() == self.start.date():
                representation += " - {}".format(display_time(self.end.time()))
            else:
                representation += " - {}".format(display_datetime(self.end))
        return representation


class EventUpdate(models.Model):
    """
    An update can be posted by event owners and will be visible on the event
    page for users to see.
    """

    event = models.ForeignKey(Event, related_name="updates", on_delete=models.CASCADE)

    description = models.TextField(
        blank=True,
        verbose_name=_("description"),
    )

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Event update")
        ordering = ("created",)


class EventImage(models.Model):

    event = models.ForeignKey(Event, related_name="images", on_delete=models.CASCADE)
    image = models.ImageField(
        verbose_name=_("image"),
        help_text=_(
            "Allowed formats: JPEG, PNG, GIF. Please upload high resolution (>1000 pixels wide)."
        ),
        upload_to=image_upload_to,
    )
    priority = models.PositiveSmallIntegerField(
        default=0, help_text=_("0=first, 1=second etc.")
    )
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("priority",)

    def thumb(self, width=100, height=75):
        try:
            return get_thumbnail(
                self.image.file,
                "{}x{}".format(width, height),
                crop="center",
                quality=90,
            )
        except OSError as e:
            if "RGBA" in str(e):
                return get_thumbnail(
                    self.image.file,
                    "{}x{}".format(width, height),
                    crop="center",
                    format="PNG",
                )
            else:
                raise


class EventLink(models.Model):
    """
    Links have automatically generated labels, in this way we can
    potentially translate them or make them consistent. For instance,
    we can make Facebook links display with a warning.
    """

    event = models.ForeignKey(Event, related_name="links", on_delete=models.CASCADE)
    link = models.URLField(blank=True, null=True, max_length=2048)
    priority = models.PositiveSmallIntegerField(
        default=0, help_text=_("0=first, 1=second etc.")
    )
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)


class EventInterval(models.Model):
    """
    Inspired by RRULE for iCal format:

    https://www.kanzaki.com/docs/ical/rrule.html
    """

    event = models.ForeignKey(Event, related_name="intervals", on_delete=models.CASCADE)

    weekday = models.ForeignKey("Weekday", on_delete=models.CASCADE)

    every_week = models.BooleanField(default=False)
    biweekly_even = models.BooleanField(default=False)
    biweekly_odd = models.BooleanField(default=False)
    first_week_of_month = models.BooleanField(default=False)
    second_week_of_month = models.BooleanField(default=False)
    third_week_of_month = models.BooleanField(default=False)
    last_week_of_month = models.BooleanField(default=False)

    starts = models.DateTimeField(null=True, blank=True)
    ends = models.DateTimeField(null=True, blank=True)

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)


class Weekday(models.Model):

    name = models.CharField(
        max_length=255,
        verbose_name=_("name"),
    )
    number = models.PositiveSmallIntegerField(default=0, unique=True)


class OldEventSync(models.Model):

    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    old_fk = models.PositiveIntegerField()
    is_series = models.BooleanField()

    class Meta:
        unique_together = ("old_fk", "is_series")
