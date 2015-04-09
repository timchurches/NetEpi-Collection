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
#   Copyright (C) 2004-2011 Health Administration Corporation and others. 
#   All Rights Reserved.
#
#   Contributors: See the CONTRIBUTORS file for details of contributions.
#

import sys
import csv

print '''
# Locality to postcode mapping
# Derived from http://www1.auspost.com.au/postcodes/

locality_to_postcode = {'''
rows = list(csv.reader(open(sys.argv[1])))
localities = {}
for row in rows[1:]:
    locality = row[1].replace('-', '')
    pcode = row[0]
    category = row[9].strip()
    if category == 'Delivery Area' and locality not in localities:
        # Just use first seen
        localities[locality] = pcode
        print '    %r: %r,' % (row[1].replace('-', ''), row[0])
print '}'

