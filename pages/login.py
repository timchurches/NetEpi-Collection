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
from casemgr import credentials, globals, user_edit
from pages import page_common
import config


class PageOps(page_common.PageOpsBase):

    def do_login(self, ctx, ignore):
        cred = ctx.locals._credentials
        try:
            cred.authenticate_user(globals.db, ctx.locals.username, 
                                    ctx.locals.password)
        except credentials.DisabledUser, e:
            ctx.msg('warn', '%s. You may update your contact details '
                            'if necessary:' % e)
            ue = user_edit.DisabledEdit(None, e.user.user_id)
            ctx.push_page('useredit', ue)
        except credentials.SelectUnit:
            ctx.set_page('unitselect')
        else:
            ctx.set_page('main')

    def do_register(self, ctx, ignore):
        if config.user_registration_mode == 'register':
            ue = user_edit.SelfRegister(None)
        elif config.user_registration_mode in ('invite', 'sponsor'):
            ue = user_edit.SponsoredRegister(None)
        else:
            return
        ctx.push_page('useredit', ue)

    def do_invite(self, ctx, key):
        ue = user_edit.SponsoredRegister(None, key)
        ctx.push_page('useredit', ue)

pageops = PageOps()

class DummyUnit:
    name = '----'

def page_enter(ctx):
    ctx.locals.has_js = ''
    ctx.add_session_vars('has_js')
    ctx.locals.confirm = None
    ctx.add_session_vars('confirm')
    ctx.locals._credentials = credentials.Credentials()
    ctx.add_session_vars('_credentials')

def page_display(ctx):
    ctx.locals.password = ''
    ctx.locals.unit_options = None
    ctx.set_save_session(False)
    ctx.run_template('login.html')

def page_process(ctx):
    ctx.merge_vars('invite')
    pageops.page_process(ctx)
