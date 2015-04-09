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

from cocklebur import utils
from casemgr import personmerge, globals, casemerge
from pages import page_common

import config

class PageOps(page_common.PageOpsBase):
    def do_merge(self, ctx, ignore):
        cred = ctx.locals._credentials
        try:
            person, ids = ctx.locals.personmerge.merge(cred)
        except personmerge.PersonHasChanged:
            ctx.add_error('A conflicting edit has occurred - redo merge')
            ctx.pop_page()
            return
        globals.db.commit()
        ctx.add_message('Merged persons associated with System IDs %s'%ids)
        if 'dupepersons' in ctx.locals.__pages__:
            ctx.pop_page('dupepersons')
            #ctx.locals.likely.new_search()
        else:
            ctx.pop_page()  # mergeperson
            ctx.pop_page()
        try:
            selmerge = casemerge.by_person(ctx.locals._credentials, person)
        except casemerge.NoOtherRecords:
            pass
        else:
            ctx.add_message('Now please check for duplicate case/contact records...')
            ctx.push_page('selmergecase', selmerge)



pageops = PageOps()

def page_enter(ctx):
    pass

def page_leave(ctx):
    pass

def page_display(ctx):
    ctx.run_template('mergeperson_detail.html')

def page_process(ctx):
    if pageops.page_process(ctx):
        return
