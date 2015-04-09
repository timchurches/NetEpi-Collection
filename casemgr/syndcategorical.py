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
Base classes for syndrome-specific case fields such as "case status"

"""

from casemgr import globals, mergelabels, cached


unknown_state = ('', 'Unknown')

class SyndromeCategoricalInfo(object):

    table = None
    order_by = None
    explicit_order = False
    defaults = []


class EditSyndromeCategorical(object):
    """
    Table must have "name" and "label" columns.

    """

    def __init__(self, syndrome_id):
        """
        syndrome_id is None to edit the default values
        """
        self.syndrome_id = syndrome_id
        self.order = ''
        query = globals.db.query(self.table, order_by=self.order_by)
        if self.syndrome_id is None:
            query.where('syndrome_id IS NULL')
        else:
            query.where('syndrome_id = %s', self.syndrome_id)
        self.rows = query.fetchall()
        if not self.rows:
            if self.syndrome_id is not None:
                query = globals.db.query(self.table, 
                                         order_by=self.order_by)
                query.where('syndrome_id IS NULL')
                for row in query.fetchall():
                    self.new(name=row.name, label=row.label)
            if not self.rows:
                for name, label in self.defaults:
                    self.new(name=name, label=label)

    def __len__(self):
        return len(self.rows)

    def new(self, **kwargs): 
        if self.explicit_order:
            id = globals.db.nextval(self.table, self.order_by)
            kwargs[self.order_by] = id
        row = self.rows.new_row(syndrome_id=self.syndrome_id, **kwargs)
        self.rows.append(row)
        return row

    def delete(self, index):
        del self.rows[index]

    def swap(self, a, b):
        assert self.explicit_order
        length = len(self.rows)
        if 0 <= a < length and 0 <= b < length:
            tmp = self.rows[a].name, self.rows[a].label
            self.rows[a].name, self.rows[a].label = \
                self.rows[b].name, self.rows[b].label
            self.rows[b].name, self.rows[b].label = tmp

    def reorder(self):
        if self.order:
            nl = [(row.name, row.label) for row in self.rows]
            for dst, src in enumerate(self.order.split(',')):
                self.rows[dst].name, self.rows[dst].label = nl[int(src)]
            self.order = ''

    def move_up(self, index):
        self.swap(index, index - 1)

    def move_down(self, index):
        self.swap(index, index + 1)

    def __getitem__(self, index):
        return self.rows[index]

    def has_changed(self):
        return self.rows.db_has_changed()

    def update(self):
        self.rows.db_update()


class SyndromeValues(list):

    def __init__(self, initial=None):
        self.by_name = {}
        if initial is not None:
            for row in initial:
                self.add(*row)

    def add(self, name, label):
        pair = name, label
        self.append(pair)
        self.by_name[name.lower()] = pair

    def __contains__(self, name):
        return name.lower() in self.by_name

    def label(self, name):
        if name:
            try:
                return self.by_name[name.lower()][1]
            except KeyError:
                pass
        return unknown_state[1]

    def normalise(self, name):
        if name:
            try:
                return self.by_name[name.lower()][0]
            except KeyError:
                pass
        return unknown_state[0]


class SyndromeCategorical(cached.NotifyCache):

    notification_target = 'syndromes'

    def load(self):
        by_syndrome = {}
        allvals = mergelabels.MergeLabels()
        allvals.add(*unknown_state)
        query = globals.db.query(self.table, order_by=self.order_by)
        query.join('LEFT JOIN syndrome_types USING (syndrome_id)')
        query.where('syndrome_id IS NULL OR syndrome_types.enabled')
        for row in query.fetchall():
            try:
                syndvals = by_syndrome[row.syndrome_id]
            except KeyError:
                syndvals = by_syndrome[row.syndrome_id] = SyndromeValues()
                syndvals.add(*unknown_state)
            syndvals.add(row.name, row.label)
            allvals.add(row.name, row.label)
        if None not in by_syndrome:
            syndvals = by_syndrome[None] = SyndromeValues()
            syndvals.add(*unknown_state)
            for name, label in self.defaults:
                syndvals.add(name, label)
                allvals.add(name, label)
        self.by_syndrome = by_syndrome
        self.allvals = SyndromeValues(allvals.in_order())

    def get_syndrome(self, syndrome_id):
        self.refresh()
        if syndrome_id is None:
            return self.allvals
        try:
            return self.by_syndrome[syndrome_id]
        except KeyError:
            return self.by_syndrome[None]

    def get_common(self):
        self.refresh()
        return self.allvals

    def optionexpr(self, *syndrome_ids):
        if not syndrome_ids or syndrome_ids[0] is None:
            return self.get_common()
        elif len(syndrome_ids) == 1:
            return self.get_syndrome(syndrome_ids[0])
        else:
            merged = mergelabels.MergeLabels()
            merged.add(*unknown_state)
            for syndrome_id in syndrome_ids:
                merged.addall(self.get_syndrome(syndrome_id))
            return merged.in_order()

    def get_label(self, syndrome_id, name):
        """
        Given a syndrome and name, return associated label
        """
        return self.get_syndrome(syndrome_id).label(name)

    def normalise(self, syndrome_id, name):
        """
        Given a syndrome name, return canonical form
        """
        return self.get_syndrome(syndrome_id).normalise(name)
