#!/usr/bin/python
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

"""
A tool to extract and process "client report" data

client reports look like:

    client report: inst=collection page=tasks unit=1 user=1 start=1197333660 ip=127.0.0.1 server=0.155 client=0.87

"""

import sys
import os
import re
import math
import time
import datetime
import optparse
import colorsys

class ParseError(Exception): pass

groupby_cols = [
    'inst', 'page', 'unit', 'user', 'ip', 'forwarded', 
]

def record_filter(col, regexp):
    try:
        regexp = re.compile(regexp)
    except re.error, e:
        raise ParseError(e)
    return lambda record: regexp.search(record.get(col, ''))

def parse_line(line):
    cr = 'client report: '
    n = line.find(cr)
    if n < 0:
        return                  # not found
    record = {}
    for field in line[n+len(cr):-1].split():
        try:
            name, value = field.split('=', 1)
        except ValueError:
            raise ParseError('could not parse %r' % line)
        record[name] = value
    return record


fieldre = re.compile(r' (\w+)=')
def parse_line_forgiving(line):
    """
    A slower version of the line parser that copes with spaces within
    field values.
    """
    cr = 'client report:'
    s = line.find(cr)
    if s < 0:
        return                          # not found
    s += len(cr)
    e = line.find(', referer: ')        # Apache makes this harder
    record = {}
    fields = fieldre.split(line[s:e])
    n = 1
    while n < len(fields):
        record[fields[n]] = fields[n+1]
        n += 2
    return record


def parse_files(files, start=None, end=None, filter=None,
                       parser=parse_line_forgiving):
    for fn in files:
        try:
            f = open(fn)
        except IOError, (eno, estr):
            sys.exit('%s: %s' % (fn, estr))
        for line in f:
            try:
                record = parser(line)
            except ParseError, e:
                sys.exit('%s: %s' % (fn, e))
            if record is not None:
                try:
                    record['t'] = t = int(record['start'])
                except ValueError:
                    continue
                if filter and not filter(record):
                    continue
                if ((not start or t >= start) and
                    (not end or t < end)):
                    yield record
        f.close()


def write_csv(options, lines):
    """
    Write records as CSV
    """
    import csv

    fields = [
        'inst', 'page', 'unit', 'user', 'start', 'ip', 'forwarded', 
        'server', 'client'
    ]
    writer = csv.writer(sys.stdout)
    writer.writerow(fields)
    for record in lines:
        try:
            t = time.localtime(record['t'])
            record['start'] = time.strftime('%Y-%m-%d %H:%M:%S', t)
        except (ValueError, TypeError):
            pass
        writer.writerow([record.get(field, '') for field in fields])


def write_ds(options, line):
    """
    Write records as a NEA dataset
    """
    from SOOMv0 import soom, makedataset
    from SOOMv0.Sources.common import DataSourceBase
    from mx import DateTime

    class DataSource(DataSourceBase):
        def __init__(self, lines):
            DataSourceBase.__init__(self, 'client_report', [])
            self.lines = lines

        def next_rowdict(self):
            record = self.lines.next()
            t = record['t']
            record['date'] = DateTime.DateFromTicks(t)
            record['datetime'] = DateTime.DateTimeFromTicks(t)
            return record

    soom.messages = options.verbose
    soom.setpath(options.dspath)
    soom.writepath = soom.searchpath[0]

    ds = makedataset(options.dsname, label=options.dslabel)
    ds.addcolumn('inst', label='Application instance', 
                          coltype='categorical', datatype='recode')
    ds.addcolumn('page', label='Application page', 
                          coltype='categorical', datatype='recode')
    ds.addcolumn('user', label='User ID', 
                          coltype='scalar', datatype='int')
    ds.addcolumn('unit', label='Unit ID', 
                          coltype='scalar', datatype='int')
    ds.addcolumn('date', label='Report date', 
                          coltype='ordinal', datatype='date')
    ds.addcolumn('datetime', label='Report date/time', 
                          coltype='ordinal', datatype='datetime')
    ds.addcolumn('ip', label='Remote IP address', 
                          coltype='categorical', datatype='recode')
    ds.addcolumn('forwarded', label='Forwarded IP address', 
                          coltype='categorical', datatype='recode')
    ds.addcolumn('server', label='Server time', 
                          coltype='scalar', datatype='float')
    ds.addcolumn('client', label='Client time', 
                          coltype='scalar', datatype='float')
    ds.loaddata(DataSource(lines), initialise=True, finalise=True)
    ds.save()


