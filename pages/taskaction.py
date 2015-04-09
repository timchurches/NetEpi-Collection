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

"""
Given a task_id, this code loads and locks the task, sets up preconditions
for the action, and dispatches to the appropriate page.
"""

from cocklebur import form_ui
from casemgr import globals, tasks, cases

import page_common

import config

class TAError(Exception): pass

def task_dispatch(ctx, task_id, set_page, edit=False):
    cred = ctx.locals._credentials
    if 'VIEWONLY' in cred.rights:
        task = tasks.UnlockedTask(globals.db, cred, task_id)
    else:
        ctx.locals.task = task = tasks.LockedTask(globals.db, cred, task_id)
    try:
        case = ef = None
        if task.action in tasks.action_req_case:
            if task.case_id is None:
                raise TAError('Case has been deleted')
            case = ctx.locals.case
            if case is None or case.case_row.case_id != task.case_id:
                case = cases.edit_case(cred, task.case_id)
                page_common.set_case(ctx, case)
        if task.action in tasks.action_req_form_name:
            if task.form_name is None:
                raise TAError('Form definition has been deleted')
            if task.action in tasks.action_req_summary_id:
                if task.summary_id is None:
                    raise TAError('Form instance has been deleted')
                ef = case.edit_form(task.summary_id)
            else:
                form = case.getform(task.form_name)
                if not form.allow_new_form() and form.summaries:
                    raise TAError('Form has already been created')
                ef = case.new_form(task.form_name)
        if edit:
            if task.action == tasks.ACTION_NOTE:
                set_page('notetask', edit)
            else:
                set_page('casetask', case, True)
        else:
            if task.action == tasks.ACTION_NOTE:
                set_page('notetask', edit)
            elif task.action in tasks.action_case_edit:
                set_page('case')
            elif task.action in tasks.action_form_edit:
                set_page('caseform', ef)
            else:
                raise TAError('This action is not implemented at this time')
        globals.db.commit()
    except (TAError, form_ui.FormError), e:
        ctx.add_error(e)
        task.annotation = '[%s]\n%s' % (e, task.annotation or '')
        task.action == tasks.ACTION_NOTE
        ta(ctx, task, set_page, edit=True)
