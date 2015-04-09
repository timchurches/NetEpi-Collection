#
#   The contents of this file are subject to the HACOS License Version 1.2
#   (the "License"); you may not use this file except in compliance with
#   the License.  Software distributed under the License is distributed
#   on an "AS IS" basis, WITHOUT WARRANTY OF ANY KIND, either express or
#   implied. See the LICENSE file for the specific language governing
#   rights and limitations under the License.  The Original Software
#   is "NetEpi Collection". The Initial Developer of the Original
#   Software is the Health Administration Corporation, incorporated in
#   the State of New South Wales, Australia.
#
#   Copyright (C) 2004-2011 Health Administration Corporation, Australian
#   Government Department of Health and Ageing, and others.
#   All Rights Reserved.
#
#   Contributors: See the CONTRIBUTORS file for details of contributions.
#

# Standard Library
import time
import operator
import re

# 3rd Party
from mx import DateTime

# Microcomputers have been around for more than 3 decades, yet here
# we are still writing our own date/time parsing routines. Sigh.

datestyle = None

class Error(Exception):
    pass


def fix_year(year):
    if year < 100:
        this_year = time.localtime().tm_year
        this_year_2digit = this_year % 100
        if year > this_year_2digit + 5:
            year -= 100;
        year += this_year - this_year_2digit
    return year

def to_fmt(spec):
    """
    Convert arbitrary YYYY-MM-DD hh:mm:ss style date specs into
    strptime-style formats.
    """
    spec = spec.replace('YYYY', '%Y')
    spec = spec.replace('YY', '%y')
    spec = spec.replace('MMM', '%b')
    spec = spec.replace('MM', '%m')
    spec = spec.replace('DD', '%d')
    spec = spec.replace('hh', '%H')
    spec = spec.replace('mm', '%M')
    spec = spec.replace('ss', '%S')
    return spec

class fmt_parser(object):

    __slots__ = 'fmt', 'fix_year', 'year_adj', 'year_cutoff'

    def __init__(self, fmt, age_years=False):
        self.fmt = to_fmt(fmt)
        self.fix_year = '%y' in self.fmt and age_years
        if self.fix_year:
            self.year_adj = DateTime.RelativeDate(years=100)
            self.year_cutoff = DateTime.today().year + 1

    def __call__(self, value):
        date = mx_parse_datetime.strptime(value, self.fmt)
        if self.fix_year and date.year > self.year_cutoff:
            return date - self.year_adj
        return date


def parse_date(date_str):
    """
    Parse a date in dd/mm/{yy}yy, dd-mm-{yy}yy, or ISO yyyy-mm-dd
    form, and returns a 3-tuple (year, month, day).

    Our century guessing is tuned for human lifespans - we accept
    2 digit dates up to 5 years in the future, anything else is
    considered to be the previous century.

    Raises Error if a parsing error occurs.
    """
    try:
        try:
            day, month, year = date_str.split('/')
        except ValueError:
            day, month, year = date_str.split('-')
        day, month, year = int(day), int(month), int(year)
        if day > 1000:
            # ISO date
            year, month, day = day, month, year
        else:
            if datestyle == 'MDY':
                day, month = month, day
            if year < 100:
                year = fix_year(year)
        return year, month, day
    except (ValueError, AttributeError):
        raise Error('could not parse date "%s"' % date_str)

def parse_time(time_str):
    """
    Parse a time in hh:mm or hh:mm:ss form, and returns a 3-tuple
    (hour, minute, second).

    Raises Error if a parsing error occurs.
    """
    try:
        fields = time_str.split(':', 2)
        if len(fields) < 3:
            # Just hours and minutes
            fields.append(0)
        else:
            # Remove microseconds if it's included
            fields[-1] = fields[-1].split('.')[0]
        hours, minutes, seconds = map(int, fields)
        if hours < 0 or hours > 23: raise ValueError
        if minutes < 0 or hours > 59: raise ValueError
        if seconds < 0 or seconds > 59: raise ValueError
        return hours, minutes, seconds
    except (ValueError, AttributeError):
        raise Error('could not parse time "%s" - use HH:MM:SS format' % time_str)