def make_n_colors(n):
    # We should just return a 3-tuple of float RGB values, but matplotlib is
    # too smart for it's own good, and if the plot has three x values, it
    # unsuccessfully tries to interpret this as colour values for each X value,
    # so we use the HTML #rrggbb format instead
    return ['#%02x%02x%02x' % colorsys.hsv_to_rgb(float(i) / n, 0.8, 255.0) 
            for i in range(n)]


class PlotGroup(object):
    __slots__ = ('name', 'x', 'y', 'color', 'handle')

    bins_per_day = 24.0

    def __init__(self, name):
        self.name = str(name)
        self.x = []
        self.y = []

    def to_rate(self):
        counts = {}
        for x in self.x:
            epoch = math.floor(x * self.bins_per_day)
            counts[epoch] = counts.get(epoch, 0) + 1
        x = []
        y = []
        for epoch, count in counts.iteritems():
            x.append(epoch / self.bins_per_day)
            y.append(count)
        self.x, self.y = x, y


def avg(seq):
    total = 0.0
    count = 0
    for v in seq:
        total += v
        count += 1
    return total / count


def plot(options, lines):
    try:
        import pylab
    except ImportError:
        sys.exit('MatPlotLib (pylab) not found?')

    if options.local:
        measure = 'server'
    else:
        measure = 'client'
    groupby = options.groupby

    day_seconds = 24.0*60*60
    gregorian_offs = datetime.datetime.fromtimestamp(0).toordinal()

    data = {}
    last_g = NotImplemented
    g = None
    for record in lines:
        t = record.get('t')
        m = record.get(measure)
        if t and m:
            if groupby:
                g = record.get(groupby)
            if g != last_g:
                try:
                    group = data[g]
                except KeyError:
                    group = data[g] = PlotGroup(g)
                last_g = g
            t = t / day_seconds + gregorian_offs
            group.x.append(t)
            group.y.append(float(m))
    if options.rate:
        for group in data.itervalues():
            group.to_rate()
    if not data:
        sys.exit('No data found')
    for color, group in zip(make_n_colors(len(data)), data.values()):
        group.color = color

    if 'TZ' in os.environ:
        pylab.rcParams['timezone'] = os.environ['TZ']
    elif os.path.exists('/etc/timezone'):
        tzname = open('/etc/timezone').next().strip()
        try:
            pylab.rcParams['timezone'] = tzname        
        except Exception:
            pass

    fig = pylab.figure(figsize=(10,6), dpi=120, facecolor='w')
    data = data.values()
    
    # Render the least common points on top...
    data.sort(lambda a, b: cmp(len(b.x), len(a.x)))
    for group in data:
        group.handle = pylab.plot_date(group.x, group.y, color=group.color, 
                                       marker='.')
    if options.groupby:
        if len(data) > 12:
            data.sort(lambda a, b: cmp(avg(b.y), avg(a.y)))
            data = data[:12]
        else:
            data.sort(lambda a, b: cmp(a.name, b.name))
        handles = [g.handle for g in data]
        labels = ['%4.1f - %s' % (avg(g.y), g.name) for g in data]
        legend = pylab.legend(handles, labels, numpoints=1, loc='upper left')
        pylab.setp(legend.get_texts(), fontsize=8)
    ax = pylab.gca()
    #ax.grid(True)
    ax.set_axis_bgcolor('#cccccc')
    if options.logscale:
        ax.set_yscale("log")
    ax.autoscale_view()
    fig.autofmt_xdate()
    if options.rate:
        pylab.ylabel('Requests per hour')
        title = 'Request rate'
    elif options.local:
        pylab.ylabel('Server response (in seconds)')
        title = 'Server response'
    else:
        pylab.ylabel('Round trip (in seconds)')
        title = 'Round-trip'
    if options.groupby:
        title += ' by %s' % options.groupby
    if options.filter:
        title += ' where %s' % options.filter
    pylab.title(title)

    #pylab.xlabel('Date/time')

    if options.plotfile:
        pylab.savefig(options.plotfile)
    else:
        pylab.show()


