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
    def do_bulletin_detail(self, ctx, bulletin_id):
        ctx.set_page('bulletin_detail', int(bulletin_id))

    def do_back(self, ctx, ignore):
        ctx.pop_page()

pageops = PageOps()

def page_enter(ctx, bulletin_id):
    ctx.locals.bulletin = ctx.locals.bulletins.get_bulletin(bulletin_id)
    ctx.add_session_vars('bulletin')

def page_display(ctx):
    hide_time = ctx.locals._credentials.prefs.get('bulletin_time')
    ctx.locals.bulletin_list = ctx.locals.bulletins.get_bulletins(hide_time)
    ctx.run_template('bulletin_detail.html')

def page_process(ctx):
    pageops.page_process(ctx)

def page_leave(ctx):
    ctx.del_session_vars('bulletin')
