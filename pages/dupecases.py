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

from casemgr import globals, casedupe, paged_search, casemerge
from pages import page_common
import config

class PageOps(page_common.PageOpsBase):
    
    def do_merge(self, ctx, person_id):
        selmerge = casemerge.by_person_id(ctx.locals._credentials, 
                                          ctx.locals.case_dups.syndrome_id,
                                          int(person_id))
        ctx.push_page('selmergecase', selmerge)


pageops = PageOps()


def page_enter(ctx, syndrome_id, notification_window):
    ctx.locals.case_dups = casedupe.CaseDupeScan(ctx.locals._credentials.prefs,
                                                 syndrome_id, 
                                                 notification_window)
    paged_search.push_pager(ctx, ctx.locals.case_dups)
    ctx.add_session_vars('case_dups')

def page_leave(ctx):
    paged_search.pop_pager(ctx)
    ctx.del_session_vars('case_dups')

def page_display(ctx):
    ctx.run_template('dupecases.html')

def page_process(ctx):
    pageops.page_process(ctx)
