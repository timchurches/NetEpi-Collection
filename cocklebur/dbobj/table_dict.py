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
try:
    set
except NameError:
    from sets import Set as set
from cocklebur.dbobj import query_builder

class TableDict(dict):
    def __init__(self, table_desc, key_col = None):
        self.table_desc = table_desc
        if key_col is None:
            pkey_cols = self.table_desc.get_primary_cols()
            assert len(pkey_cols) == 1
            self.primary_key_name = pkey_cols[0].name
        else:
            self.primary_key_name = key_col
        self.pending = None
        self.query_obj = None

    def want(self, key):
        """
        Record that we want /key/ preloaded
        """
        if key not in self:
            if self.pending is None:
                self.pending = set()
            self.pending.add(key)

    def add(self, row):
        primary_key = getattr(row, self.primary_key_name)
        self[primary_key] = row

    def from_result(self, result_set):
        for row in result_set:
            self.add(row)

    def preload(self, keys=()):
        keys = set(keys)
        if self.pending:
            keys.update(self.pending)
        keys = keys - set(self)
        if keys:
            query = query_builder.Query(self.table_desc)
            query.where_in(self.primary_key_name, keys)
            self.from_result(query.fetchall())
        self.pending = None

    def preload_all(self):
        query = query_builder.Query(self.table_desc)
        self.from_result(query.fetchall())

    def option_list(self, label_col):
        options = [(getattr(r, label_col), k) for k, r in self.items()]
        options.sort()
        return [(k, l) for l, k in options]

    def query(self, **kwargs):
        self.query_obj = query_builder.Query(self.table_desc)

    def where(self, where, *args):
        self.query_obj.where(where, *args)

    def fetch_preload(self, limit=None):
        result = self.query_obj.fetchall(limit=limit)
        self.from_result(result)
        self.query_obj = None
        return result
