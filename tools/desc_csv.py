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
Produce a simple description of the data in a CSV file, attempting to detect
types and reporting maximum field width.
"""
import sys
import os
import csv
import re

isodate_re = re.compile(r'^\d{4}-\d{2}-\d{2}$')
isodatetime_re = re.compile(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$')
decimal_re = re.compile(r'^\d*\.\d*$')

class Col:
    def __init__(self, name):
        self.name = name
        self.maxlen = 0
        self.maybe_isodate = True
        self.maybe_isodatetime = True
        self.maybe_decimal = True
        self.maybe_int = True

    def add(self, value):
        value_len = len(value)
        if value_len > self.maxlen:
            self.maxlen = value_len
        if self.maybe_decimal and not decimal_re.match(value):
            self.maybe_decimal = False
        if self.maybe_isodate and not isodate_re.match(value):
            self.maybe_isodate = False
        if self.maybe_isodatetime and not isodatetime_re.match(value):
            self.maybe_isodatetime = False
        if self.maybe_int and not value.isdigit():
            self.maybe_int = False
        
    def desc(self):
        if self.maybe_int:
            type = 'int'
        elif self.maybe_decimal:
            type = 'decimal'
        elif self.maybe_isodate:
            type = 'date'
        elif self.maybe_isodatetime:
            type = 'datetime'
        else:
            type = 'string'
        return self.name, type, self.maxlen


def desc_file(fn):
    cols = None
    for row in csv.reader(open(fn, 'rb')):
        if cols is None:
            cols = [Col(name) for name in row]
        else:
            for col, value in zip(cols, row):
                if value:
                    col.add(value)
    f = open('%s.desc' % fn, 'w')
    try:
        w = csv.writer(f)
        w.writerow(('name', 'type', 'len'))
        for col in cols:
            w.writerow(col.desc())
    finally:
        f.close()

if __name__ == '__main__':
    for fn in sys.argv[1:]:
        desc_file(fn)
