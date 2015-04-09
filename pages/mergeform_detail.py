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
from casemgr import globals, formmerge
from pages import page_common

import config

class PageOps(page_common.PageOpsBase):
    def do_merge(self, ctx, ignore):
        try:
            ctx.locals.formmerge.merge(ctx.locals._credentials)
        except formmerge.FormHasChanged:
            ctx.add_error('A conflicting edit has occurred - redo merge')
            ctx.pop_page()
        else:
            globals.db.commit()
            ctx.add_message('Merged forms')
            # refresh form view
            ctx.locals.formmerge_record.forms.load()
            ctx.pop_page()  # To mergeform
            ctx.pop_page()  # To selmergeforms
            if not ctx.locals.formmerge_record.can_merge_forms():
                ctx.pop_page()  # To case/casecontact

pageops = PageOps()

def page_enter(ctx):
    pass

def page_leave(ctx):
    pass

def page_display(ctx):
    ctx.run_template('mergeform_detail.html')

def page_process(ctx):
    if pageops.page_process(ctx):
        return
