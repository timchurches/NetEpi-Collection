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
from casemgr import globals, tasks
from pages import page_common, taskedit
import config

pageops = taskedit.PageOps()

def page_enter(ctx, task_case, inplace=False):
    case_id = task_case.case_row.case_id
    edittask = tasks.EditTask(globals.db, ctx.locals._credentials, 
                              ctx.locals.task, case_id=case_id, inplace=inplace)
    taskedit.page_enter(ctx, task_case.case_row.syndrome_id, edittask)
    ctx.locals.task_case = task_case
    ctx.add_session_vars('task_case')

def page_leave(ctx):
    taskedit.page_leave(ctx)
    ctx.del_session_vars('task_case')

def page_display(ctx):
    taskedit.page_display(ctx)
    ctx.locals.fh = taskedit.FormsHelper(ctx.locals.task_case, 
                                         ctx.locals.edittask)
    ctx.run_template('casetask.html')

def page_process(ctx):
    if pageops.page_process(ctx):
        return