def parse_datetime(arg):
    try:
        try:
            p1, p2 = arg.split()
        except ValueError:
            return parse_date(arg) + (0,0,0)
        else:
            try:
                return parse_date(p1) + parse_time(p2)
            except Error:
                # Transposed?
                return parse_date(p2) + parse_time(p1)
    except Error:
        raise Error('could not parse date/time "%s"' % arg)


# We really just want to subclass mx.DateTime.DateTime, but it's an old-style
# extension type, so we have to proxy instead - this causes a fair bit of
# phutzing around overloading operators.
class DatetimeFormat(object):
    __slots__ = '_value'

    def __str__(self):
        if self._value is None:
            return ''
        else:
            return self.strftime(self.format)

    def __repr__(self):
        if self._value is None:
            value = None
        else:
            value = str(self)
        return '<%s.%s %s>' % (self.__class__.__module__,
                               self.__class__.__name__,
                               value)
    def strptime(cls, t, fmt):
        try:
            return cls(DateTime.strptime(t, fmt))
        except DateTime.Error, e:
            raise Error('date/time %r does not match format %r' % (t, fmt))
        except ValueError, e:
            raise Error(str(e))
    strptime = classmethod(strptime)

    def mx(self):
        return self._value

    def __getattr__(self, a):
        return getattr(self._value, a)

    def __setattr__(self, a, v):
        if a == '_value':
            object.__setattr__(self, a, v)
        else:
            setattr(self._value, a, v)

    def __getstate__(self):
        return self._value,

    def __setstate__(self, state):
        self._value, = state

    def __nonzero__(self):
        return self._value is not None

    def __add__(self, other):
        return self._value + other

    def __sub__(self, other):
        return self._value - other

    def __radd__(self, other):
        return other + self._value

    def __rsub__(self, other):
        return other - self._value

    def _ops(self, op, other):
        if isinstance(other, basestring):
            try:
                other = self.__class__(other)
            except Error:
                pass
        if isinstance(other, DatetimeFormat):
            other = other._value
        if self._value is None or other is None:
            return op(self._value, other)
        try:
            return op(DateTime.cmp(self._value, other, self.precision), 0)
        except TypeError, e:
            raise TypeError('%s: %r vs %r' % (e, self._value, other))

    def __eq__(self, other):
        return self._ops(operator.eq, other)

    def __ne__(self, other):
        return self._ops(operator.ne, other)

    def __gt__(self, other):
        return self._ops(operator.gt, other)

    def __ge__(self, other):
        return self._ops(operator.ge, other)

    def __lt__(self, other):
        return self._ops(operator.lt, other)

    def __le__(self, other):
        return self._ops(operator.le, other)

class mx_parse_date(DatetimeFormat):
    __slots__ = ()
    format = None
    help = None
    precision = 24 * 60 * 60 - 1

    def __init__(self, arg):
        if isinstance(arg, DateTime.DateTimeType):
            self._value = arg
        elif isinstance(arg, DatetimeFormat):
            self._value = arg._value
        elif not arg:
            self._value = None
        else:
            try:
                self._value = DateTime.Date(*parse_datetime(arg)[:3])
            except Error:
                raise Error('could not parse date "%s"' % arg)
            except DateTime.Error:
                raise Error('invalid date "%s"' % arg)
    # python 2.2.1 overrides the normal MRO for these methods as a safety
    # measure to prevent accidents with it's incomplete slots implementation.
    __getstate__ = DatetimeFormat.__getstate__
    __setstate__ = DatetimeFormat.__setstate__