def parse_datetime_opt(date):
    try:
        t = time.strptime(date, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        try:
            t = time.strptime(date, '%Y-%m-%d %H:%M')
        except ValueError:
            try:
                t = time.strptime(date, '%Y-%m-%d')
            except ValueError:
                raise ParseError('Cannot parse date %r (use ISO YYYY-MM-DD '
                                 'format)' % date)
    return time.mktime(t)


if __name__ == '__main__':
    optp = optparse.OptionParser(usage='usage: %prog [options] <logfile> ...')
    optp.add_option('-c', '--csv', 
                    action='store_true', default=False,
                    help='emit CSV records')

    optg = optparse.OptionGroup(optp, 'Filtering')
    optg.add_option('--start', 
                    help='Ignore records before START')
    optg.add_option('--end', 
                    help='Ignore records after END')
    optg.add_option('--filter', metavar='COLUMN=REGEXP',
                    help='Only produce rows where COLUMN matches REGEXP')
    optp.add_option_group(optg)

    optg = optparse.OptionGroup(optp, 'NetEpi Analysis dataset options'
                    '(specify dataset name for ds output mode)')
    optg.add_option('-N', '--dsname', 
                    help='NetEpi Analysis dataset name')
    optg.add_option('--dslabel', default='NetEpi Collection client reports',
                    help='NetEpi Analysis dataset label')
    optg.add_option('--dspath', 
                    help='NetEpi Analysis dataset path')
    optg.add_option('-v', '--verbose', 
                    action='store_true', default=False,
                    help='Verbose operation')
    optp.add_option_group(optg)

    optg = optparse.OptionGroup(optp, 'MatPlotLib options')
    optg.add_option('-p', '--plot', 
                    action='store_true', default=False,
                    help='Graph response times (requires MatPlotLib)')
    optg.add_option('-g', '--groupby', metavar='COLUMN',
                    help='Group-by column (one of: %s)' % 
                            ', '.join(groupby_cols))
    optg.add_option('-l', '--local', 
                    action='store_true', default=False,
                    help='Plot local (server) times, rather than client '
                         'round-trip times (default)')
    optg.add_option('-r', '--rate', 
                    action='store_true', default=False,
                    help='Plot request rate')
    optg.add_option('--logscale', 
                    action='store_true', default=False,
                    help='Use log scale for y axis')
    optg.add_option('--plotfile', '--output',
                    help='write plot to FILE', metavar='FILE')
    optp.add_option_group(optg)

    options, args = optp.parse_args()

    if options.start:
        try:
            options.start = parse_datetime_opt(options.start)
        except ParseError, e:
            optp.error('--start: %s' % e)
    if options.end:
        try:
            options.end = parse_datetime_opt(options.end)
        except ParseError, e:
            optp.error('--start: %s' % e)
    filter_fn = None
    if options.filter:
        try:
            col, regexp = options.filter.split('=')
        except ValueError:
            optp.error('filter syntax is COLUMN=REGEXP')
        if col not in groupby_cols:
            optp.error('--filter column must be one of %s' % 
                            ', '.join(groupby_cols))
        try:
            filter_fn = record_filter(col, regexp)
        except ParseError, e:
            optp.error(e)
    if options.groupby and options.groupby not in groupby_cols:
        optp.error('--groupby must be one of %s' % ', '.join(groupby_cols))

    if not args:
        optp.error('specify at least one input file')

    oneof = 'csv', 'dsname', 'plot'
    if sum([bool(getattr(options, name)) for name in oneof]) != 1:
        optp.error('specify one and only one of %s' %
            ', '.join(['--' + name for name in oneof]))

    lines = parse_files(args, start=options.start, end=options.end,
                              filter=filter_fn)

    if options.csv:
        write_csv(options, lines)

    if options.dsname:
        write_ds(options, lines)

    if options.plot:
        plot(options, lines)
