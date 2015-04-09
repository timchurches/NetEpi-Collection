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
from casemgr import globals, tasks, casemerge, logview, caseset, casetags
from pages import page_common, caseset_ops
import config

class ConfirmCaseDelete(page_common.ConfirmDelete):
    mode = 'delete'
    title = 'You are deleting this case'
    reason_prompt = 'Reason for deletion:'


class ConfirmCaseUndelete(page_common.ConfirmUndelete):
    mode = 'delete'
    title = 'You are undeleting this case'


def desc_task(ctx):
    action = tasks.ACTION_UPDATE_CASE
    if ctx.locals.case.is_new():
        action = tasks.ACTION_NEW_CASE
    return dict(case_id = ctx.locals.case.case_row.case_id,
                action = action)

class PageOps(page_common.PageOpsBase, caseset_ops.CasesetOps):

    def unsaved_check(self, ctx):
        if ctx.locals.case.has_changed():
            raise page_common.ConfirmSave
    
    def rollback(self, ctx):
        ctx.locals.case.revert()

    def commit(self, ctx):
        case = ctx.locals.case
        try:
            log = case.db_desc()
            task_desc = desc_task(ctx)
            case.update()
            case.user_log(log)
            page_common.task_update(ctx, task_desc)
            globals.db.commit()
            ctx.add_message('Case updated')
        except casetags.InvalidTags, e:
            ctx.msg('err', e)
            ctx.push_page('tagbrowse', 'Case tags', 'case.tags.cur')
        except dbobj.DuplicateKeyError, e:
            raise dbobj.DatabaseError('Case already added')

    def do_back(self, ctx, ignore):
        self.check_unsaved_or_confirmed(ctx)
        self.rollback(ctx)
        page_common.unlock_desc_task(ctx, desc_task(ctx))
        ctx.pop_page()

    def do_update(self, ctx, ignore):
        self.commit(ctx)
        if ctx.locals.task and ctx.locals.task.done:
            ctx.set_page('casetask', ctx.locals.case)

    def do_edit(self, ctx, form_label, summary_id):
        self.check_unsaved_or_confirmed(ctx)
        edit_form = ctx.locals.case.edit_form(int(summary_id))
        ctx.push_page('caseform', edit_form)

    def do_new(self, ctx, form_label):
        self.check_unsaved_or_confirmed(ctx)
        edit_form = ctx.locals.case.new_form(form_label)
        ctx.push_page('caseform', edit_form)

    def do_useperson(self, ctx, person_id):
        ctx.locals.case.use_person_id(int(person_id))
        self.update_case(ctx, db)

    def do_contacts(self, ctx, ignore):
        self.check_unsaved_or_confirmed(ctx)
        ctx.locals.case.invalidate_contact_count()
        ctx.push_page('casecontacts')

    def do_exposures(self, ctx, ignore):
        self.check_unsaved_or_confirmed(ctx)
        ctx.locals.case.invalidate_contact_count()
        ctx.push_page('caseexposures')

    def do_newtask(self, ctx, ignore):
        ctx.push_page('casetask', ctx.locals.case)

    def do_casetasks(self, ctx, ignore):
        ctx.push_page('casetasks', ctx.locals.case)

    def do_quit_task(self, ctx, ignore):
        page_common.unlock_task(ctx)

    def do_access(self, ctx, ignore):
        self.check_unsaved_or_confirmed(ctx)
        ctx.push_page('caseaccess')

    def do_log(self, ctx, ignore):
        self.check_unsaved_or_confirmed(ctx)
        case_id = ctx.locals.case.case_row.case_id
        log = logview.CaseLogView(ctx.locals._credentials.prefs, 
                                  'Log for Case ID %r' % case_id,
                                  case_id=case_id)
        ctx.push_page('logview', log)

    def do_delete(self, ctx, ignore):
        if self.confirmed:
            case = ctx.locals.case
            case.set_deleted(True, ctx.locals.confirm.reason)
            case.user_log('Deleted case')
            globals.db.commit()
        else:
            raise ConfirmCaseDelete

    def do_undelete(self, ctx, ignore):
        if self.confirmed:
            case = ctx.locals.case
            case.set_deleted(False)
            case.user_log('Undeleted case')
            globals.db.commit()
        else:
            raise ConfirmCaseUndelete

    def do_print(self, ctx, ignore):
        case = ctx.locals.case
        if case.case_row.is_new() or case.has_changed():
            ctx.add_error('Save record before printing')
        else:
            ctx.push_page('caseprint')

    def do_mergecase(self, ctx, ignore):
        self.check_unsaved_or_confirmed(ctx)
        selmerge = casemerge.by_case(ctx.locals._credentials,
                                     ctx.locals.case.case_row,
                                     ctx.locals.case.person)
        ctx.push_page('selmergecase', selmerge)

    def do_mergeforms(self, ctx, ignore):
        if not ctx.locals.case.can_merge_forms():
            raise page_common.PageError('There are no forms eligible to '
                                        'be merged')
        self.check_unsaved_or_confirmed(ctx)
        ctx.push_page('selmergeforms', ctx.locals.case)

    def do_tab(self, ctx, tab):
        ctx.locals.case.tabs.select(tab)

    def do_ownsrc(self, ctx, ignore):
        if self.confirmed:
            ctx.locals.case.person.data_src = None
            self.commit(ctx)
        else:
            raise page_common.ConfirmUnlock

    def do_tagbrowse(self, ctx, ignore):
        ctx.push_page('tagbrowse', 'Case tags', 'case.tags.cur')

    def get_menubar(self, ctx):
        menubar = page_common.MenuBar()
        rw = 'VIEWONLY' not in ctx.locals._credentials.rights
        if not ctx.locals.case.case_row.is_new():
            menubar.add_middle('contacts', config.contact_label + 's')
            cs_options = ctx.locals.casesets.caseoptions(ctx.locals.caseset)
            droplist = menubar.add_middle('menubardrop', '(More actions)')
            for cmd, label in cs_options:
                droplist.add_drop(cmd, label)
            droplist.add_droprule()
            if ctx.locals.task:
                menubar.add_middle('quit_task', 'Quit Task')
            else:
                if (not ctx.locals.case.deleted 
                    and 'TASKINIT' in ctx.locals._credentials.rights):
                    droplist.add_drop('newtask', 'Create a New Task')
                droplist.add_drop('casetasks', 'Case Tasks')
                droplist.add_droprule()
            if rw:
                droplist.add_drop('access', 'Access Control')
            droplist.add_drop('caseset_person', 'Other records for this person')
            droplist.add_drop('log', 'Activity Log')
            droplist.add_droprule()
            if 'mergeperson' not in ctx.locals.__pages__:
                droplist.add_drop('mergecase', 'Merge Cases')
            droplist.add_drop('mergeforms', 'Merge Forms')
            droplist.add_droprule()
            if ctx.locals.case.deleted and rw:
                droplist.add_drop('undelete', 'Undelete', 
                                    style='danger butt')
            elif rw:
                droplist.add_drop('delete', 'Delete', style='danger butt')
                menubar.add_right('update', 'Update')
        else:
            menubar.add_right('update', 'Create')
        menubar.done()
        return menubar


pageops = PageOps()

def page_enter(ctx):
    task = ctx.locals.task 
    case = ctx.locals.case
    if task and task.case_id != case.case_row.case_id:
        # This should not happen.
        page_common.unlock_task(ctx)

def page_leave(ctx):
    ctx.locals.case = None

def page_display(ctx):
    ctx.locals.case.forms.refresh()
    ctx.locals.menubar = pageops.get_menubar(ctx)
    ctx.run_template('case.html')

def page_process(ctx):
    if ctx.locals.case.case_row.case_id:
        ctx.locals._credentials.prefs.set_recent_case(ctx.locals.case.case_row.case_id, str(ctx.locals.case))
    if pageops.page_process(ctx):
        return
