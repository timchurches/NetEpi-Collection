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
from casemgr import globals, tasksearch, paged_search, tasks
from pages import page_common, taskaction

import config

class PageOps(page_common.PageOpsBase):
    def do_edit(self, ctx, task_id):
        ctx.locals.paged_search.reset()
        try:
            taskaction.task_dispatch(ctx, int(task_id), ctx.push_page, True)
        except taskaction.TAError, e:
            ctx.add_error(e)

    def do_go(self, ctx, task_id):
        ctx.locals.paged_search.reset()
        try:
            taskaction.task_dispatch(ctx, int(task_id), ctx.set_page)
        except taskaction.TAError, e:
            ctx.add_error(e)

    def do_note(self, ctx, ignore):
        if 'TASKINIT' in ctx.locals._credentials.rights:
            ctx.push_page('notetask')

    def do_results_prev_page(self, ctx, ignore):
        ctx.locals.paged_search.prev()

    def do_results_next_page(self, ctx, ignore):
        ctx.locals.paged_search.next()

pageops = PageOps()


def page_enter(ctx, task_case):
    assert ctx.locals.task is None
    paged_search.push_pager(ctx, tasksearch.TaskSearch(globals.db, 
                                          ctx.locals._credentials,
                                          ctx.locals._credentials.prefs,
                                          case_id=task_case.case_row.case_id))

def page_leave(ctx):
    paged_search.pop_pager(ctx)

def page_display(ctx):
    page_common.unlock_task(ctx)
    ctx.run_template('tasks.html')

def page_process(ctx):
    ctx.locals.paged_search.new_search()
    pageops.page_process(ctx)
