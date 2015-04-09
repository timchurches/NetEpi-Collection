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

def calc_checkdigit(id):
    sum = 0
    for i, d in enumerate(id):
        sum += int(d) * (i + 1)
    return str((sum % 11) % 10)

def check_checkdigit(id_and_check):
    invalid = False, None
    try:
        id = id_and_check[:-1]
        check = id_and_check[-1]
    except IndexError:
        return invalid
    try:
        if calc_checkdigit(id) == check:
            return True, int(id)
    except ValueError:
        pass
    return invalid

def add_checkdigit(id):
    id = str(id)
    return id + calc_checkdigit(id)

def test():
    import random
    n = 100000
    okay_count = 0
    for i in xrange(n):
        okay, id = check_checkdigit('%d' % random.randrange(1000000000))
        if okay:
            okay_count += 1
    print '%.1f%% okay' % (okay_count * 100.0 / n)
