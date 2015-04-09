#! /usr/bin/env python
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
Split a file into parts preserving header line(s) in a manner akin
to split(1).
"""

import sys, optparse, os


ALPHABET = 'abcdefghijklmnopqrstuvwxyz'


def int2str(i, length):
    digits = []
    while length > 0 or i:
        digits.insert(0, ALPHABET[i % 26])
        i /= 26
        length -= 1
    return ''.join(digits)
    


def csvsplit(args):
    parser = optparse.OptionParser(usage="usage: %prog [options] [file [name]]")
    parser.add_option('-?', action='help', help=optparse.SUPPRESS_HELP)
    parser.add_option('-a', '--suffix-length',
            type='int', default=2,
            metavar='m',
            help='use m letters to form the suffix of the file name [default: %default]')
    parser.add_option('-H', '--header-lines',
            type='int', default=1,
            metavar='h',
            help='repeat h lines from the start of the input file at the start of each output file [default: %default]')
    parser.add_option('-l', '--line-count',
            type='int', default=1000,
            metavar='n',
            help='create smaller files n lines in length [default: %default]')
    options, args = parser.parse_args(args)
    if len(args) > 2:
        parser.error('too many arguments')
    if not args or args[0] == '-':
        input = sys.stdin
    else:
        input = file(args[0], 'r')
    if options.suffix_length <= 0:
        parser.error('suffix length must be positive')
    if options.header_lines < 0:
        parser.error('number of header lines must be non-negative')
    if options.line_count <= 0:
        parser.error('line count must be positive')
    if len(args) == 2:
        prefix = args[1]
    else:
        prefix = 'x.csv'
    prefix, ext = os.path.splitext(prefix)
    part = 0
    count = 0
    # grab the lines to repeat
    if options.header_lines > 0:
        header = []
        for l in input:
            header.append(l)
            if len(header) == options.header_lines:
                header = ''.join(header)
                break
    else:
        header = ''
    # loop over input
    for l in input:
        # start a new output file as necessary
        if count % options.line_count == 0:
            output = file(prefix + int2str(part, options.suffix_length) + ext, 'w')
            output.write(header)
            part += 1
        output.write(l)
        count += 1
    output.close()

if __name__ == '__main__':
    csvsplit(sys.argv[1:])