class mx_parse_time(DatetimeFormat):
    __slots__ = ()
    format = '%H:%M:%S'
    help = 'hh:mm(:ss)'
    precision = 1

    def __init__(self, arg):
        if isinstance(arg, DatetimeFormat):
            arg = arg._value
        if isinstance(arg, DateTime.DateTimeDeltaType):
            self._value = arg
        elif isinstance(arg, DateTime.DateTimeType):
            self._value = DateTime.DateTimeDelta(0, arg.hour, arg.minute, 
                                                    arg.second)
        elif not arg:
            self._value = None
        else:
            try:
                self._value = DateTime.DateTimeDelta(0, *parse_time(arg))
            except DateTime.Error:
                raise Error('invalid time "%s"' % arg)
        if self._value is not None and self._value.day:
            raise Error('invalid time %r' % arg)
    __getstate__ = DatetimeFormat.__getstate__
    __setstate__ = DatetimeFormat.__setstate__

class mx_parse_datetime(DatetimeFormat):
    __slots__ = ()
    format = None
    help = None
    precision = 1

    def __init__(self, arg):
        if isinstance(arg, DateTime.DateTimeType):
            self._value = arg
        elif isinstance(arg, DatetimeFormat):
            self._value = arg._value
        elif not arg:
            self._value = None
        else:
            try:
                self._value = DateTime.DateTime(*parse_datetime(arg))
            except DateTime.Error:
                raise Error('invalid date/time "%s"' % arg)
    def date(self):
        return mx_parse_date(self)
    def time(self):
        return mx_parse_time(self)
    __getstate__ = DatetimeFormat.__getstate__
    __setstate__ = DatetimeFormat.__setstate__

def is_later_than(date_a, date_b):
    if not date_a or not date_b:
        return False
    return date_a > date_b

def now():
    return mx_parse_datetime(DateTime.now())

def relative(date, ref=None):
    if isinstance(date, DateTime.DateTimeDeltaType):
        delta = date
    else:
        if not date:
            return ''
        if ref is None:
            ref = now()
        delta = date - ref
    past = delta < 0
    if past:
        delta = -delta
    if delta.days > 400:
        value = '%.0f years' % (delta.days / 365.24)
    elif delta.days > 40:
        value = '%.0f months' % (delta.days / 30.44)
    elif delta.days > 13:
        value = '%.0f weeks' % (delta.days / 7)
    elif delta.days >= 2:
        value = '%.0f days' % delta.days
    elif delta.hours >= 2:
        value = '%.0f hours' % delta.hours
    elif round(delta.minutes) > 1:
        value = '%.0f minutes' % delta.minutes
    elif round(delta.minutes):
        value = '1 minute'
    else:
        value = 'less than a minute'
    if past:
        return value + ' ago'
    else:
        return 'in ' + value

days_of_week = {
    'monday': DateTime.Monday,
    'tuesday': DateTime.Tuesday,
    'wednesday': DateTime.Wednesday,
    'thursday': DateTime.Thursday,
    'friday': DateTime.Friday,
    'saturday': DateTime.Saturday,
    'sunday': DateTime.Sunday,
}

def to_discrete(date, ref=None):
    if isinstance(date, DateTime.DateTimeDeltaType):
        delta = date
    else:
        if date is None:
            return ''
        if ref is None:
            ref = now()
        delta = date - ref
    past = delta < 0
    if past:
        delta = -delta
        raise ValueError('negative relative dates not currently supported')
    if not delta:
        return 'now'
    elif delta.days < 1:
        value = '%.0fh' % delta.hours
    elif delta.days < 2:
        value = 'tomorrow'
    elif round(delta.days) == 7:
        value = 'week'
    elif round(delta.days) == 14:
        value = 'fortnight'
    elif delta.days < 30:
        value = '%.0fd' % delta.days
    elif delta.days <= 31:
        value = 'month'
    elif 88 < delta.days <= 92:
        value = 'quarter'
    else:
        value = '%.0fm' % (delta.days / 30.44)
    return value


rel_date_re = re.compile(
     '\s*'                                      # Ignore leading whitespace
     '(now|tomorrow|yesterday'
     '|monday|tuesday|wednesday|thursday|friday|saturday|sunday'
     '|(\d*|one|two|three|four|five|six|seven|eight|nine|ten)'  # Count
      '\s*'
      '(h|d|w|m|y'                                              # Units
      '|minutes?|hours?'
      '|days?|weeks?|wks?|fortnights?|quarters?|months?|yrs?|years?'
      '|/\d+'
      ')'
      '(\s*ago)?'                                               # Optional
     ')'
     '\s*'                                      # Ignore trailing whitespace
     '$'
    )

