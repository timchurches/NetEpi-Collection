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

from cocklebur import form_ui
from casemgr import formmerge
from pages import page_common

import config

class PageOps(page_common.PageOpsBase):
    def do_showmerge(self, ctx, ignore):
        if not ctx.locals.key_a or not ctx.locals.key_b:
            raise page_common.PageError('Select an A and B form')
        key_a = int(ctx.locals.key_a)
        key_b = int(ctx.locals.key_b)
        if key_a == key_b:
            raise page_common.PageError('Select separate A and B forms')
        case_id = ctx.locals.formmerge_record.case_row.case_id
        merge = formmerge.FormMerge(case_id, key_a, key_b)
        ctx.push_page('mergeform', merge)

pageops = PageOps()

def page_enter(ctx, formmerge_record):
    ctx.locals.formmerge_record = formmerge_record
    ctx.add_session_vars('formmerge_record')

def page_leave(ctx):
    ctx.del_session_vars('formmerge_record')

def page_display(ctx):
    ctx.run_template('selmergeforms.html')

def page_process(ctx):
    if pageops.page_process(ctx):
        return

