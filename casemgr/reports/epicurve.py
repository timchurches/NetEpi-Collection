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

# NOTE - this module does not include logic for the case-contact visualisation.

import sys, os
import math
import textwrap
import itertools
try:
    set
except NameError:
    from sets import Set as set

from mx.DateTime import DateTimeType, DateTimeDelta, RelativeDateTime, Monday

from cocklebur import datetime, trafficlight, utils

from casemgr import globals
from casemgr.reports.common import *

import config

class Error(globals.Error): pass


def import_pylab():
    """
    We defer loading matplotlib until it's actually needed as it can
    take several seconds to import, and it may not be available at all.
    """
    global matplotlib, pylab
    if 'matplotlib' not in sys.modules:
        # Problem: matplotlib wants to load it's font cache (pickle) and rc
        # files from a writable directory. This is potentially a security
        # problem in a CGI app, but we have no solution at this time.
        homedir = os.path.expanduser('~')
        mpldir = os.path.join(homedir, '.matplotlib')
        if not os.access(mpldir, os.W_OK) and not os.access(homedir, os.W_OK):
            mpldir = os.path.join(config.scratchdir, '.matplotlib')
        os.environ['MPLCONFIGDIR'] = mpldir
        if not os.path.exists(mpldir):
            os.mkdir(mpldir)
        try:
            import matplotlib
            matplotlib.use('Agg')
            import pylab
        except ImportError, e:
            raise Error('matplotlib not available (%s)?' % (e))

def pad_axis(ax, axis, amount=0.01):
    lower, upper = getattr(ax, 'get_%slim' % axis)()
    abit = (upper - lower) * amount
    getattr(ax, 'set_%slim' % axis)(lower - abit, upper + abit)

def same_scale(axis, *axes):
    lower = []
    upper = []
    for ax in axes:
        l, u = getattr(ax, 'get_%slim' % axis)()
        lower.append(l)
        upper.append(u)
    l = min(lower)
    u = max(upper)
    for ax in axes:
        getattr(ax, 'set_%slim' % axis)(l, u)


class CondCol:
    def __init__(self, data, optionexpr=None):
        self.data = map(str, data)
        values = set(self.data)
        self.order = []
        self.labels = {}
        self.order_labels = []
        if optionexpr is not None:
            for v, l in optionexpr:
                if v in values:
                    self.order.append(v)
                    self.labels[v] = str(l)
                    self.order_labels.append((v, str(l)))
        missing = list(values - set(self.order))
        missing.sort()
        for v in missing:
            self.order.append(v)
            self.labels[v] = str(v)
            self.order_labels.append((v, str(v)))


