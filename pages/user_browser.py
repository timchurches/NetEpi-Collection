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

from casemgr import user_search, paged_search
from pages import page_common

import config

class PageOps(page_common.PageOpsBase):

    def do_export(self, ctx, ignore):
        page_common.csv_download(ctx, ctx.locals.paged_search.yield_rows(),
                                 'users.csv')

    def page_process(self, ctx):
        if page_common.PageOpsBase.page_process(self, ctx):
            return
        if ctx.locals.term != ctx.locals.paged_search.term:
            ctx.locals.paged_search.new_query(ctx.locals.term)

page_process = PageOps().page_process


def page_enter(ctx):
    search = user_search.UserSearch(ctx.locals._credentials.prefs)
    paged_search.push_pager(ctx, search)

def page_leave(ctx):
    paged_search.pop_pager(ctx)

def page_display(ctx):
    if not page_common.send_download(ctx):
        ctx.run_template('user_browser.html')
