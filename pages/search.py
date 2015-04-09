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
from casemgr import globals, search
from pages import page_common

import config

class PageOps(page_common.PageOpsBase):

    def do_search_reset(self, ctx, ignore):
        ctx.locals.search.reset()

    def do_search_go(self, ctx, ignore):
        prefs = ctx.locals._credentials.prefs
        ctx.locals.search.search(ctx.locals)
        ctx.locals.search.search_ops.result(ctx, ctx.locals.search.result)

    def do_cs_recent(self, ctx, idx):
        cs = ctx.locals.casesets.recent_casesets[int(idx)]
        ctx.locals.search.search_ops.result_caseset(ctx, self.confirmed, cs)

    def do_cs_saved(self, ctx, id):
        cs = ctx.locals.casesets.load(int(id))
        ctx.locals.search.search_ops.result_caseset(ctx, self.confirmed, cs)

    def do_tab(self, ctx, tab):
        ctx.locals.search.tabs.select(tab)

    def do_tagbrowse(self, ctx, ignore):
        ctx.push_page('tagbrowse', 'Search tags', 'search.tags')

pageops = PageOps()


def page_enter(ctx, search_ops):
    # Implement a stack of searches
    s = search.Search(search_ops)
    s.saved = ctx.locals.search
    ctx.locals.search = s

def page_leave(ctx):
    if hasattr(ctx.locals, 'search'):
        # Logout clears ctx.locals
        ctx.locals.search = ctx.locals.search.saved

def page_display(ctx):
    ctx.locals.casesets.saved_casesets.refresh()
    ctx.run_template('search.html')

def page_process(ctx):
    ctx.locals.search.save_prefs()
    pageops.page_process(ctx)
