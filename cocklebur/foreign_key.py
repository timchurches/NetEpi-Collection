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
from cocklebur import dbobj
from cocklebur.dbobj import table_dict

class ForeignKeySearch:
    def __init__(self, row, col_name, search_col, foreign_row_cache = None):
        self.row = row
        self.col_name = col_name
        self.search_col = search_col
        db = self.row.db()
        col_desc = self.row.table_desc().get_column(col_name)
        assert isinstance(col_desc, dbobj.ReferenceColumn)
        self.foreign_table_desc = db.get_table(col_desc.references)
        pkey_cols = self.foreign_table_desc.get_primary_cols()
        assert len(pkey_cols) == 1
        self.pkey_col = pkey_cols[0].name
        if foreign_row_cache is None:
            self.foreign_row_cache = table_dict.TableDict(self.foreign_table_desc)
        else:
            self.foreign_row_cache = foreign_row_cache
        value = getattr(self.row, self.col_name)
        if value is not None:
            self.foreign_row_cache.preload((value,))
        self.search_term = ''
        self.reset()

    def reset(self):
        self.error_msg = ''
        self.results = None
        self.query = None

    def new_query(self):
        self.query = dbobj.Query(self.foreign_table_desc, 
                                 order_by = self.search_col)
        if self.search_term:
            if type(self.search_col) not in (list, tuple):
                cols = [self.search_col]
            else:
                cols = self.search_col
            for col in cols:
                self.query.where('%s ILIKE %%s' % col, 
                                 dbobj.wild(self.search_term))

    def fetchall(self):
        try:
            try:
                results = self.query.fetchall()
            except dbobj.DatabaseError, e:
                self.error_msg = str(e)
            else:
                if len(results) == 0:
                    self.error_msg = 'not found'
                else:
                    self.results = results
                    self.foreign_row_cache.from_result(results)
        finally:
            self.query = None

    def search(self):
        self.query()
        self.fetchall()

    def select(self, index):
        foreign_key = getattr(self.results[index], self.pkey_col)
        setattr(self.row, self.col_name, foreign_key)
        self.reset()

    def ref_row(self):
        return self.foreign_row_cache[getattr(self.row, self.col_name)]
