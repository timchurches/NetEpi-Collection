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
UI Logic to support simple searches of a table
"""

from cocklebur import dbobj

class TableSearch:
    def __init__(self, db, table, col, filter=None, title=None, 
                 showcols=None, info_page=False):
        self.db = db
        self.table = table
        self.filter = filter
        self.title = title
        self.col = col
        if showcols is None:
            self.showcols = (col,)
        else:
            self.showcols = showcols
        self.info_page = info_page
        self.clear_search()

    def clear_search(self):
        self.term = ''
        self.clear_search_result()

    def clear_search_result(self):
        self.result = []
        self.clear_search_error()

    def clear_search_error(self):
        self.search_error = ''

    def search(self):
        self.clear_search_result()
        try:
            query = self.db.query(self.table)
            if self.filter:
                query.where(self.filter)
            if self.term:
                query.where('%s ilike %%s' % self.col,
                            dbobj.wild(self.term))
            self.result = query.fetchall(limit=100)
        except dbobj.DatabaseError, e:
            self.search_error = str(e)
        else:
            if not self.result:
                self.search_error = 'No matching entries found'

    def clear(self):
        self.clear_search()

    def span(self):
        span = len(self.showcols) + 1
        if self.info_page:
            span += 1
        return span

    def do(self, op, *args):
        if op in ('search', 'clear'):
            meth = getattr(self, op)
            meth(*args)
