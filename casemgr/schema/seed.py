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

def check(db, table, **key):
    """
    Checks to see if the row uniquely identified by the key-value pairs
    exists, and if not, yields up a single new row with the key-values
    pre-populated.
    """
    query = db.query(table)
    for k, v in key.iteritems():
        query.where('%s=%%s' % k, v)
    if query.fetchone() is None:
        row = db.new_row(table)
        for k, v in key.iteritems():
            setattr(row, k, v)
        yield row


def if_empty_insert(db, table, data, *cols):
    """
    If the named table has no rows, then insert the given list of row
    tuples into the named columns.
    """
    if db.query(table, limit=1).fetchone() is None:
        cmd = 'INSERT INTO %s (%s) VALUES (%s)' %\
            (table, ','.join(cols), ','.join(['%s'] * len(cols)))
        curs = db.cursor()
        try:
            for row in data:
                dbobj.execute(curs, cmd, row)
        finally:
            curs.close()


def seed_db(db):
    """
    Create essential entities, such as the admin user, unit and group
    """
    for user in check(db, 'users', username='admin'):
        from casemgr import credentials
        import getpass
        user = db.new_row('users')
        user.user_id = 0
        user.enabled = True
        user.rights = 'ADMIN'
        user.username = 'admin'
        user.fullname = 'Administrator'
        user.role = 'Administrator'
        while 1:
            pwd = credentials.NewPass()
            print 'Setting initial administrator password'
            pwd.new_a = getpass.getpass('Administrator password: ')
            pwd.new_b = getpass.getpass('Re-enter administrator password: ')
            try:
                pwd.set(user)
            except credentials.PasswordError, e:
                print str(e)
            else:
                user.db_update()
                break

    # Admin unit
    for unit in check(db, 'units', unit_id=0):
        unit.enabled = True
        unit.name = 'Administrator Unit'
        unit.db_update()

    # Admin group
    for group in check(db, 'groups', group_id=0):
        group.group_name = 'Administrator Group'
        group.rights = 'ACCESSALL,EXPORT'
        group.description = 'Administrator Group'
        group.db_update()

    # unit_groups
    for unit_group in check(db, 'unit_groups', unit_id=0, group_id=0):
        unit_group.db_update()

    # unit_users
    for unit_user in check(db, 'unit_users', unit_id=0, user_id=0):
        unit_user.db_update()

    # address_states (this is Australia-specific, but serves as an example, and
    # can be overridden from within the admin interface)
    states = [
        ('NSW', 'New South Wales'), 
        ('ACT', 'Australian Capital Territory'), 
        ('NT', 'Northern Territory'),
        ('QLD', 'Queensland'), 
        ('SA', 'South Australia'), 
        ('TAS', 'Tasmania'), 
        ('VIC', 'Victoria'),
        ('WA', 'Western Australia'),
    ]
    if_empty_insert(db, 'address_states', states, 'code', 'label')
    # case assignments (this is NSWDoH-specific, but serves as an example, and
    # can be overridden from within the admin interface)
    assignments = [
        ('GSAHS_G', 'Greater Southern AHS (Goulburn)'),
        ('GSAHS_A', 'Greater Southern AHS (Albury)'),
        ('GWAHS_BH', 'Greater Western AHS (Broken Hill)'),
        ('GWAHS_D', 'Greater Western AHS (Dubbo)'),
        ('GWAHS_B', 'Greater Western AHS (Bathurst)'),
        ('HNEAHS_N', 'Hunter/New England AHS (Newcastle)'),
        ('HNEAHS_T', 'Hunter/New England AHS (Tamworth)'),
        ('JH', 'Justice Health Service'),
        ('NCAHS_PM', 'North Coast AHS (Port Macquarie)'),
        ('NCAHS_L', 'North Coast AHS (Lismore)'),
        ('NSCCAHS_H', 'Northern Sydney/Central Coast AHS (Hornsby)'),
        ('NSCCAHS_G', 'Northern Sydney/Central Coast AHS (Gosford)'),
        ('SESIAHS_R', 'South Eastern Sydney/Illawarra AHS (Randwick)'),
        ('SESIAHS_W', 'South Eastern Sydney/Illawarra AHS (Wollongong)'),
        ('SSWAHS_C', 'Sydney South West AHS (Camperdown)'),
        ('SWAHS_PA', 'Sydney West AHS (Parramatta)'),
        ('SWAHS_PE', 'Sydney West AHS (Penrith)'),
        ('OTHER', 'Other'),
    ]
    if_empty_insert(db, 'syndrome_case_assignments', assignments, 'name', 'label')
    #
    from casemgr.nicknames import nicknames
    if_empty_insert(db, 'nicknames', nicknames, 'nick', 'alt')
    # contact_types
    contact_types = [
        ('Household',),
        ('Workplace/School',),
    ]
    if_empty_insert(db, 'contact_types', contact_types, 'contact_type')
