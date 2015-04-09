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

class GroupEdit:
    def __init__(self, db, group_membership):
        self.group_membership = group_membership
        self.group_map = {}
        for group in db.query('groups').fetchall():
            self.group_map[group.group_id] = group.group_name
        self.excluded = self.group_map.copy()
        self.included = {}
        for group in self.group_membership:
            group_id = group.group_id
            try:
                del self.excluded[group_id]
            except KeyError:
                pass
            self.included[group_id] = self.group_map[group_id]
        self.include_group = []
        self.exclude_group = []

    def get_included(self):
        included = [(v, k) for k, v in self.included.items()]
        included.sort()
        return [(k, v) for v, k in included]

    def get_excluded(self):
        excluded = [(v, k) for k, v in self.excluded.items()]
        excluded.sort()
        return [(k, v) for v, k in excluded]

    def page_process(self, ctx):
        if ctx.req_equals('groups_add'):
            for group_id in self.include_group:
                group_id = int(group_id)
                name = self.excluded[group_id]
                del self.excluded[group_id]
                self.included[group_id] = name
        if ctx.req_equals('groups_del'):
            for group_id in self.exclude_group:
                group_id = int(group_id)
                name = self.included[group_id]
                del self.included[group_id]
                self.excluded[group_id] = name

    def db_update(self):
        add_groups = self.included.copy()
        for gm in tuple(self.group_membership):
            if self.excluded.has_key(gm.group_id):
                self.group_membership.remove(gm)
            else:
                try:
                    del add_groups[gm.group_id]
                except KeyError:
                    pass
        for group_id in add_groups.keys():
            gm = self.group_membership.new_row()
            self.new_member(gm)
            gm.group_id = group_id
            self.group_membership.append(gm)
        self.group_membership.db_update()

    def db_revert(self):
        self.group_membership.db_revert()