class EpiCurve:
    max_bins = 400              # Limit number of bars on chart
    max_ticks = 40              # Approx limit on readable X tickmarks

    def __init__(self, title=None):
        import_pylab()
        self.dates = None       # Event dates (list of DateTime)
        self.date_label = None
        self.lower_dates = None
        self.lower_date_label = None
        self.stack = None       # If stacking, a CondCol
        self.first = None       # First date (DateTime)
        self.last = None        # Last date (DateTime)
        self.span = None        # Span of dates (DateTimeDelta)
        self.n_bins = None      # Number of bins (int)
        self.bin_span = None    # Span of each bin (DateTimeDelta)
        self.title = title

    def calc_span(self):
        """
        Find the first and last date, then round them down and up
        (respecively).
        """
        assert self.dates
        if self.lower_dates:
            dates = filter(None, self.dates + self.lower_dates)
        else:
            dates = filter(None, self.dates)
        if not dates:
            raise Error('No date records found')
        start_of_day = RelativeDateTime(hour=0, minute=0, second=0)
        start_of_next_day = RelativeDateTime(days=1, hour=0, minute=0, second=0)
        self.first = min(dates) + start_of_day
        self.last = max(dates) + start_of_next_day
        self.span = self.last - self.first
        assert isinstance(self.first, DateTimeType)
        assert isinstance(self.last, DateTimeType)

    def set_dates(self, dates, date_label=None):
        self.dates = dates
        if date_label is not None:
            self.date_label = date_label

    def set_lower_dates(self, dates, date_label=None):
        self.lower_dates = dates
        if date_label is not None:
            self.lower_date_label = date_label

    def set_stack(self, data, optionexpr, 
                  label=None, ratios=False, suppress=None):
        assert len(self.dates) == len(data)
        self.stack_label = label
        self.stack = CondCol(data, optionexpr)
        self.stack_ratios = ratios
        self.stack_suppress = suppress

    def calc_bin_span(self, days):
        """
        Given a desired bin span in days, calculate number of bins that
        comes closest.
        """
        assert self.span
        if (days % 7) == 0:
            # If user asked for a bin width that is a multiple of 7 days, shift
            # bins to align with weeks.
            self.first += RelativeDateTime(weekday=(Monday,0))
            self.span = self.last - self.first
        self.bin_span = DateTimeDelta(days)
        self.n_bins = int(math.ceil(self.span / self.bin_span))
        if self.n_bins > self.max_bins:
            raise Error('Too many bins (%d, maximum is %d) - make bins bigger, or limit date range' % (self.n_bins, self.max_bins))

    def set_n_bins(self, n_bins):
        """
        Given a desired number of bins, calculate the closest possible number
        of bins.
        """
        self.calc_span()
        days = round((self.span / n_bins).days)
        if days < 1:
            days = 1
        self.calc_bin_span(days)

    def set_n_days(self, days):
        self.calc_span()
        self.calc_bin_span(days)

    def calc_tick_labels(self):
        """
        Generate ticks & tick labels. If the density of the ticks looks like
        it will be too high, we start skipping ticks (tick_stride).
        """
        assert self.n_bins
        assert self.bin_span
        tick_labels = []
        ticks = []
        tick_stride = int(math.ceil(self.n_bins / float(self.max_ticks)))
        tick = self.first
        if self.bin_span.days == 1:
            adj = 0
            if tick_stride == 1:
                step = RelativeDateTime(days=1)
            elif tick_stride <= 7:
                step = RelativeDateTime(weeks=1, weekday=(Monday,0))
                tick += step
            elif tick_stride <= 14:
                step = RelativeDateTime(weeks=2, weekday=(Monday,0))
                tick += RelativeDateTime(weeks=1, weekday=(Monday,0))
            else:
                step = RelativeDateTime(day=1, months=1)
                tick += step
        else:
            adj = -0.5
            step = self.bin_span * tick_stride
        while tick < self.last:
            bin = (tick - self.first) / self.bin_span
            ticks.append(bin+adj)
            tick_labels.append(str(datetime.mx_parse_date(tick)))
            tick += step
        return ticks, tick_labels

    def info(self, msgs):
        n_recs = len(self.dates)
        info = ['%d records' % n_recs]
        date_missing = sum([not date for date in self.dates])
        if date_missing:
            info.append(', %d missing %s' % (date_missing, self.date_label))
        if self.lower_dates:
            lower_date_missing = sum([not date for date in self.lower_dates])
            if lower_date_missing:
                info.append(', %d missing %s' % (lower_date_missing, 
                                                 self.lower_date_label))
        else:
            lower_date_missing = 0
        if (date_missing == n_recs and 
                (not self.lower_dates or lower_date_missing == n_recs)):
            lvl = 'err'
            info.insert(0, 'Error - ')
        elif date_missing or lower_date_missing:
            lvl = 'warn'
        else:
            lvl = 'info'
        msgs.msg(lvl, ''.join(info))

    def date_bin(self, dates):
        """
        Do the date binning
        """
        assert self.n_bins
        assert self.bin_span
        bins = pylab.zeros(self.n_bins)
        for date in dates:
            if date is not None:
                bin = int((date - self.first) / self.bin_span)
                bins[bin] += 1
        return bins

    def strata_date_bin(self, dates, *condcols):
        """
        Do date binning with strata.

        Strata is a list of tuples. There must be a tuple for each date entry.
        """
        assert self.n_bins
        assert self.bin_span
        cols = [cc.data for cc in condcols]
        rows = zip(*cols)
        strata_bins = {}
        for c in set(rows):
            strata_bins[c] = pylab.zeros(self.n_bins)
        for d, c in itertools.izip(dates, rows):
            if d is not None:
                bin = int((d - self.first) / self.bin_span)
                strata_bins[c][bin] += 1
        return strata_bins

    def strata_ratios(self, strata_bins):
        values, bins = zip(*strata_bins.iteritems())
        matrix = pylab.array(bins, dtype='d')
        ratios = matrix * 100.0 / pylab.add.reduce(matrix)
        return dict(zip(values, ratios))

    def graph(self, outfmt, filename=None):
        def wrap(title):
            if title:
                return textwrap.fill(title, 30)
        def _graph(ax, dates, legend=True):
            ax.xaxis.set_ticks(ticks)
            pylab.setp(ax.xaxis.get_ticklabels(), rotation=90, fontsize=8)
            ax.xaxis.set_major_formatter(pylab.FixedFormatter(tick_labels))
            ylocator = pylab.MaxNLocator(10, steps=[1,2,5,10],integer=1)
            ax.yaxis.set_major_locator(ylocator)
            ax.yaxis.grid(1)
            if self.stack:
                bottom = pylab.zeros(self.n_bins)
                legend_handles = []
                legend_labels = []
                strata_bins = self.strata_date_bin(dates, self.stack)
                if self.stack_ratios:
                    strata_bins = self.strata_ratios(strata_bins)
                for n, (v, l) in enumerate(self.stack.order_labels):
                    if self.stack_suppress and v in self.stack_suppress:
                        continue
                    bins = strata_bins[(v,)]
                    handles = pylab.bar(x, bins, bottom=bottom, 
                                        width=1.0,
                                        align='center', 
                                        color=colors[n])
                    legend_handles.append(handles[0])
                    legend_labels.append(wrap(l))
                    bottom += bins
                if legend:
                    l = pylab.legend(legend_handles, legend_labels, loc=0,
                                     prop=dict(size=8),
                                     title=wrap(self.stack_label))
                    pylab.setp(l.get_title(), fontsize=9)
