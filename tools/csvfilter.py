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
import os
import sys
import csv
import optparse

class Error(Exception): pass

class Matcher:

    def __init__(self, header, field, value):
        self.field = field
        self.value = value
        try:
            self.index = header.index(self.field)
        except ValueError:
            raise Error('column %r not found' % self.field)


class Include(Matcher):

    def match(self, include, row):
        if not include:
            include = row[self.index] == self.value
        return include
        

class Exclude(Matcher):

    def match(self, include, row):
        if include:
            include = row[self.index] != self.value
        return include


def make_matchers(rules, header):
    matchers = []
    for op, field, value in rules:
        if op == '=':
            matchers.append(Include(header, field, value))
        else:
            matchers.append(Exclude(header, field, value))
    return matchers


def yield_rows(matchers, in_rows):
    initial = isinstance(matchers[0], Exclude)
    for row in in_rows:
        include = initial
        for matcher in matchers:
            include = matcher.match(include, row)
        if include:
            yield row


def write_rows(header, filter_rows, out_fn, limit=None):
    out_f = open(out_fn, 'wb')
    try:
        writer = csv.writer(out_f)
        writer.writerow(header)
        out_count = 0
        for row in filter_rows:
            writer.writerow(row)
            out_count += 1
            if limit and out_count >= limit:
                break
    except Exception:
        try:
            out_f.close()
        except OSError:
            pass
        os.unlink(out_fn)
        raise
    else:
        out_f.close()
        return limit and out_count >= limit


def filter(options, rules, in_fn, out_fn):
    f = open(in_fn, 'rb')
    try:
        reader = csv.reader(f)
        header = reader.next()
        try:
            matchers = make_matchers(rules, header)
        except Error, e:
            raise Error('%s: %s' % (in_fn, e))
        filter_rows = yield_rows(matchers, reader)
        if not options.chunk:
            write_rows(header, filter_rows, out_fn)
        else:
            n = 1
            base, ext = os.path.splitext(out_fn)
            while write_rows(header, filter_rows, 
                             '%s_%d%s' % (base, n, ext),
                             limit=options.chunk):
                n += 1
    finally:
        f.close()


usage = 'Usage: %prog [options] column=include column!=exclude in_file out_file'

def main():
    optp = optparse.OptionParser(usage=usage)
    optp.add_option('-c', '--chunk', type='int',
                    help='Split output in files of CHUNK rows or less')
    options, args = optp.parse_args()
    rules = []
    files = []
    for arg in args:
        try:
            field, value = arg.split('!=')
        except ValueError:
            try:
                field, value = arg.split('=')
            except ValueError:
                files.append(arg)
            else:
                rules.append(('=', field, value))
        else:
            rules.append(('!', field, value))
    if len(files) != 2 or not rules:
        optp.print_help()
        sys.exit(1)
    try:
        filter(options, rules, *files)
    except Error, e:
        sys.exit(e)


if __name__ == '__main__':
    main()
