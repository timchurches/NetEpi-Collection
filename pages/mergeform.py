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

import config

class PageOps(page_common.PageOpsBase):
    def do_showmerge(self, ctx, ignore):
        if not ctx.locals.formmerge.validate():
            ctx.add_error('Fix field errors first')
        else:
            ctx.push_page('mergeform_detail')

    def do_edit(self, ctx, index):
        ctx.locals.formmerge.toggle_edit(int(index))

pageops = PageOps()

def page_enter(ctx, formmerge):
    ctx.locals.formmerge = formmerge
    ctx.locals.form_data = formmerge.form_data
    ctx.add_session_vars('formmerge', 'form_data')

def page_leave(ctx):
    ctx.del_session_vars('formmerge', 'form_data')

def page_display(ctx):
    ctx.locals.form_disabled = False
    ctx.run_template('mergeform.html')

def page_process(ctx):
    if pageops.page_process(ctx):
        return

