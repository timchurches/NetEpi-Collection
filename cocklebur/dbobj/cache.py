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

import time

class RowCache:
    """
    A simple proxy to a dbobj.ResultRow object that periodically
    refreshes itself.
    """

    def __init__(self, initial_row, ttl=60):
        self.__row = initial_row
        self.__when = time.time() + ttl
        self.__ttl = ttl

    def __refresh(self):
        t = time.time()
        if self.__when < t:
            self.__when = t + self.__ttl
            self.__row.db_refetch()

    def __getattr__(self, a):
        if a.startswith('_'):
            raise AttributeError(a)
        self.__refresh()
        return getattr(self.__row, a)

# Other ideas:
#  - a "Query"/"ResultSet" proxy that periodically refreshes.
#  - subsume table_dict?
