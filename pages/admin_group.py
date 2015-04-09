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
from casemgr import credentials, globals, syndrome
from pages import page_common
import config

class PageOps(page_common.PageOpsBase):
    def unsaved_check(self, ctx):
        ctx.locals.group.rights = str(credentials.Rights(ctx.locals.rights))
        if ctx.locals.group.db_has_changed():
            raise page_common.ConfirmSave
            
    def commit(self, ctx):
        group = ctx.locals.group
        if not group.group_name:
            raise page_common.PageError('Please specify a name')
        if not group.description:
            raise page_common.PageError('Please specify a description')
        group.rights = str(credentials.Rights(ctx.locals.rights))
        is_new = group.is_new()
        ctx.admin_log(group.db_desc())
        group.db_update()
        globals.db.commit()
        units = credentials.group_units(globals.db, group.group_id)
        globals.notify.notify('units', *units)

    def do_update(self, ctx, ignore):
        self.commit(ctx)
        ctx.add_message('Updated %r' % ctx.locals.group.group_name)
        ctx.pop_page()

    def do_delete(self, ctx, ignore):
        if not ctx.locals.group.is_new():
            if not self.confirmed:
                raise page_common.ConfirmDelete
            try:
                ctx.locals.group.db_delete()
            except dbobj.ConstraintError:
                ctx.locals.confirm = None
                raise dbobj.ConstraintError('Can\'t delete in-use groups')
            globals.db.commit()
        ctx.add_message('Deleted %s %r' % (config.group_label, ctx.locals.group.group_name))
        ctx.pop_page()

pageops = PageOps()


def page_enter(ctx, group_id):
    if group_id is None:
        ctx.locals.group = globals.db.new_row('groups')
    else:
        query = globals.db.query('groups')
        query.where('group_id = %s', int(group_id))
        ctx.locals.group = query.fetchone()
    ctx.add_session_vars('group')
    ctx.locals.rights = list(credentials.Rights(ctx.locals.group.rights))
    ctx.add_session_vars('rights')

def page_leave(ctx):
    ctx.del_session_vars('group')
    ctx.del_session_vars('rights')

def page_display(ctx):
    query = syndrome.query_by_group(ctx.locals.group.group_id)
    ctx.locals.syndrome_names = query.fetchcols('name')
    ctx.run_template('admin_group.html')

def page_process(ctx):
    if pageops.page_process(ctx):
        return
