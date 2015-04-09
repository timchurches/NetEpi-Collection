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
from cocklebur import dbobj, tablesearch, form_ui
from casemgr import globals, tasks, cases, taskdesc
from pages import page_common
import config

def assign_search(ctx, table, col, mode, **kwargs):
    search = tablesearch.TableSearch(globals.db, table, col, **kwargs)
    ctx.locals.assign_search = search
    ctx.locals.edittask.assignee.assign_type = mode

def row_select(op, row):
    keys = [str(k) for k in row.get_keys()]
    return ':'.join([op] + keys)

class PageOps(page_common.PageOpsBase):
    def rollback(self, ctx):
        ctx.locals.edittask = None

    def commit(self, ctx):
        ctx.locals.edittask.update(globals.db)
        globals.db.commit()
        ctx.locals.task = None
  
    def msg(self, ctx, op):
        ctx.add_message('%s %r task' % (op, 
                        ctx.locals.edittask.task_description))

    def do_close(self, ctx, ignore):
        ctx.locals.edittask.close(globals.db)
        globals.db.commit()
        self.msg(ctx, 'Closed')
        ctx.locals.task = None
        ctx.pop_page()

    def do_delete(self, ctx, ignore):
        ctx.locals.edittask.delete(globals.db)
        globals.db.commit()
        self.msg(ctx, 'Deleted')
        ctx.locals.task = None
        ctx.pop_page()

    def do_update(self, ctx, ignore):
        self.commit(ctx)
        if ctx.locals.edittask.inplace:
            self.msg(ctx, 'Updated')
        else:
            self.msg(ctx, 'Created')
        ctx.pop_page()

    def do_search_unit(self, ctx, ignore):
        assign_search(ctx, 'units', 'name', 'unit',
                      filter='enabled',
                      title='Assign task to ' + config.unit_label,
                      info_page=True)

    def do_search_user(self, ctx, ignore):
        assign_search(ctx, 'users', 'username', 'user',
                      showcols=('username', 'fullname'),
                      filter='enabled',
                      title='Assign task to user')

    def do_search_assign(self, ctx, id):
        if ctx.locals.assign_search.table == 'units':
            ctx.locals.edittask.assignee.unit_id = int(id)
        else:
            ctx.locals.edittask.assignee.user_id = int(id)
        ctx.locals.assign_search = None

    def do_search_info(self, ctx, id):
        ctx.push_page('unitview', id)

    def do_as(self, ctx, op, *args):
        ctx.locals.assign_search.do(op, *args)

    def do_cancel_search(self, ctx, ignore):
        ctx.locals.assign_search = None

    def do_apply_desc(self, ctx, ignore):
        params = taskdesc.params(ctx.locals.task_synd_id, 
                                 ctx.locals.popular_tasks)
        if config.debug:
            p = ['%s=%s' % kv for kv in params.items()]
            ctx.log('task params: %s' % ', '.join(p))
        ctx.locals.edittask.set_params(globals.db, **params)


class FormsHelper:
    def __init__(self, case, task):
        self.forms = []
        self.selected_form = None
        self.form_instances = None
        if case:
            self.forms.append(('None', 'No form'))
            for form in case.forms:
                self.forms.append((form.label, form.name))
            if task.form_name and task.form_name != 'None':
                try:
                    form = case.getform(task.form_name)
                except form_ui.FormError, e:
                    task.form_name = None
                    return
                self.selected_form = form.name
                self.form_instances = []
                if form.allow_new_form():
                    self.form_instances.append((None, '', 'New form'))
                for summary in form.summaries:
                    self.form_instances.append((summary.summary_id, 
                                                summary.form_date,
                                                summary.summary))
                for summary_id, form_date, summary in self.form_instances:
                    if summary_id == task.summary_id:
                        break
                else:
                    task.summary_id = self.form_instances[0][0]

def get_menubar(ctx):
    menubar = page_common.MenuBar()
    if ctx.locals.edittask.seed_task_id:
        if ctx.locals.edittask.inplace:
            if ctx.locals.edittask.action in tasks.action_closed:
                menubar.add_middle('close', 'Mark Completed')
                menubar.add_right('update', 'Re-open task')
            else:
                menubar.add_middle('delete', 'Delete Task')
                menubar.add_middle('close', 'Task Completed')
                menubar.add_right('update', 'Update task')
        else:
            menubar.add_middle('close', 'Task Completed')
            menubar.add_right('update', 'Create next task(s)')
    else:
        menubar.add_right('update', 'Create task')
    menubar.done()
    return menubar


def page_enter(ctx, syndrome_id, edittask):
    ctx.locals.task_synd_id = syndrome_id
    ctx.locals.edittask = edittask
    ctx.locals.assign_search = None
    ctx.add_session_vars('task_synd_id', 'edittask', 'assign_search')

def page_leave(ctx):
    page_common.unlock_task(ctx)
    ctx.del_session_vars('task_synd_id', 'edittask', 'assign_search') 

def page_display(ctx):
    ctx.locals.task_options = taskdesc.task_options(ctx.locals.task_synd_id)
    ctx.locals.menubar = get_menubar(ctx)
    ctx.locals.fh = None

def page_process(ctx):
    if pageops.page_process(ctx):
        return
