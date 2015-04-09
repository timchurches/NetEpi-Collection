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

# Paper over some of the differences between python versions
try:
    # Introduced in python 2.4, faster implementation in 2.5
    set = set
except NameError:
    from sets import Set as set

try:
    # Introduced in python 2.4
    sorted = sorted
except NameError:
    def sorted(iterable, cmp=None, key=None, reverse=False):
        if key is None:
            lst = list(iterable)
            lst.sort(cmp)
            if reverse:
                lst.reverse()
            return lst
        else:
            lst = [(key(val), idx, val) for idx, val in enumerate(iterable)]
            lst.sort(cmp)
            if reverse:
                lst.reverse()
            return [i[-1] for i in lst]
