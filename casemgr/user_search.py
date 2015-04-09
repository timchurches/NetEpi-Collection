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
Users searching for other user's contact details
"""

try:
    set
except NameError:
    from sets import Set as set

from cocklebur import dbobj
from casemgr import globals, paged_search
import config

privopts = [
    ('email', 'e-mail address'),
    ('phone_home', 'Home Phone No.'),
    ('phone_work', 'Work Phone No.'),
    ('phone_mobile', 'Mobile Phone No.'),
    ('phone_fax', 'Fax No.'),
]
privcols = set([o[0] for o in privopts])

class Privacy(set):
    def __init__(self, privacy=()):
        if privacy is None or privacy == '!':
            privacy = ()
        if isinstance(privacy, basestring):
            privacy = privacy.split(',')
        set.__init__(self, privacy)


class PrivacyEdit:
    privopts = privopts

    def __init__(self, user_id):
        self.user_id = user_id
        query = globals.db.query('users')
        query.where('user_id = %s', self.user_id)
        rows = query.fetchcols(('privacy',))
        assert len(rows) == 1
        self.privacy = rows[0][0]
        if not self.privacy or self.privacy == '!':
            self.share = 'False'
            self.share_details = []
        else:
            self.share = 'True'
            self.share_details = self.privacy.split(',')

    def update(self):
        if self.share == 'False':
            privacy = '!'
        else:
            privacy = ','.join(self.share_details + ['fullname'])
        if self.privacy != privacy:
            curs = globals.db.cursor()
            dbobj.execute(curs, 'UPDATE users SET privacy=%s WHERE user_id=%s',
                          (privacy, self.user_id))
            globals.db.commit()
            self.privacy = privacy


class UserSearchBase(paged_search.SortablePagedSearch):
    order_by = 'fullname'
    headers = [
        ('fullname', 'Full Name'),
        ('username', 'Username'),
        (None, 'Title/Agency/Expertise'),
        (None, config.unit_label),
        ('email', 'e-mail'),
        (None, 'Phone'),
        (None, 'Fax No.'),
    ]

    def __init__(self, prefs, query=None):
        paged_search.SortablePagedSearch.__init__(self, globals.db, prefs, 
                                                  query, title='User search')

    def row_format(self, row, users_units=None):
        def _field(attr):
            value = getattr(row, attr)
            if value and (attr not in privcols or attr in privacy):
                return value
            return ''
        def _subfields(*a):
            fields = []
            for attr, label in a:
                value = getattr(row, attr)
                if value and (attr not in privcols or attr in privacy):
                    fields.append('%s: %s' % (label, value))
            return fields

        if users_units is None:
            uu = ''
        else:
            uu = users_units[row.user_id].comma_list('name')
        privacy = Privacy(row.privacy)
        return [
            row.fullname, 
            row.username, 
            _subfields(('title', 'Job Title'),
                       ('agency', 'Agency/Employer'),
                       ('expertise', 'Expertise')),
            uu,
            _field('email'),
            _subfields(('phone_work', 'WK'),
                       ('phone_home', 'HM'),
                       ('phone_mobile', 'MOB')),
            _field('phone_fax'),
        ]

    def load_units(self, users):
        user_ids = [u.user_id for u in users]
        users_units = globals.db.participation_table('unit_users',
                                                     'user_id', 'unit_id')
        users_units.preload(user_ids)
        return users_units

    def result_page(self):
        page = []
        rows = paged_search.SortablePagedSearch.result_page(self)
        users_units = self.load_units(rows)
        for row in rows:
            page.append(self.row_format(row, users_units))
        return page

    def yield_rows(self):
        cols = ['fullname', 'username', 'title', 'agency', 'expertise',
                'unit', 'email', 'phone_work', 'phone_home', 'phone_mobile',
                'phone_fax']
        yield cols
        chunk_size = 100
        for i in range(0, len(self.pkeys), chunk_size):
            chunk_keys = self.pkeys[i:i + chunk_size]
            query = self.db.query(self.table)
            rows = query.fetchall_by_keys(chunk_keys)
            users_units = self.load_units(rows)
            for row in rows:
                line = []
                for col in cols:
                    value = ''
                    if col not in privcols or col in Privacy(row.privacy):
                        if col == 'unit':
                            value = users_units[row.user_id].comma_list('name')
                        else:
                            value = getattr(row, col)
                    line.append(value or '')
                yield line


class UserSearch(UserSearchBase):

    def __init__(self, prefs, term=None):
        self.new_query(term)
        UserSearchBase.__init__(self, prefs)

    def new_query(self, term=None):
        self.reset()
        self.term = term
        self.query = globals.db.query('users', order_by=self.order_by)
        #self.query.where('enabled')
        self.query.where('not deleted')
        self.query.where('privacy IS NOT NULL')
        self.query.where("privacy != '!'")
        if self.term:
            if '*' in self.term:
                term_like = dbobj.wild(self.term)
            else:
                term_like = '%%%s%%' % self.term
            orquery = self.query.sub_expr('OR')
            orquery.where('fullname ILIKE %s', term_like)
            orquery.where('username ILIKE %s', term_like)
            orquery.where('title ILIKE %s', term_like)
            orquery.where('agency ILIKE %s', term_like)
            orquery.where('expertise ILIKE %s', term_like)


class UserByUnitSearch(UserSearchBase):
    def __init__(self, prefs, unit_id):
        query = globals.db.query('users', order_by='fullname')
        query.join('JOIN unit_users USING (user_id)')
        query.where('unit_id = %s', unit_id)
        query.where('enabled')
        UserSearchBase.__init__(self, prefs, query)
