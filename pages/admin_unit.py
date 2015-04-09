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
from cocklebur.foreign_key import ForeignKeySearch
from cocklebur.pt import SelectPT
from casemgr import globals, paged_search, credentials
from pages import page_common
import config

class PageOps(page_common.PageOpsBase):
    def unsaved_check(self, ctx):
        ctx.locals.unit.rights = str(credentials.Rights(ctx.locals.urights))
        if ctx.locals.group_edit.db_has_changed():
            raise page_common.ConfirmSave
        if ctx.locals.unit.db_has_changed():
            raise page_common.ConfirmSave

    def commit(self, ctx):
        unit = ctx.locals.unit
        if unit.name:
            unit.name = unit.name.strip()
        if not unit.name:
            raise page_common.PageError('A unit name must be given')
        unit.rights = str(credentials.Rights(ctx.locals.urights))
        ctx.admin_log(unit.db_desc())
        unit.db_update()
        ctx.locals.group_edit.set_key(unit.unit_id)
        ctx.admin_log(ctx.locals.group_edit.db_desc())
        ctx.locals.group_edit.db_update()
        globals.db.commit()
        ctx.add_message('Updated %s %r' % (config.unit_label.lower(), unit.name))
        globals.notify.notify('units', unit.unit_id)
        globals.notify.notify('unit_groups', unit.unit_id)
        globals.notify.notify('syndrome_units', unit.unit_id)

    def revert(self, ctx):
        ctx.locals.group_edit.db_revert()
        ctx.locals.unit.db_revert()

    def do_update(self, ctx, ignore):
        self.commit(ctx)
        ctx.pop_page()

    def do_users(self, ctx, ignore):
        prefs = ctx.locals._credentials.prefs
        query = globals.db.query('users', order_by='username')
        query.join('JOIN unit_users USING (user_id)')
        query.where('unit_users.unit_id = %s', ctx.locals.unit.unit_id)
        query.where('not users.deleted')
        search = paged_search.SortablePagedSearch(globals.db, prefs, query)
        ctx.push_page('admin_users', search)

    def do_contact_user_select_go(self, ctx, ignore):
        contact_user_select = ctx.locals.contact_user_select
        contact_user_select.new_query()
        contact_user_select.query.join('JOIN unit_users USING (user_id)')
        contact_user_select.query.where('enabled = True')
        contact_user_select.query.where('unit_users.unit_id = %s', 
                                        ctx.locals.unit.unit_id)
        contact_user_select.fetchall()

    def do_contact_user_select_cancel(self, ctx, ignore):
        ctx.locals.contact_user_select.reset()

    def do_contact(self, ctx, user_id):
        ctx.locals.unit.contact_user_id = int(user_id)
        ctx.locals.contact_user_select.reset()

    def do_delete(self, ctx, ignore):
        credentials.delete_unit(ctx.locals.unit)
        globals.db.commit()
        ctx.add_message('Deleted unit %r' % ctx.locals.unit.name)
        ctx.pop_page()

    def do_group_edit(self, ctx, op, *args):
        ctx.locals.group_edit.do(op, *args)

pageops = PageOps()


def page_enter(ctx, unit_id):
    if unit_id is None:
        ctx.locals.unit = globals.db.new_row('units')
    else:
        query = globals.db.query('units')
        query.where('unit_id = %s', unit_id)
        ctx.locals.unit = query.fetchone()
    ctx.locals.group_pt = globals.db.ptset('unit_groups', 
                                           'unit_id', 'group_id', unit_id)
    ctx.locals.group_pt.get_slave_cache().preload_all()
    ctx.locals.group_edit = SelectPT(ctx.locals.group_pt, 'group_name')
    ctx.locals.contact_user_select = ForeignKeySearch(ctx.locals.unit,
                                                      'contact_user_id',
                                                      ('username', 'fullname'))
    ctx.locals.urights = list(credentials.Rights(ctx.locals.unit.rights))
    ctx.add_session_vars('unit', 'group_pt', 'group_edit', 
                         'contact_user_select', 'urights')

def page_leave(ctx):
    ctx.del_session_vars('unit', 'group_pt', 'group_edit', 
                         'contact_user_select', 'urights')

def page_display(ctx):
    ctx.run_template('admin_unit.html')

def page_process(ctx):
    pageops.page_process(ctx)
