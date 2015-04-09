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
A script to pre-process Health Declaration csv data, normalising
some fields, and optionally filtering on flight and/or seat (with
row proximity). Also:
 - e-mail fields are concatenated as sectiona_email and sectionb_email
 - address fields are concatenated as sectiona1, sectiona2, sectionb1, sectionb2
"""

import sys
import os
import csv
import re
import optparse

merge_fields = (
    'name',
    'address',
    'state',
    'postcode',
    'phone',
    'mobilephone',
    'email',
)

class ParseError(Exception): pass

def normalise(v):
    if v:
        return v.strip().upper()


normalise_flight = normalise

row_re = re.compile(r'^\s*[A-Z]?([0-9]+)[A-Z]?\s*$', re.IGNORECASE)

def parse_seat_row(seat):
    if not seat:
        return
    match = row_re.match(seat)
    if not match:
        raise ParseError('Could not parse seat: %r' % seat)
    return int(match.group(1))


def seat_near(seat):
    seat_row = parse_seat_row(seat)
    return (seat_row >= options.row - options.proximity
            and seat_row <= options.row + options.proximity)


def filter_row(row):
    row['flight_number'] = normalise_flight(row['flight_number'])
    if options.flight and options.flight != row['flight_number']:
        return False
    if options.seat:
        if (not seat_near(row['seat_number']) and 
            (not row['alternative_seat_number'] or
            not seat_near(row['alternative_seat_number']))):
            return False
    return True


def combine(row, *fields):
    values = []
    seen = set()
    for field in fields:
        value = row[field]
        if value:
            value = value.strip()
        if value:
            lvalue = value.lower()
            if lvalue not in seen:
                seen.add(lvalue)
                values.append(value)
    return ', '.join(values)


new_fields = [
    'sectiona_email',
    'sectiona_phone',
    'sectiona_mobilephone',
    'sectionb',
]
def process_row(row):
    row['sectiona_email'] = combine(row, 'sectiona_email1', 'sectiona_email2')
    row['sectiona_phone'] = combine(row, 'sectiona_phone1', 'sectiona_phone2')
    row['sectiona_mobilephone'] = combine(row, 'sectiona_mobilephone1', 
                                               'sectiona_mobilephone2')
    sec = 'b'
    blocks = []
    seen = set()
    for subsec in '12':
        lines = []
        for field in merge_fields:
            value = row.get('section%s_%s%s' % (sec, field, subsec))
            if value and value.strip():
                lines.append('%s: %s' % (field, value.strip()))
        lines = '\r\n'.join(lines)
        if lines and lines not in seen:
            seen.add(lines)
            blocks.append(lines)
    row['section%s' % sec] = '\r\n\r\n'.join(blocks)
    return row


def process_file(out_f, fn):
    header = None
    f = open(fn, 'rb')
    in_count = out_count = err_count = 0
    try:
        reader = csv.reader(f)
        writer = csv.writer(out_f)
        for row in reader:
            if header is None:
                header = [col.lower() for col in row]
                header.extend(new_fields)
                writer.writerow(header)
            else:
                in_count += 1
                row = dict(map(None, header, row))
                try:
                    if not filter_row(row):
                        continue
                except ParseError, m:
                    err_count += 1
                    sys.stderr.write('WARNING: %s, row %d: %s\n' %
                                     (fn, in_count + 1, m))
                try:
                    row = process_row(row)
                except ParseError, m:
                    err_count += 1
                    sys.stderr.write('ERROR: %s, row %d: %s\n' %
                                     (fn, in_count + 1, m))
                else:
                    if row:
                        writer.writerow([row[col] for col in header])
                        out_count += 1
    finally:
        f.close()
    if options.verbose:
        print 'Read %d records from %s, wrote %s records, %d warnings' %\
            (in_count, fn, out_count, err_count)


def main():
    global options

    from optparse import OptionParser

    optp = OptionParser()
    optp.add_option('--flight', dest="flight",
                    help="Filter on FLIGHT")
    optp.add_option('--seat', dest="seat",
                    help="Filter on SEAT")
    optp.add_option('--proximity', dest="proximity", default=2, type='int',
                    help="Row proximity for seat filter (default: 2)")
    optp.add_option('-o', dest="outfile",
                    help="Write output to FILE", metavar='FILE')
    optp.add_option('-v', dest="verbose", action='store_true', default=False,
                    help="Verbose output")

    options, args = optp.parse_args()
    if len(args) != 1:
        optp.error('No input file specified')

    options.flight = normalise_flight(options.flight)
    try:
        options.row = parse_seat_row(options.seat)
    except ParseError, m:
        optp.error(m)
    if options.outfile:
        out_f = open(options.outfile, 'wb')
    else:
        out_f = sys.stdout
    try:
        process_file(out_f, *args)
    except Exception, e:
        if options.outfile:
            out_f.close()
            os.unlink(options.outfile)
        raise
    else:
        if options.outfile:
            out_f.close()

if __name__ == '__main__':
    main()
