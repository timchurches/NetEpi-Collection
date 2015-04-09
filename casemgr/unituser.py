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
Read-only cache of units and users

Note that we defer importing "globals" until it's needed, as parts of this code
are used by the initial installer, and globals in not valid in that context.

"""

from casemgr.rights import Rights

NULL_UNIT_ID = NULL_USER_ID = NULL_ID = -1

class DummyUnit:
    name = '---'
    unit_id = NULL_UNIT_ID
    rights = Rights()


class DummyUser:
    user_id = NULL_USER_ID
    username = '---'
    fullname = '---'
    rights = Rights()


class CacheUser(object):
    def apply(self, dbrow):
        self.user_id = dbrow.user_id
        self.username = dbrow.username
        self.fullname = dbrow.fullname
        self.rights = Rights(dbrow.rights)

    def __nonzero__(self):
        return self.user_id != NULL_USER_ID


class CacheUnit(object):
    def apply(self, dbrow):
        self.unit_id = dbrow.unit_id
        self.name = dbrow.name
        self.unit_rights = dbrow.rights
        self._rights = None
        self._groups = None

    def __nonzero__(self):
        return self.unit_id != NULL_UNIT_ID

    def _load_group_rights(self):
        from globals import db
        rights = Rights(self.unit_rights)
        groups = []
        query = db.query('groups')
        query.join('LEFT JOIN unit_groups USING (group_id)')
        query.where('unit_groups.unit_id = %s', self.unit_id)
        for group, grights in query.fetchcols(('group_name', 'rights')):
            groups.append(group)
            rights.add(grights)
        self._groups = groups
        self._rights = rights

    def _get_groups(self):
        if self._groups is None:
            self._load_group_rights()
        return self._groups
    groups = property(_get_groups)

    def _get_rights(self):
        if self._rights is None:
            self._load_group_rights()
        return self._rights
    rights = property(_get_rights)


class Refresher:
    def __init__(self):
        self.by_id = {}
        self.subscribed = False

    def notification(self, *args):
        try:
            ids = map(int, args)
        except ValueError:
            return
        self.load(*ids)

    def add(self, row):
        id = getattr(row, self.id_col)
        if id != NULL_ID and not self.subscribed:
            from globals import notify
            self.subscribed = True
            if not notify.subscribe(self.entity_name, self.notification):
                # XXX Notification not available - use time based refresh?
                pass
        try:
            inst = self.by_id[id]
        except KeyError:
            inst = self.by_id[id] = self.inst_class()
        inst.apply(row)
        return inst

    def load(self, *ids):
        from globals import db
        query = db.query(self.entity_name)
        query.where_in(self.id_col, ids)
        for row in query.fetchall():
            self.add(row)

    def fetch(self, *ids):
        missing = [id for id in ids if id not in self.by_id]
        self.load(*missing)
        return [self.by_id[id] for id in ids]

    def __getitem__(self, id):
        try:
            return self.by_id[id]
        except KeyError:
            self.load(id)
            return self.by_id[id]


class UserCache(Refresher):
    entity_name = 'users'
    id_col = 'user_id'
    inst_class = CacheUser

users = UserCache()
null_user = users.add(DummyUser())


class UnitCache(Refresher):
    entity_name = 'units'
    id_col = 'unit_id'
    inst_class = CacheUnit

units = UnitCache()
null_unit = units.add(DummyUnit())
