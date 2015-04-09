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

from casemgr import globals, mergelabels, cached

unknown_state = ('', 'Unknown')

class EditAddressStates:

    def __init__(self):
        query = globals.db.query('address_states')
        self.rows = query.fetchall()
        self.sort()

    def new(self, **kwargs):
        row = self.rows.new_row(**kwargs)
        self.rows.append(row)
        return row

    def sort(self):
        self.rows.sort(lambda a, b: cmp(a.code, b.code))

    def __len__(self):
        return len(self.rows)

    def delete(self, index):
        del self.rows[index]

    def __getitem__(self, index):
        return self.rows[index]

    def has_changed(self):
        return self.rows.db_has_changed()

    def update(self):
        self.rows.db_update()


class AddressStates(cached.NotifyCache):
    notification_target = 'address_states'

    def __init__(self):
        cached.NotifyCache.__init__(self)
        self.address_states = []

    def load(self):
        query = globals.db.query('address_states', order_by='label')
        self.address_states[:] = query.fetchcols(('code', 'label'))

    def optionexpr(self):
        self.refresh()
        return [unknown_state] + self.address_states


_address_states = AddressStates()
optionexpr = _address_states.optionexpr