count_map = {
    '': 1,
    None: 1,
    'one': 1,
    'two': 2,
    'three': 3,
    'four': 4,
    'five': 5,
    'six': 6,
    'seven': 7,
    'eight': 8,
    'nine': 9,
    'ten': 10,
}

def parse_discrete(relative, ref=None, past=False):
    if not relative:
        return None
    match = rel_date_re.match(relative.lower())
    if match:
        daystart = dict(hour=7, minute=0, second=0)
        if ref is None:
            t = DateTime.now()
        else:
            t = ref
        word, count, units, direction = match.groups()
        count = count_map.get(count, count)
        if word == 'now':
            return mx_parse_datetime(t)
        elif word in days_of_week:
            day_of_week = days_of_week[word]
            if day_of_week > t.day_of_week:
                offs = DateTime.RelativeDate(weekday=(day_of_week, 0), **daystart)
            else:
                offs = DateTime.RelativeDate(weekday=(day_of_week, 0), days=7, **daystart)
        elif word == 'tomorrow':
            offs = DateTime.RelativeDate(days=1, **daystart)
        elif word == 'yesterday':
            offs = DateTime.RelativeDate(days=-1, **daystart)
        elif units.startswith('minute'):
            offs = DateTime.RelativeDate(minutes=int(count))
        elif units[0] == 'h' or units == '/24':
            offs = DateTime.RelativeDate(hours=int(count))
        elif units[0] == 'd' or units == '/7':
            offs = DateTime.RelativeDate(days=int(count))
        elif units[0] == 'm' or units == '/12':
            offs = DateTime.RelativeDate(months=int(count), **daystart)
        elif units[0] == 'w' or units == '/52':
            offs = DateTime.RelativeDate(weeks=int(count), **daystart)
        elif units[0] == 'y':
            offs = DateTime.RelativeDate(years=int(count), **daystart)
        elif units.startswith('fortnight'):
            offs = DateTime.RelativeDate(weeks=int(count)*2, **daystart)
        elif relative == 'quarter':
            offs = DateTime.RelativeDate(months=int(count)*3, **daystart)
        if (direction and direction.lstrip() == 'ago') or past:
            return mx_parse_datetime(t - offs)
        else:
            return mx_parse_datetime(t + offs)
    else:
        return mx_parse_datetime(relative)

def near(a, b, range=60):
    if not a or not b:
        return False
    delta = a - b
    return abs(delta.seconds) < range


iso_date_re = re.compile(r'(\d{4}-\d{2}-\d{2})')

def date_fix(text):
    """
    Replace ISO dates in /text/ with the current date convention
    """
    if mx_parse_date.format != '%Y-%m-%d':
        splits = iso_date_re.split(text)
        for i in xrange(1, len(splits), 2):
            try:
                splits[i] = str(mx_parse_date(splits[i]))
            except Error:
                pass
        text = ''.join(splits)
    return text


def set_date_style(new_datestyle):
    global datestyle

    old_datestyle = datestyle
    if datestyle != new_datestyle:
        if new_datestyle == 'DMY':
            format = '%d/%m/%Y'
            help = 'dd/mm/yyyy'
        elif new_datestyle == 'MDY':
            format = '%m/%d/%Y'
            help = 'mm/dd/yyyy'
        elif new_datestyle == 'ISO':
            format = '%Y-%m-%d'
            help = 'yyyy-mm-dd'
        else:
            raise Error('Unknown date format %r' % format)
        datestyle = new_datestyle
        mx_parse_date.format = format
        mx_parse_date.help = help
        mx_parse_datetime.format = format + ' ' + mx_parse_time.format
        mx_parse_datetime.help = help + ' ' + mx_parse_time.help
    return old_datestyle

set_date_style('DMY')
