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

from casemgr import rights, globals
from pages import page_common
import config

class PageOps(page_common.PageOpsBase):

    def do_edit_user(self, ctx, user_id):
        ctx.push_page('admin_user', int(user_id))

    def do_edit_unit(self, ctx, unit_id):
        ctx.push_page('admin_unit', int(unit_id))

    def do_edit_group(self, ctx, group_id):
        ctx.push_page('admin_group', int(group_id))

page_process = PageOps().page_process


def page_enter(ctx, right):
    ctx.locals.view_right = right
    ctx.add_session_vars('view_right')

def page_leave(ctx):
    ctx.del_session_vars('view_right')

def page_display(ctx):
    ctx.locals.rm = rights.RightMembers(globals.db, ctx.locals.view_right)
    ctx.run_template('admin_view_right.html')