#                    pylab.setp(l.get_texts(), fontsize=8)
                if self.stack_ratios:
                    ax.set_ylim(0, 100)
            else:
                bins = self.date_bin(dates)
                pylab.bar(x, bins, width=1.0, color='#bbbbff', align='center')
            pad_axis(ax, 'x')
            pad_axis(ax, 'y')

        ticks, tick_labels = self.calc_tick_labels()
        x = pylab.arange(self.n_bins)
        pylab.figure(figsize=(10,6), dpi=100, facecolor='w')
        colors = None
        ylabel = 'Count'
        if self.stack:
            colors = trafficlight.make_n_colors(len(self.stack.order))
            if self.stack_ratios:
                ylabel = 'Ratio'
        if self.lower_dates:
            lax = pylab.axes([0.1, 0.2, .8, 0.34], frameon=False)
            _graph(lax, self.lower_dates, False)
            pylab.ylabel(wrap(self.lower_date_label + ' ' + ylabel), fontsize=9)

            ax = pylab.axes([0.1, 0.58, .8, 0.34], frameon=False)
            _graph(ax, self.dates)
            ax.xaxis.set_major_formatter(pylab.NullFormatter())
            pylab.ylabel(wrap(self.date_label + ' ' + ylabel), fontsize=9)
            same_scale('x', lax, ax)
            #same_scale('y', lax, ax)
        else:
            ax = pylab.axes([0.1, 0.2, .8, 0.7], frameon=False)
            _graph(ax, self.dates)
            pylab.ylabel(ylabel, fontsize=9)
            if self.date_label is not None:
                pylab.xlabel(self.date_label)

        if self.title:
            pylab.title(self.title)
        if not filename:
            outfn = utils.randfn('vis', outfmt)
            filename = os.path.join(config.scratchdir, outfn)
        else:
            outfn = filename
        pylab.savefig(filename)
        return outfn


