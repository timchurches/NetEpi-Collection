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
from casemgr.admin import dropsyndrome

from pages import page_common

import config

class PageOps(page_common.PageOpsBase):
    def do_delete(self, ctx, ignore):
        ctx.locals.drop_syndrome.delete(ctx.locals.drop_syndrome.case_count,
                                        ctx.locals.drop_syndrome.form_count)
        globals.db.commit()
        ctx.pop_page()
        ctx.pop_page()

pageops = PageOps()

def page_enter(ctx):
    syndrome_id = ctx.locals.syndrome.syndrome_id
    ctx.locals.drop_syndrome = dropsyndrome.DropSyndrome(syndrome_id)
    ctx.add_session_vars('drop_syndrome')

def page_leave(ctx):
    ctx.del_session_vars('drop_syndrome')

def page_display(ctx):
    try:
        ctx.locals.drop_syndrome.update_counts()
    except globals.Error, e:
        ctx.add_error(e)
    ctx.run_template('admin_synd_drop.html')

def page_process(ctx):
    pageops.page_process(ctx)
