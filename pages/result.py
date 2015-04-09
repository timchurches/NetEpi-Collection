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
from casemgr import globals, paged_search
from pages import page_common
import config


class PageOps(page_common.PageOpsBase):

    def do_search_op(self, ctx, op, *a):
        ctx.locals.search.search_ops.do(ctx, self.confirmed, op, *a)

    def do_selectnone(self, ctx, ignore):
        ctx.locals.search.result.select([])
        
    def do_selectall(self, ctx, ignore):
        ctx.locals.search.result.select_all()
        

pageops = PageOps()

def page_enter(ctx):
    paged_search.push_pager(ctx, ctx.locals.search.result)

def page_leave(ctx):
    paged_search.pop_pager(ctx)

def page_display(ctx):
    ctx.run_template('result.html')

def page_process(ctx):
    ctx.locals.caseset = None
    if pageops.page_process(ctx):
        return
