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
from casemgr import globals
from pages import page_common

import config

class PageOps(page_common.PageOpsBase):
    def commit(self, ctx):
        ctx.locals.ue.save()
        ctx.add_messages(ctx.locals.ue.messages)
        globals.db.commit()
        globals.notify.notify('users', ctx.locals.ue.user.user_id)

    def unsaved_check(self, ctx):
        if ctx.locals.ue.has_changed():
            raise page_common.ConfirmSave

    def do_reset_attempts(self, ctx, ignore):
        ctx.locals.ue.reset_attempts()

    def do_checked(self, ctx, ignore):
        ctx.locals.ue.mark_checked()
        ctx.pop_page()

    def do_update(self, ctx, ignore):
        self.commit(ctx)
        ctx.pop_page()

    def do_key_submit(self, ctx, ignore):
        ctx.locals.ue.load()
        if not ctx.locals.ue.need_key:
            ctx.msg('info', 'Key accepted - enter your details')
        else:
            ctx.msg('err', 'Enter a valid registration key')

pageops = PageOps()


def page_enter(ctx, ue):
    ctx.locals.ue = ue
    ctx.add_session_vars('ue')

def page_leave(ctx):
    ctx.del_session_vars('ue')

def page_display(ctx):
    ctx.run_template('useredit.html')

def page_process(ctx):
    if pageops.page_process(ctx):
        return
