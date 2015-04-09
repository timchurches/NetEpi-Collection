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

from pages import page_common
from casemgr.dataimp import Error
from casemgr.dataimp.editor import CHOOSE

import config

class PageOps(page_common.PageOpsBase):

    def do_setaction(self, ctx, action):
        ctx.locals.editfield.set_action(action)

    def do_add_translate(self, ctx, mode):
        ctx.locals.editfield.add_translate(mode == 'regexp')

    def do_del_translate(self, ctx, index):
        ctx.locals.editfield.del_translate(int(index))

    def do_add_field_opts(self, ctx, index):
        colvals = ctx.locals.editfield.colvalues(ctx.locals.dataimp_src)
        ctx.locals.editfield.add_field_opts(colvals)

    def do_okay(self, ctx, ignore):
        ctx.locals.editor.save_edit_field(ctx.locals.editfield)
        ctx.pop_page()

    def do_back(self, ctx, ignore):
        ctx.pop_page()

def page_process(ctx):
    try:
        ctx.locals.editfield.trial_translate(ctx.locals.dataimp_src)
    except Error, e:
        ctx.add_error(e)
    PageOps().page_process(ctx)

def page_enter(ctx, group_name, field_name):
    ctx.locals.editfield = ctx.locals.editor.edit_field(group_name, field_name)
    ctx.add_session_vars('editfield')

def page_leave(ctx):
    ctx.del_session_vars('editfield')

def page_display(ctx):
    ctx.run_template('dataimp_editfield.html')

