import datetime
import re

from django.conf import settings
from django.forms.utils import to_current_timezone
from django.forms.widgets import MultiWidget
from django.forms.widgets import Select
from django.forms.widgets import TextInput
from django.forms.widgets import Widget
from django.utils.formats import get_format


class DateWidget(TextInput):
    input_type = 'date'
    template_name = 'django/forms/widgets/text.html'


class SelectTimeWidget(Widget):
    """
    A widget that splits time input into 2 <select> boxes.

    This also serves as an example of a Widget that has more than one HTML
    element and hence implements value_from_datadict.
    """
    none_value = ('', '---')
    hour_field = '%s_hour'
    minute_field = '%s_minute'
    template_name = 'calendar/forms/widgets/select_time.html'
    input_type = 'select'
    select_widget = Select
    time_re = re.compile(r'(\d\d?):(\d\d?)$')

    def __init__(self, attrs=None, hours=None, minutes=None, empty_label=None):
        self.attrs = attrs or {}

        # Optional list or tuple of years to use in the "year" select box.
        if hours:
            self.hours = hours
        else:
            self.hours = {str(x): x for x in range(0, 25)}

        # Optional dict of months to use in the "month" select box.
        if minutes:
            self.minutes = minutes
        else:
            self.minutes = {str(x): x for x in range(0, 60)}

        # Optional string, list, or tuple to use as empty_label.
        if isinstance(empty_label, (list, tuple)):
            if not len(empty_label) == 2:
                raise ValueError('empty_label list/tuple must have 2 elements.')

            self.hour_none_value = ('', empty_label[0])
            self.minute_none_value = ('', empty_label[1])
        else:
            if empty_label is not None:
                self.none_value = ('', empty_label)

            self.hour_none_value = self.none_value
            self.minute_none_value = self.none_value

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        time_context = {}
        hour_choices = [(i, str(i)) for i in self.hours]
        if not self.is_required:
            hour_choices.insert(0, self.hour_none_value)
        hour_name = self.hour_field % name
        time_context['hour'] = self.select_widget(attrs, choices=hour_choices).get_context(
            name=hour_name,
            value=context['widget']['value']['hour'],
            attrs={**context['widget']['attrs'], 'id': 'id_%s' % hour_name},
        )
        minute_choices = list(self.minutes.items())
        if not self.is_required:
            minute_choices.insert(0, self.minute_none_value)
        minute_name = self.minute_field % name
        time_context['minute'] = self.select_widget(attrs, choices=minute_choices).get_context(
            name=minute_name,
            value=context['widget']['value']['minute'],
            attrs={**context['widget']['attrs'], 'id': 'id_%s' % minute_name},
        )
        subwidgets = context['widget'].get('subwidgets', [])
        for field in self._parse_time_fmt():
            subwidgets.append(time_context[field]['widget'])
        context['widget']['subwidgets'] = subwidgets
        return context

    def format_value(self, value):
        """
        Return a dict containing the year, month, and day of the current value.
        Use dict instead of a datetime to allow invalid dates such as February
        31 to display correctly.
        """
        hour, minute = None, None
        if isinstance(value, (datetime.time, datetime.datetime)):
            hour, minute = value.hour, value.minute
        elif isinstance(value, str):
            match = self.time_re.match(value)
            if match:
                # Convert any zeros in the date to empty strings to match the
                # empty option value.
                hour, minute = [int(val) or '' for val in match.groups()]
            elif settings.USE_L10N:
                input_format = get_format('TIME_INPUT_FORMATS')[0]
                try:
                    d = datetime.datetime.strptime(value, input_format)
                except ValueError:
                    pass
                else:
                    hour, minute = d.hour, d.minute
        return {'hour': hour, 'minute': minute}

    @staticmethod
    def _parse_time_fmt():
        """
        This method is proposed and implemented in SelectDateWidget such
        that django's settings.DATE_FORMAT can define the order of the widgets,
        however it's not implemented here, we just hard-code the order.
        """
        return ('hour', 'minute')

    def id_for_label(self, id_):
        for first_select in self._parse_time_fmt():
            return '%s_%s' % (id_, first_select)
        return '%s_minute' % id_

    def value_from_datadict(self, data, files, name):
        h = data.get(self.hour_field % name)
        m = data.get(self.minute_field % name)
        if h == m == '':
            return None
        if h is not None and m is not None:
            if settings.USE_L10N:
                try:
                    return datetime.time(int(h), int(m))
                except ValueError:
                    pass
            # Return pseudo-ISO times with zeros for any unselected values,
            # e.g. '0:30'.
            return '%s:%s' % (h or 0, m or 0)
        return data.get(name)

    def value_omitted_from_data(self, data, files, name):
        return not any(
            ('{}_{}'.format(name, interval) in data)
            for interval in ('hour', 'minute')
        )


class SplitDateTimeWidget(MultiWidget):
    """
    A widget that splits datetime input into two <input type="text"> boxes.
    """
    supports_microseconds = False
    template_name = 'django/forms/widgets/splitdatetime.html'

    def __init__(self, attrs=None, time_format=None, date_attrs=None, time_attrs=None):
        widgets = (
            DateWidget(),
            SelectTimeWidget(),
        )
        super().__init__(widgets)

    def decompress(self, value):
        if value:
            value = to_current_timezone(value)
            return [value.date(), value.time()]
        return [None, None]
