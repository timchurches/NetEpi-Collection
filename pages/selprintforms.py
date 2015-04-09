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
from cocklebur import dbobj
from casemgr import globals, printforms

import config

class PageOps(page_common.PageOpsBase):
    def page_process(self, ctx):
        ctx.locals.forms.refresh()
        page_common.PageOpsBase.page_process(self, ctx)

    def do_select_all(self, ctx, ignore):
        ctx.locals.forms.select_all()

    def do_clear_all(self, ctx, ignore):
        ctx.locals.forms.clear()

    def do_okay(self, ctx, ignore):
        ctx.locals.forms.check_forms()
        ctx.push_page('printforms')

page_process = PageOps().page_process


def page_enter(ctx, syndrome_id):
    ctx.locals.forms = printforms.Forms(syndrome_id)
    ctx.add_session_vars('forms')

def page_leave(ctx):
    ctx.del_session_vars('forms')

def page_display(ctx):
    ctx.run_template('selprintforms.html')