class FieldInfo(object):

    def data(self):
        return self.fields.get_column(self.index)


class DemogFieldInfo(FieldInfo):

    join = None

    def __init__(self, field):
        self.field = field
        self.column = '%s.%s' % (field.table, field.name)
        self.label = field.label

    def options(self):
        return self.field.optionexpr()

class FormFieldInfo(FieldInfo):

    def __init__(self, forminfo, input):
        self.input = input
        self.join = forminfo.name
        self.column = '%s.%s' % (forminfo.tablename(), input.column)
        self.label = input.label or input.column

    def options(self):
        return self.input.choices


class ECFields(list):

    def __init__(self, params):
        self.params = params
        self.cols = []
        self.join = None
        self.rows = None

    def _get_field(self, field):
        form, field = field.split(':')
        if form:
            fi = self.params.form_info(form)
            input = fi.load().columns.find_input(field)
            return FormFieldInfo(fi, input)
        else:
            field = self.params.demog_fields().field_by_name(field)
            return DemogFieldInfo(field)

    def add_field(self, name):
        field = self._get_field(name)
        field.index = len(self)
        field.fields = self
        if field.join:
            assert self.join is None or self.join == field.join
            self.join = field.join
        self.append(field)
        self.cols.append(field.column)
        return field

    def load(self, query, include_missing_forms):
        if self.join:
            if include_missing_forms:
                join = 'LEFT JOIN'
            else:
                join = 'JOIN'
            fi = self.params.form_info(self.join)
            table = fi.tablename()
            query.join(join + ' case_form_summary USING (case_id)')
            query.join(join + ' %s ON (case_form_summary.summary_id = %s.summary_id AND NOT case_form_summary.deleted)' % (table, table))
            #query.where('NOT case_form_summary.deleted')
        self.rows = query.fetchcols(self.cols)

    def get_column(self, index):
        return [row[index] for row in self.rows]


class EpiCurveParamsMixin:

    show_epicurve = True

    ts_outfmt = 'png'
    ts_nbins = 'D1'
    ts_bincol = ':onset_datetime'
    ts_bincol2 = ''
    ts_stacking = ''
    ts_join = ''
    ts_missing_forms = False
    ts_stack_ratios = False
    ts_stack_suppress = None

    def available_outfmts(self):
        return [
            ('png', 'PNG'),
            ('svg', 'SVG'),
            ('pdf', 'PDF'),
        ]

    def available_nbins(self):
        return [
            ('N20', '20 bins'),
            ('N50', '50 bins'),
            ('N100', '100 bins'),
            ('D1', '1 day'),
            ('D2', '2 days'),
            ('D3', '3 days'),
            ('D4', '4 days'),
            ('D5', '5 days'),
            ('D6', '6 days'),
            ('D7', '7 days'),
            ('D14', '14 days'),
            ('D28', '28 days'),
        ]

    def available_forms(self):
        forms = [('', 'Case')]
        for fi in self.all_form_info():
            forms.append((fi.name, fi.label))
        return forms

    def available_bincol(self, allow_none=False):
        options = []
        if allow_none:
            options.append(('', 'None'))
        for field in self.demog_fields('report'):
            if field.render == 'datetimeinput':
                options.append((':%s' % field.name, field.label))
        if self.ts_join:
            fi = self.form_info(self.ts_join)
            form_options = []
            for input in fi.load().get_inputs():
                if input.render == 'DateInput':
                    form_options.append(((input.label or input.column),
                                        '%s:%s' % (fi.name, input.column)))
            form_options.sort()
            for l, n in form_options:
                options.append((n, l))
        return options

    def available_strata(self):
        options = [('', 'None')]
        for field in self.demog_fields('report'):
            if field.optionexpr is not None and field.name != 'tags':
                options.append((':%s' % field.name, field.label))
        if self.ts_join:
            fi = self.form_info(self.ts_join)
            form_options = []
            for input in fi.load().get_inputs():
                if input.render in ('DropList', 'RadioList'):
                    form_options.append(((input.label or input.column),
                                        '%s:%s' % (fi.name, input.column)))
            form_options.sort()
            for l, n in form_options:
                options.append((n, l))
        return options

    def available_values(self, field):
        return ECFields(self)._get_field(field).options()

    def _defaults(self, msgs):
        if not config.enable_matplotlib:
            msgs.msg('err', '%s not available on this system' % self.type_label)

    def report(self, cred, msgs, filename=None):
        self.check(msgs)
        if msgs.have_errors():
            return
        ec = EpiCurve('\n'.join(self.title(cred).splitlines()))
        # Fetch the data
        include_deleted = False
        if (self.ts_bincol == ':delete_timestamp'
                or self.ts_bincol2 == ':delete_timestamp'
                or self.ts_stacking == ':deleted'):
            include_deleted = None
        query = self.query(cred, include_deleted = include_deleted)
        ecfields = ECFields(self)
        stack_field = date2_field = None
        date_field = ecfields.add_field(self.ts_bincol)
        if self.ts_bincol2:
            date2_field = ecfields.add_field(self.ts_bincol2)
