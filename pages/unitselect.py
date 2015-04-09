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

# NOTE - this page module is a sub-function of the "login" module, and shares
# the login page template. It gets called on login if the user is a member of
# multiple units, and has not already chosen a unit.

from casemgr import globals
from pages import page_common
import config

class PageOps(page_common.PageOpsBase):

    def do_login(self, ctx, ignore):
        cred = ctx.locals._credentials
        assert cred.user
        if not ctx.locals.unit_id:
            raise page_common.PageError('Please select a unit')
        cred.set_unit(globals.db, int(ctx.locals.unit_id))
        ctx.set_page('main')

page_process = PageOps().page_process

def page_enter(ctx):
    ctx.locals.unit_options = list(ctx.locals._credentials.unit_options)
    choose = ('', '(select a %s)' % config.unit_label.lower())
    ctx.locals.unit_options.insert(0, choose)
    ctx.locals.unit_id = ''
    ctx.add_session_vars('unit_options', 'unit_id')

def page_leave(ctx):
    ctx.del_session_vars('unit_options', 'unit_id')

def page_display(ctx):
    ctx.locals.username = ctx.locals._credentials.user.username
    ctx.run_template('login.html')
