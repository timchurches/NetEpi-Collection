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
from casemgr import globals, paged_search


class Search:
    name = None
    browse_page = None
    edit_page = None

    def __init__(self):
        self.reset()

    def clear_error(self):
        self.error = ''

    def set_error(self, error):
        if not self.error:
            self.error = str(error)

    def init(self):
        pass

    def reset(self):
        self.init()
        self.clear_error()

    def search(self, prefs):
        self.clear_error()
        try:
            query = self.query()
            rows = query.fetchall()
            if len(rows) == 0:
                return self.set_error('No matches')
            return rows
        except dbobj.DatabaseError, e:
            globals.db.rollback()
            return self.set_error(e)

    def go(self, ctx, prefs):
        rows = self.search(prefs)
        if rows:
            ctx.push_page(self.browse_page, rows)

    def new(self, ctx, prefs):
        ctx.push_page(self.edit_page, None)


class PagedSearch(Search):

    def search(self, prefs):
        self.clear_error()
        try:
            query = self.query()
            search = paged_search.SortablePagedSearch(globals.db, prefs, query)
            if not search.result_count():
                return self.set_error(search.error or 'No matches')
            return search
        except dbobj.DatabaseError, e:
            globals.db.rollback()
            return self.set_error(e)

    def go(self, ctx, prefs):
        rows = self.search(prefs)
        if rows:
            if len(rows) == 1:
                ctx.push_page(self.edit_page, *rows.pkeys[0])
            else:
                ctx.push_page(self.browse_page, rows)


class UserSearch(PagedSearch):
    name = 'user'
    browse_page = 'admin_users'
    edit_page = 'admin_user'

    def init(self):
        self.name = self.fullname = self.unit = self.title = self.sponsor = ''
        self.enabled = 'enabled'

    def query(self):
        query = globals.db.query('users', order_by='users.username')
        if self.enabled == 'enabled':
            query.where('users.enabled')
        elif self.enabled == 'disabled':
            query.where('not users.enabled')
        if self.enabled == 'deleted':
            query.where('users.deleted')
            if self.name and self.name[-1] not in '*%':
                self.name += '*'
        else:
            query.where('not users.deleted')
        if self.name:
            query.where('users.username ILIKE %s', dbobj.wild(self.name))
        if self.fullname:
            query.where('users.fullname ILIKE %s', dbobj.wild(self.fullname))
        if self.title:
            query.where('users.title ILIKE %s', dbobj.wild(self.title))
        if self.unit:
            query.join('JOIN unit_users USING (user_id)')
            query.join('JOIN units USING (unit_id)')
            query.where('units.name ILIKE %s', dbobj.wild(self.unit))
        if self.sponsor:
            query.join('JOIN users AS su'
                       ' ON (su.user_id = users.sponsoring_user_id)')
            or_expr = query.sub_expr('OR')
            or_expr.where('su.username ILIKE %s', dbobj.wild(self.sponsor))
            or_expr.where('su.fullname ILIKE %s', dbobj.wild(self.sponsor))
        return query


class UnitSearch(PagedSearch):
    name = 'unit'
    browse_page = 'admin_units'
    edit_page = 'admin_unit'

    def init(self):
        self.name = self.group_id = ''
        self.enabled = 'enabled'

    def query(self):
        query = globals.db.query('units', order_by='name')
        if self.enabled == 'enabled':
            query.where('enabled = True')
        elif self.enabled == 'disabled':
            query.where('enabled = False')
        if self.name:
            query.where('name ILIKE %s', dbobj.wild(self.name))
        if self.group_id:
            query.join('JOIN unit_groups USING (unit_id)')
            query.where('group_id = %s', int(self.group_id))
        return query


class GroupSearch(PagedSearch):
    name = 'group'
    browse_page = 'admin_groups'
    edit_page = 'admin_group'

    def init(self):
        self.group_id = ''

    def query(self):
        return globals.db.query('groups', order_by = 'group_name')

    def go(self, ctx, prefs):
        if self.group_id:
            ctx.push_page(self.edit_page, self.group_id)
        else:
            PagedSearch.go(self, ctx, prefs)


class SyndromeSearch(PagedSearch):
    name = 'syndrome'
    browse_page = 'admin_syndromes'
    edit_page = 'admin_syndrome'

    def init(self):
        self.group_id = ''
        self.name = ''
        self.enabled = 'enabled'

    def query(self):
        query = globals.db.query('syndrome_types', order_by='name')
        if self.name:
            query.where('name ILIKE %s', dbobj.wild(self.name))
        if self.enabled == 'enabled':
            query.where('enabled = True')
        elif self.enabled == 'disabled':
            query.where('enabled = False')
        if self.group_id:
            query.join('JOIN group_syndromes USING (syndrome_id)')
            query.where('group_id = %s', int(self.group_id))
        return query


class QueueSearch(PagedSearch):
    name = 'queue'
    browse_page = 'admin_queues'
    edit_page = 'admin_queue'

    def init(self):
        self.name = ''

    def query(self):
        query = globals.db.query('workqueues', order_by = 'name')
        query.where('user_id is null AND unit_id is null')
        if self.name:
            name_like = dbobj.wild(self.name)
            query.where('name ILIKE %s or description ILIKE %s', 
                name_like, name_like)
        return query


class BulletinSearch(PagedSearch):
    name = 'bulletin'
    browse_page = 'admin_bulletins'
    edit_page = 'admin_bulletin'

    def init(self):
        self.title = self.group_id = self.before = self.after = ''

    def query(self):
        query = globals.db.query('bulletins', order_by='post_date')
        if self.title:
            or_query = query.sub_expr('OR')
            or_query.where('title ILIKE %s', dbobj.wild(self.title))
            or_query.where('synopsis ILIKE %s', dbobj.wild(self.title))
        if self.group_id:
            query.join('JOIN group_bulletins USING (bulletin_id)')
            query.where('group_id = %s', int(self.group_id))
        if self.before:
            query.where('post_date < %s', self.before)
        if self.after:
            query.where('post_date > %s', self.after)
        return query


class FormSearch(PagedSearch):
    name = 'form'
    browse_page = 'admin_forms'
    edit_page = 'admin_form_edit'

    def init(self):
        self.syndrome_id = self.form = ''

    def query(self):
        query = globals.db.query('forms', order_by = 'label')
        if self.form:
            form_like = dbobj.wild(self.form)
            query.where('forms.label ILIKE %s or forms.name ILIKE %s',
                        form_like, form_like)
        if self.syndrome_id:
            query.join('JOIN syndrome_forms'
                       ' ON (syndrome_forms.form_label = forms.label)')
            query.where('syndrome_forms.syndrome_id = %s', int(self.syndrome_id))
        return query


class Searches(list):
    searches = [
        GroupSearch,
        SyndromeSearch,
        FormSearch,
        UnitSearch,
        UserSearch,
        QueueSearch,
        BulletinSearch,
    ]

    def __init__(self):
        for cls in self.searches:
            search = cls()
            self.append(search)
            setattr(self, cls.name, search)
        self.reset()

    def reset(self):
        self.group_id = ''
        for search in self:
            search.reset()

    def clear_errors(self):
        for search in self:
            search.clear_error()

    def search(self, ctx, name, prefs):
        search = getattr(self, name)
        search.group_id = self.group_id
        search.go(ctx, prefs)

    def new(self, ctx, name, prefs):
        search = getattr(self, name)
        search.new(ctx, prefs)