#        for col in ecfields.cols:
#            query.where('%s IS NOT NULL' % col)
        if self.ts_stacking:
            stack_field = ecfields.add_field(self.ts_stacking)
        ecfields.load(query, boolstr(self.ts_missing_forms))
        if not ecfields.rows:
            raise globals.Error('No records found')
        ec.set_dates(date_field.data(), date_field.label)
        if date2_field:
            ec.set_lower_dates(date2_field.data(), date2_field.label)
        ec.info(msgs)
        if msgs.have_errors():
            return
        if stack_field:
            ec.set_stack(stack_field.data(), stack_field.options(),
                         label=stack_field.label, 
                         ratios=boolstr(self.ts_stack_ratios),
                         suppress=self.ts_stack_suppress)
        if self.ts_nbins.startswith('N'):
            ec.set_n_bins(int(self.ts_nbins[1:]))
        elif self.ts_nbins.startswith('D'):
            ec.set_n_days(int(self.ts_nbins[1:]))
        return ImageReport(ec.graph(self.ts_outfmt, filename))

    def _forms_used(self, used):
        if self.ts_join:
            used.add(self.ts_join)

    def set_join(self, form):
        if form:
            if self.ts_join and self.ts_join != form:
                raise Error('Can only specify one form (requested %s and %s)' %
                            (self.ts_join, form))
            self.ts_join = form

    def _to_xml(self, xmlgen, curnode):
        def field_attrs(e, field):
            form, field = field.split(':')
            if form:
                e.attr('form', form)
            e.attr('field', field)
        e = xmlgen.push('epicurve')
        e.boolattr('missing_forms', self.ts_missing_forms)
        e.attr('format', self.ts_outfmt)
        e.attr('nbins', self.ts_nbins)
        e = xmlgen.push('dates')
        field_attrs(e, self.ts_bincol)
        xmlgen.pop()
        if self.ts_bincol2:
            e = xmlgen.push('dates')
            field_attrs(e, self.ts_bincol2)
            xmlgen.pop()
        if self.ts_stacking:
            e = xmlgen.push('stacking')
            field_attrs(e, self.ts_stacking)
            e.boolattr('ratios', self.ts_stack_ratios)
            for suppress in self.ts_stack_suppress:
                e = xmlgen.push('suppress')
                e.text(suppress)
                xmlgen.pop()
            xmlgen.pop()
        xmlgen.pop()
