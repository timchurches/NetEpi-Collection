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

class _PTcommon:
    def __init__(self, pt_set, label_col):
        self.pt_set = pt_set
        self.label_col = label_col
        self.pt_available = []

    def set_key(self, key):
        self.pt_set.set_key(key)

    def db_update(self):
        self.pt_set.db_update()

    def db_revert(self):
        self.pt_set.db_revert()

    def db_has_changed(self):
        return self.pt_set.db_has_changed()

    def __len__(self):
        return len(self.pt_set)

    def get_included(self):
        included = [(getattr(self.pt_set[i], self.label_col), i)
                    for i in range(len(self.pt_set))]
        included.sort()
        return [(i, l) for l, i in included]

    def get_available(self):
        available = [(getattr(self.pt_available[i], self.label_col), i)
                    for i in range(len(self.pt_available))]
        available.sort()
        return [(i, l) for l, i in available]

    def add(self, index):
        self.pt_set.add(self.pt_available.pop(int(index)))

    def remove(self, index):
        row = self.pt_set.pop(int(index))
        if row not in self.pt_available:
            self.pt_available.append(row)

    def db_desc(self):
        added, removed = self.pt_set.changes()
        if not added and not removed:
            return
        table = self.pt_set.pt_info.table_desc.name
        keycol = self.pt_set.pt_info.master_col
        fields = ['%s:%r' % (keycol, self.pt_set.key)]
        for row in removed:
            fields.append('-(%s)' % getattr(row, self.label_col))
        for row in added:
            fields.append('+(%s)' % getattr(row, self.label_col))
        return '%s[%s]' % (table, ', '.join(fields))

    dispatch = ()

    def do(self, op, *args):
        if op in self.dispatch:
            meth = getattr(self, op)
            meth(*args)


class SearchPT(_PTcommon):
    def __init__(self, pt_set, label_col, filter=None, name='pt_search',
                 info_page=False):
        _PTcommon.__init__(self, pt_set, label_col)
        self.is_ordered = 0
        self.filter = filter
        self.name = name
        self.info_page = info_page
        self.clear_search()

    def clear_search(self):
        self.search_term = ''
        self.clear_search_result()

    def clear_search_result(self):
        self.pt_available = []
        self.clear_search_error()

    def clear_search_error(self):
        self.search_error = ''

    def selected(self):
        return self.pt_set

    def search(self):
        self.clear_search_result()
        try:
            table_dict = self.pt_set.get_slave_cache()
            table_dict.query(order_by = self.label_col)
            if self.search_term:
                table_dict.where('%s ilike %%s' % self.label_col,
                                 dbobj.wild(self.search_term))
            if self.filter:
                table_dict.where(self.filter)
            self.pt_available = table_dict.fetch_preload(limit=100)
        except dbobj.DatabaseError, e:
            self.search_error = str(e)
        else:
            if not self.pt_available:
                self.search_error = 'No matching entries found'

    def clear(self):
        self.clear_search()

    def move_up(self, index):
        self.pt_set.move_up(int(index))

    def move_dn(self, index):
        self.pt_set.move_down(int(index))

    dispatch = 'search', 'clear', 'add', 'remove', 'move_up', 'move_dn'


class OrderedSearchPT(SearchPT):
    def __init__(self, pt_set, label_col, filter=None, name='pt_search'):
        SearchPT.__init__(self, pt_set, label_col, filter, name)
        self.is_ordered = 1

    def get_included(self):
        return [(i, getattr(self.pt_set[i], self.label_col))
                for i in range(len(self.pt_set))]

def highest_first(g):
    g = [int(i) for i in g]
    g.sort()
    g.reverse()
    return g

class SelectPT(_PTcommon):
    def __init__(self, pt_set, label_col, name='group_edit'):
        _PTcommon.__init__(self, pt_set, label_col)
        self.name = name
        slave_pkey = self.pt_set.pt_info.slave_pkey
        available = self.pt_set.get_slave_cache().copy()
        for row in self.pt_set:
            try:
                del available[getattr(row, slave_pkey)]
            except KeyError:
                pass
        self.pt_available = available.values()
        self.include_group = []
        self.exclude_group = []

    def add(self):
        for index in highest_first(self.include_group):
            _PTcommon.add(self, index)
        self.include_group = []

    def remove(self):
        for index in highest_first(self.exclude_group):
            _PTcommon.remove(self, index)
        self.exclude_group = []

    dispatch = 'add', 'remove'
