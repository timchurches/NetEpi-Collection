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
from cocklebur import dbobj, form_ui
from casemgr import globals, tasks
from pages import page_common

import config

class ConfirmFormDelete(page_common.ConfirmDelete):
    mode = 'delete'
    title = 'Delete form'
    message = 'Are you sure you wish to delete this form?'
    reason_prompt = 'Reason for deletion:'


class ConfirmFormUndelete(page_common.ConfirmUndelete):
    mode = 'undelete'
    title = 'Undelete form'
    message = 'Are you sure you wish to undelete this form?'


def desc_task(ctx, is_new, **kwargs):
    action = tasks.ACTION_UPDATE_CASE_FORM
    if is_new:
        action = tasks.ACTION_NEW_CASE_FORM
    return dict(kwargs, action = action,
                case_id = ctx.locals.case.case_row.case_id)

class PageOps(page_common.PageOpsBase):
    def validate(self, ctx):
        ctx.locals.form_errors = ctx.locals.edit_form.validate()
        if ctx.locals.form_errors:
            raise page_common.PageError('There are errors in some fields -'
                                        ' please fix them and try again')

    def unsaved_check(self, ctx):
        if ctx.locals.edit_form.has_changed():
            raise page_common.ConfirmSave
    
    def commit(self, ctx):
        self.validate(ctx)
        ctx.locals.case.user_log(ctx.locals.edit_form.db_desc())
        try:
            form_desc = ctx.locals.edit_form.update()
        except globals.ReviewForm:
            ctx.locals.form_data = ctx.locals.edit_form.get_form_data()
            raise
        page_common.task_update(ctx, desc_task(ctx, **form_desc))
        globals.db.commit()
        ctx.locals.case.forms.cache_invalidate()

    def rollback(self, ctx):
        form_desc = ctx.locals.edit_form.abort()
        if form_desc:
            page_common.unlock_desc_task(ctx, desc_task(ctx, **form_desc))

    def do_form_submit(self, ctx, ignore):
        self.commit(ctx)
        if ctx.locals.task and ctx.locals.task.done:
            ctx.set_page('casetask', ctx.locals.case)
        else:        
            ctx.pop_page()

    def do_form_cancel(self, ctx, ignore):
        self.check_unsaved_or_confirmed(ctx)
        self.rollback(ctx)
        ctx.pop_page()

    def do_form_delete(self, ctx, ignore):
        if self.confirmed:
            ctx.locals.edit_form.set_deleted(True, ctx.locals.confirm.reason)
            ctx.locals.case.user_log('Deleted form')
            globals.db.commit()
            ctx.locals.case.forms.cache_invalidate()
            ctx.pop_page()
        else:
            raise ConfirmFormDelete

    def do_form_undelete(self, ctx, ignore):
        if self.confirmed:
            ctx.locals.edit_form.set_deleted(False)
            ctx.locals.case.user_log('Undeleted form')
            globals.db.commit()
            ctx.locals.case.forms.cache_invalidate()
        else:
            raise ConfirmFormUndelete

    def do_showhelp(self, ctx, input_name):
        ctx.locals.showhelp = input_name.replace('_', '.')
        ctx.locals.curnode = ctx.locals.showhelp

    def do_print(self, ctx, ignore):
        ctx.push_page('caseprint')
    
    def do_ownsrc(self, ctx, ignore):
        if self.confirmed:
            ctx.locals.edit_form.take_ownership()
            ctx.locals.case.forms.cache_invalidate()
        else:
            raise page_common.ConfirmUnlock

pageops = PageOps()

def page_enter(ctx, edit_form):
    ctx.locals.edit_form = edit_form
    ctx.locals.form_data = ctx.locals.edit_form.get_form_data()
    ctx.locals.form_errors = form_ui.FormErrors()
    ctx.locals.curnode = ''
    ctx.add_session_vars('edit_form', 'form_data', 'form_errors', 'curnode')

def page_leave(ctx):
    ctx.del_session_vars('edit_form', 'form_data', 'form_errors', 'curnode')

def page_display(ctx):
    if not hasattr(ctx.locals, 'showhelp'):
        ctx.locals.showhelp = ''
    ctx.locals.form_disabled = (ctx.locals.confirm or
                                ctx.locals.case.viewonly() or 
                                ctx.locals.edit_form.viewonly())
    ctx.run_template('caseform.html')

def page_process(ctx):
    pageops.page_process(ctx)
