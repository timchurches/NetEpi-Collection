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

from casemgr import globals, casemerge, cases
from pages import page_common, caseset_ops

import config

class PageOps(page_common.PageOpsBase):

    def do_merge(self, ctx, ignore):
        cred = ctx.locals._credentials
        try:
            update_case, delete_case = ctx.locals.casemerge.merge(cred)
        except casemerge.CaseHasChanged:
            ctx.add_error('A conflicting edit has occurred - redo merge')
            ctx.pop_page()
        else:
            globals.db.commit()
            ctx.add_message('Merged System ID %s into %s' % 
                            (delete_case.case_id, update_case.case_id))
            caseset_ops.caseset_remove(ctx, delete_case.case_id)
            # refresh case view
            case = cases.edit_case(cred, update_case.case_id)
            page_common.set_case(ctx, case)
            ctx.pop_page('selmergecase')
            if ctx.locals.case.can_merge_forms():
                ctx.msg('warn', 'Now please check for duplicate forms...')
                ctx.push_page('selmergeforms', ctx.locals.case)


pageops = PageOps()

def page_enter(ctx):
    pass

def page_leave(ctx):
    pass

def page_display(ctx):
    ctx.run_template('mergecase_detail.html')

def page_process(ctx):
    if pageops.page_process(ctx):
        return
