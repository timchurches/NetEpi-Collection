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

import config

class RightDef:

    def __init__(self, right, label, desc=None):
        self.right = right
        self.label = label
        self.desc = desc

class AvailableRights(list):

    def __init__(self, *defs):
        self.by_right = {}
        self.options = []

    def add(self, *args):
        rightdef = RightDef(*args)
        self.append(rightdef)
        self.options.append((rightdef.right, rightdef.label))
        self.by_right[rightdef.right] = rightdef

    def __getitem__(self, right):
        return self.by_right[right]

    def __contains__(self, right):
        return right in self.by_right


available = AvailableRights()
available.add('ADMIN', 'System Administrator'),
available.add('DATAMGR', 'Data Administrator',
             '%s merging' % config.person_label),
available.add('UNITADMIN', 
             'Administer users in the same %s' % config.unit_label.lower()),
if config.user_registration_mode in ('invite', 'sponsor'):
    available.add('SPONSOR', 'Sponsor new users'),
available.add('ACCESSALL', 'Access all records'),
available.add('ACCESSSYND', 'Access by %s' % config.syndrome_label),
available.add('IMPORT', 'Bulk data import'),
available.add('EXPORT', 'Bulk data export and reporting'),
available.add('PUBREP', 'View-only access to public reports'),
available.add('TQADMIN', 'Administer task queues'),
available.add('VIEWONLY', 'View-Only Case Access'),
available.add('TASKINIT', 'Create new tasks'),


class Rights(set):
    """
    Set-like rights container.

    Can be initialised from a comma-separated list of rights tags or
    another Rights instance and supports the usual set membership,
    union and intersection operations.
    """
    available = available
 
    def __init__(self, rights=None):
        set.__init__(self)
        self.add(rights)
 
    def __str__(self):
        return ','.join(self)
 
    def add(self, rights):
        if rights:
            try:
                rights = rights.split(',')
            except AttributeError:
                pass
            for right in rights:
                set.add(self, right)

    def any(self, *want):
        return bool(self & set(want))


class RMUser:

    def __init__(self, id, name=None, fullname=None):
        self.id = id
        self.name = name
        self.fullname = fullname

    def dump(self):
        print '      User', self.id, '-', self.name, '-', self.fullname


class RMUnit:

    def __init__(self, id, name=None):
        self.id = id
        self.name = name
        self.users = {}

    def sorted_users(self):
        return asu(self.users.itervalues())

    def dump(self):
        print '    Unit', self.id, '-', self.name
        for user in self.sorted_users():
            user.dump()


class RMGroup:

    def __init__(self, id, name=None):
        self.id = id
        self.name = name
        self.units = {}

    def sorted_units(self):
        return asu(self.units.itervalues())

    def dump(self):
        print '  Group', self.id, '-', self.name
        for unit in self.sorted_units():
            unit.dump()


def asu(l):
    al = [(o.name and o.name.lower(), o) for o in l]
    al.sort()
    return [o for n, o in al]


class RightMembers:
    """
    Given a /right/, determine which users, units and groups have that right
    """

    def __init__(self, db, right):
        self.right = right
        self.label = available[right].label
        self.group_by_id = {}
        self.unit_by_id = {}
        self.user_by_id = {}
        self.direct_groups = []
        self.direct_units = []
        self.direct_users = []

        unit_groups = {}
        user_units = {}

        # Scan groups for groups with /right/
        query = db.query('groups')
        cols = 'group_id', 'rights', 'group_name'
        for group_id, rights, name in query.fetchcols(cols):
            rights = Rights(rights)
            if right in rights:
                group = RMGroup(group_id, name)
                self.group_by_id[group_id] = group
                self.direct_groups.append(group)

        # For groups of interest, determine membership
        query = db.query('unit_groups')
        query.where_in('group_id', self.group_by_id)
        for group_id, unit_id in query.fetchcols(('group_id', 'unit_id')):
            unit_groups.setdefault(unit_id, []).append(group_id)

        # Scan units for units with /right/ (directly or via group)
        query = db.query('units')
        query.where('enabled')
        cols = 'unit_id', 'rights', 'name'
        for unit_id, rights, name in query.fetchcols(cols):
            rights = Rights(rights)
            groups = unit_groups.get(unit_id)
            if right in rights or groups:
                unit = RMUnit(unit_id, name)
                self.unit_by_id[unit_id] = unit
                if groups:
                    for group_id in groups:
                        self.group_by_id[group_id].units[unit_id] = unit
                if right in rights:
                    self.direct_units.append(unit)

        # For units of interest, determine membership
        query = db.query('unit_users')
        query.where_in('unit_id', self.unit_by_id)
        for unit_id, user_id in query.fetchcols(('unit_id', 'user_id')):
            user_units.setdefault(user_id, []).append(unit_id)

        # Scan users for users with /right/ (directly or via unit)
        query = db.query('users')
        query.where('(NOT deleted AND enabled)')
        cols = 'user_id', 'rights', 'username', 'fullname'
        for user_id, rights, name, fullname in query.fetchcols(cols):
            rights = Rights(rights)
            units = user_units.get(user_id)
            if right in rights or units:
                user = RMUser(user_id, name, fullname)
                self.user_by_id[user_id] = user
                if units:
                    for unit_id in units:
                        self.unit_by_id[unit_id].users[user_id] = user
                if right in rights:
                    self.direct_users.append(user)

    def sorted_groups(self):
        return asu(self.direct_groups)

    def sorted_units(self):
        return asu(self.direct_units)

    def sorted_users(self):
        return asu(self.direct_users)

    def dump(self):
        print 'Right', self.right, '-', self.label
        print 'Direct groups'
        for group in self.sorted_groups():
            group.dump()
        print 'Direct units'
        for unit in self.sorted_units():
            unit.dump()
        print 'Direct users'
        for user in self.sorted_users():
            user.dump()
