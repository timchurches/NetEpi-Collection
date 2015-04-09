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

from casemgr import persondupecfg
from pages import page_common
import config

class PageOps(page_common.PageOpsBase):
    def do_reset(self, ctx, ignore):
        ctx.locals.dupecfg_group.reset()
        
    def do_back(self, ctx, ignore):
        ctx.locals.dupecfg.apply_group(ctx.locals.dupecfg_group)
        ctx.pop_page()

page_process = PageOps().page_process


def page_enter(ctx, index):
    ctx.locals.dupecfg_group = ctx.locals.dupecfg.edit_group(index)
    ctx.add_session_vars('dupecfg_group')


def page_leave(ctx):
    ctx.del_session_vars('dupecfg_group')


def page_display(ctx):
    ctx.run_template('dupepersons_config_edit.html')
