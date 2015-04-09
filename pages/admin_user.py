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
from cocklebur import dbobj, pt
from casemgr import globals, credentials, logview, unituser, user_edit
from pages import page_common
import config


class PageOps(page_common.PageOpsBase):
    def unsaved_check(self, ctx):
        if ctx.locals.pt_search.db_has_changed():
            raise page_common.ConfirmSave
        if ctx.locals.ue.has_changed():
            raise page_common.ConfirmSave

    def commit(self, ctx):
        user = ctx.locals.ue.user
        if user.enabled and not ctx.locals.pt_search:
            raise credentials.CredentialError('Cannot enable a user who is not '
                                              'a member of at least one %s' % 
                                              config.unit_label)
        ctx.locals.ue.save()
        ctx.add_messages(ctx.locals.ue.messages)
        ctx.locals.pt_search.set_key(user.user_id)
        ctx.admin_log(ctx.locals.pt_search.db_desc())
        ctx.locals.pt_search.db_update()
        globals.db.commit()
        globals.notify.notify('users', user.user_id)

    def do_update(self, ctx, ignore):
        ctx.locals.pt_search.clear_search_result()
        self.commit(ctx)
        ctx.pop_page()

    def do_view_log(self, ctx, ignore):
        user = ctx.locals.ue.user
        if not user.is_new():
            log = logview.AdminLogView(ctx.locals._credentials.prefs, 
                                       'Log for user %r' % user.username, 
                                       user_id=user.user_id)
            ctx.push_page('logview', log)

    def do_reset_attempts(self, ctx, ignore):
        ctx.locals.ue.reset_attempts()

    def do_delete(self, ctx, ignore):
        orig_username = ctx.locals.ue.user.username
        ctx.locals.ue.delete()
        ctx.add_message('User %r deleted' % orig_username)

    def do_undelete(self, ctx, ignore):
        ctx.locals.ue.undelete()
        ctx.add_message('User %r undeleted' % ctx.locals.ue.user.username)

    def do_pt_search(self, ctx, op, *args):
        ctx.locals.pt_search.do(op, *args)

pageops = PageOps()


def page_enter(ctx, user_id):
    ctx.locals.ue = user_edit.SystemAdmin(ctx.locals._credentials, user_id)
    user_units = globals.db.ptset('unit_users', 'user_id', 'unit_id', user_id)
    if (not user_units and hasattr(ctx.locals, 'unit') 
        and ctx.locals.unit.unit_id):
        user_units.add_slave_key(ctx.locals.unit.unit_id)
    ctx.locals.pt_search = pt.SearchPT(user_units, 'name', filter='enabled')
    ctx.add_session_vars('ue', 'pt_search')

def page_display(ctx):
    ids = [u.unit_id for u in ctx.locals.pt_search.pt_set]
    ctx.locals.units = unituser.units.fetch(*ids)
    ctx.run_template('admin_user.html')

def page_process(ctx):
    pageops.page_process(ctx)

def page_leave(ctx):
    ctx.del_session_vars('ue', 'pt_search')
