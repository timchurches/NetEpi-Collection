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
from cocklebur.dbobj.result import ResultSet
from cocklebur.dbobj import table_dict, query_builder
try:
    set
except NameError:
    from sets import Set as set

class PTSet:
    """
    Give the illusion of being a set of slave rows (and maintain PT)
    """
    def __init__(self, pt_info, key=None):
        self.pt_info = pt_info
        self.set = ResultSet(self.pt_info.table_desc)
        self.key = key
        self.initial = set()

    def _add(self, pt_row):
        """
        Directly add a pt_row to the set. This differs from the .add() method,
        which adds a slave column.
        """
        slave_key = getattr(pt_row, self.pt_info.slave_col)
        self.set.append(pt_row)
        self.pt_info.slave_cache.want(slave_key)
        self.initial.add(slave_key)

    def __getitem__(self, i):
        pt_row = self.set[i]
        slave_key = getattr(pt_row, self.pt_info.slave_col)
        return self.pt_info.slave_cache[slave_key]

    def __len__(self):
        return len(self.set)

    def __contains__(self, row):
        slave_key = getattr(row, self.pt_info.slave_pkey)
        pt_slave = self.pt_info.slave_col
        for pt_row in self.set:
            if getattr(pt_row, pt_slave) == slave_key:
                return True
        return False

    def set_key(self, key):
        # When we're creating a new master row, we don't know it's key until
        # later.
        self.key = key

    def slave_keys(self):
        # This method is primarily for unit testing purposes
        slave_col = self.pt_info.slave_col
        return [getattr(pt_row, slave_col) for pt_row in self.set]

    def add(self, row):
        """
        Add a *slave* row to the pt (creating pt row if necessary).
        """
        if row in self:
            return
        self._add_slave_key(getattr(row, self.pt_info.slave_pkey))
        self.pt_info.slave_cache.add(row)

    def _add_slave_key(self, slave_key):
        pt_info = self.pt_info
        pt_row = pt_info.table_desc.get_row()
        setattr(pt_row, pt_info.slave_col, slave_key)
        self.set.append(pt_row)

    def add_slave_key(self, slave_key):
        self._add_slave_key(slave_key)
        self.pt_info.slave_cache.preload([slave_key])

    def remove(self, row):
        slave_key = getattr(row, self.pt_info.slave_pkey)
        pt_slave = self.pt_info.slave_col
        for i in range(len(self)-1, -1, -1):
            if getattr(self.set[i], pt_slave) == slave_key:
                del self.set[i]

    def pop(self, index):
        pt_row = self.set.pop(index)
        slave_key = getattr(pt_row, self.pt_info.slave_col)
        return self.pt_info.slave_cache[slave_key]

    def _swap(self, index_a, index_b):
        pt_row_a, pt_row_b = self.set[index_a], self.set[index_b]
        for col_desc in self.pt_info.table_desc.get_columns():
            if not col_desc.primary_key:
                a = getattr(pt_row_a, col_desc.name) 
                b = getattr(pt_row_b, col_desc.name)
                setattr(pt_row_a, col_desc.name, b) 
                setattr(pt_row_b, col_desc.name, a) 

    def move_up(self, index):
        if index > 0:
            self._swap(index, index - 1)

    def move_down(self, index):
        if index < len(self.set) - 1:
            self._swap(index, index + 1)

    def db_update(self):
        assert self.key is not None
        for pt_row in self.set:
            setattr(pt_row, self.pt_info.master_col, self.key)
        self.set.db_update()

    def db_revert(self):
        self.set.db_revert()

    def db_has_changed(self):
        return self.set.db_has_changed()

    def save_state(self):
        self.set.save_state()

    def comma_list(self, slave_col_name):
        items = [getattr(r, slave_col_name) for r in self]
        items.sort()
        return ', '.join(items)

    def get_slave_cache(self):
        return self.pt_info.slave_cache

    def changes(self):
        current = set()
        for pt_row in self.set:
            current.add(getattr(pt_row, self.pt_info.slave_col))
        added = [self.pt_info.slave_cache[k] for k in current - self.initial]
        removed = [self.pt_info.slave_cache[k] for k in self.initial - current]
        return added, removed

class PTInfo:
    def __init__(self, table_desc, master_col, slave_col):
        self.table_desc = table_desc
        self.master_col = master_col
        self.slave_col = slave_col
        pkey_col_desc, = table_desc.get_primary_cols()
        self.pkey = pkey_col_desc.name

        target_desc = table_desc.get_column(self.master_col).target_column()
        self.master_pkey = target_desc.name

        target_desc = table_desc.get_column(self.slave_col).target_column()
        self.slave_pkey = target_desc.name
        self.slave_cache = table_dict.TableDict(target_desc.table_desc)

        pt_pkey_desc, = table_desc.get_primary_cols()
        self.pt_pkey = pt_pkey_desc.name

class ParticipationTable:
    def __init__(self, table_desc, master_col, slave_col):
        self.pt_info = PTInfo(table_desc, master_col, slave_col)
        self.sets = {}
        self._new_set = None

    def preload(self, keys):
        keys = [key for key in keys if key is not None and key not in self.sets]
        if keys:
            for key in keys:
                self.sets[key] = PTSet(self.pt_info, key)
            pt_info = self.pt_info
            query = query_builder.Query(pt_info.table_desc,
                                        order_by = pt_info.pkey)
            query.where_in(pt_info.master_col, keys)
            for row in query.fetchall():
                key = getattr(row, pt_info.master_col)
                self.sets[key]._add(row)
            for key in keys:
                self.sets[key].save_state()
            pt_info.slave_cache.preload()
                
    def preload_from_result(self, result):
        master_pkey = self.pt_info.master_pkey
        self.preload([getattr(r, master_pkey) for r in result])

    def new_set(self):
        self._new_set = PTSet(self.pt_info)
        return self._new_set

    def _check_new_set(self):
        if self._new_set is not None and self._new_set.key is not None:
            self.sets[self._new_set.key] = self._new_set
            self._new_set = None

    def __getitem__(self, key):
        self._check_new_set()
        if key is None:
            return self.new_set()
        else:
            return self.sets[key]

    def get_slave_cache(self):
        return self.pt_info.slave_cache

    def db_has_changed(self):
        self._check_new_set()
        for set in self.sets.values():
            if set.db_has_changed():
                return True
        return False

    def db_update(self):
        self._check_new_set()
        for set in self.sets.values():
            set.db_update()

    def db_revert(self):
        self._new_set = None
        for set in self.sets.values():
            set.db_revert()

def ptset(table_desc, master_col, slave_col, key=None, filter=None):
    pt_info = PTInfo(table_desc, master_col, slave_col)
    ptset = PTSet(pt_info, key)
    if key is not None:
        query = query_builder.Query(pt_info.table_desc,
                                    order_by = pt_info.pkey)
        query.where('%s = %%s' % pt_info.master_col, key)
        if filter is not None:
            query.where(filter)
        for row in query.fetchall():
            ptset._add(row)
        pt_info.slave_cache.preload()
    return ptset
