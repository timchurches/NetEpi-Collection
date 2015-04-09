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

import sys, os
import config
from cocklebur import pageops
from cocklebur.pageops import download, csv_download, send_download, \
                              Confirm, ConfirmSave, \
                              ConfirmDelete, ConfirmUndelete, ConfirmRevert
from cocklebur import dbobj, form_ui, checkdigit
from casemgr import globals, cases, tasks, taskdesc, credentials, messages
from casemgr.tabs import Tabs


class PageError(globals.Error): pass


class ConfirmUnlock(Confirm):
    mode = 'unlock'
    title = 'Take ownership'
    message = 'This record is externally sourced. Taking ownership will stop any external updates occurring and allow local editing. This can not be reversed. Are you sure you wish to do this?'
    buttons = [
        ('continue', 'No'),
        ('confirm', 'Yes'),
    ]


class PageOpsBase(pageops.PageOpsBase):
    debug = config.debug
    home_page = 'main'
    app_errors = (
        globals.Error,
        dbobj.DatabaseError, 
        form_ui.FormError,
        credentials.CredentialError,
    )

    def do_admin(self, ctx, ignore):
        self.check_unsaved_or_confirmed(ctx)
        ctx.pop_page('admin')

    def do_logout(self, ctx, ignore):
        unlock_task(ctx)
        ctx.locals._credentials.commit_prefs(globals.db, immediate=True)
        pageops.PageOpsBase.do_logout(self, ctx, ignore)

    def do_menubardrop(self, ctx, action):
        ctx.locals.menubardrop = None
        args = action.split(':')
        action = args.pop(0)
        if not args:
            args = None,
        if hasattr(self, 'do_' + action):
            self.dispatch(ctx, action, args)
        else:
            return pageops.ContinueDispatch

    def do_page(self, ctx, *args):
        ctx.locals.paged_search.do(*args)

    def page_process(self, ctx):
        client_report(ctx)
        ctx.locals._credentials.commit_prefs(globals.db)
        try:
            paged_search = getattr(ctx.locals, 'paged_search', None)
            if paged_search is not None:
                paged_search.page_jump()
            return pageops.PageOpsBase.page_process(self, ctx)
        except messages.Messages, msgs:
            ctx.add_messages(msgs)
            globals.db.rollback()
        except self.app_errors, e:
            # ctx.set_page() & ctx.push_page() indirectly invoke the page
            # page_enter() method. If this throws an exception that we catch, 
            # the page_display() method may be called without appropriate
            # initialisation, resulting in obscure failures.
            tb = sys.exc_info()[2].tb_next
            while tb:
                if tb.tb_frame.f_code.co_name == 'page_enter':
                    ctx.pop_page()
                    break
                tb = tb.tb_next
            globals.db.rollback()
            ctx.locals.confirm = None
            ctx.add_error(e)


page_process = PageOpsBase().page_process       # Legacy


class PageOpsLeaf(PageOpsBase):
    # For pages of this type (sub pages of a page with "unsaved changes"), we
    # pass the logout/home/admin/back process up to the parent page. The
    # mechanism is somewhat of a hack, but it's the best we can do for now.

    def page_process_parent(self, ctx, *ignore):
        try:
            self.check_unsaved_or_confirmed(ctx)
        except pageops.Confirm:
            # Page model isn't sophisticated enough to support this:
            raise NotImplementedError
        ctx.pop_page()
        ctx.page.page_process(ctx)

    do_logout = page_process_parent

    def do_home(self, ctx, ignore):
        if ctx.locals.__pages__[-1] == self.home_page:
            PageOpsBase.action_home(self, ctx)
        else:
            self.page_process_parent(ctx)

    def do_admin(self, ctx, ignore):
        if ctx.locals.__pages__[-1] == 'admin':
            PageOpsBase.do_admin(self, ctx, ignore)
        else:
            self.page_process_parent(ctx)


def client_report(ctx):
    """
    Pull some hidden fields out of the client request, and log their
    contents (along with some other useful bits like the instance name,
    authenticated user, and client IP address). These can subsequently be
    analysed to identify network and application bottlenecks.
    """
    fields = dict(
        client    = getattr(ctx.locals, 'response_time', None),
        forwarded = ctx.request.get_forwarded_addr(),
        inst      = config.appname,
        ip        = ctx.request.get_remote_addr(),
        page      = getattr(ctx.locals, 'last_page', None),
        server    = getattr(ctx.locals, 'server_time', None),
        start     = getattr(ctx.locals, 'start_time', None),
        unit      = '',
        user      = '',
    )
    if ctx.locals._credentials:
        fields['user'] = str(ctx.locals._credentials.user.user_id)
        fields['unit'] = str(ctx.locals._credentials.unit.unit_id)
    pairs = []
    for key, value in fields.iteritems():
        if value:
            pairs.append('%s=%s' % (key, str(value)[:80].replace(' ', '_')))
    if fields['page']:
        print >> sys.stderr, 'client report: %s' % (' '.join(pairs))


def merge_rights(ptset):
    rights = credentials.Rights()
    for row in ptset:
        if row.rights:
            rights.add(row.rights)
    return rights


def idle(ctx):
    ctx.locals.case = None
    ctx.locals.caseset = None
    unlock_task(ctx)


class MenuBarItem:
    drop = None

    def __init__(self, name, label, style='butt'):
        self.name = name
        self.label = label
        self.style = style

    def linkjs(self):
        return "javascript:linksubmit('appform','%s');" % self.name.lower()

    def add_drop(self, name, label, style=None):
        if self.drop is None:
            self.drop = []
        self.drop.append((name, label))

    def add_droprule(self):
        if self.drop is not None and self.drop[-1][0]:
            self.drop.append(('-', ''))

    def optionexpr(self):
        return [('', self.label)] + self.drop


class MenuBar:

    def __init__(self):
        self.left = []
        self.middle = []
        self.right = []
        self.button_width = 4

    def _add(self, which, *args, **kwargs):
        item = MenuBarItem(*args, **kwargs)
        which.append(item)
        width = len(item.label)
        if width > self.button_width:
            self.button_width = width
        return item

    def table_row(self):
        yield 'mbl', self.left
        yield 'mbm', self.middle
        yield 'mbr', self.right

    def add_left(self, *args, **kwargs):
        return self._add(self.left, *args, **kwargs)

    def add_middle(self, *args, **kwargs):
        return self._add(self.middle, *args, **kwargs)

    def add_right(self, *args, **kwargs):
        return self._add(self.right, *args, **kwargs)

    def done(self):
        self.style = 'width: %.1fem;' % (self.button_width * 0.75)


def bannertabs(ctx):
    tabs = MenuBar()
    page = ctx.locals.__page__
    pages = ctx.locals.__pages__
    cred = ctx.locals._credentials
    if page == 'admin_form_edit_question' or ctx.locals.confirm:
        # The question editor can't safely say if there are unsaved changes or
        # not, so we disallow home & logout within it.
        return tabs
    if page not in ('main',):
        tabs.add_left('back', 'Back')
    if 'ADMIN' in cred.rights and 'admin' in pages:
        tabs.add_left('admin', 'Admin')
    if page == 'main':
        tabs.add_middle('query_tasks', 'Tasks')
        tabs.add_middle('tools', 'Tools')
        if 'ADMIN' in cred.rights:
            tabs.add_middle('admin', 'Admin')
    else:
        if 'TASKINIT' in cred.rights and page in ('tasks', 'casetasks'):
            tabs.add_middle('note', 'Note')
        if 'main' in pages:
            tabs.add_left('home', 'Home')
    if page in ('case', 'caseform'):
        tabs.add_right('print', 'Print')
    tabs.add_right('logout', 'Logout')
    return tabs


# Task related stuff that changes application state and consequently doesn't
# belong in the tasks module.
def unlock_task(ctx):
    # During logout, task can be deleted from ctx
    task = getattr(ctx.locals, 'task', None)
    if task is not None:
        ctx.locals.task.unlock(globals.db)
        globals.db.commit()
        ctx.locals.task = None


def task_update(ctx, task_desc):
    if ctx.locals.task is not None:
        ctx.locals.task.entity_update(globals.db, **task_desc)


def is_cur_task(ctx, task_desc):
    if ctx.locals.task is not None:
        return ctx.locals.task.same_entity(**task_desc)
    return False


def unlock_desc_task(ctx, task_desc):
    if ctx.locals.task is not None:
        if ctx.locals.task.same_entity(**task_desc):
            unlock_task(ctx)
            return True
    return False


def set_case(ctx, case):
    # Update caseset
    if ctx.locals.caseset is not None:
        if ctx.locals.caseset.cur() != case.case_row.case_id:
            try:
                ctx.locals.caseset.seek_case(case.case_row.case_id)
            except ValueError:
                ctx.locals.caseset = None
    # Update tabs
    select = None
    if ctx.locals.case is not None and hasattr(ctx.locals.case, 'tabs'):
        select = ctx.locals.case.tabs.selected
    case.init_tabs(select)
    ctx.locals.case = case


def edit_case(ctx, case, push=False):
    set_case(ctx, case)
    if push:
        ctx.push_page('case')
    else:
        ctx.set_page('case')


def precreate_case(ctx, case):
    if config.immediate_create:
        try:
            log = case.db_desc()
            case.update()
            case.user_log(log)
            globals.db.commit()
            ctx.add_message('Case created')
        except dbobj.DatabaseError, e:
            globals.db.rollback()
            ctx.add_error(e)


def new_case(ctx, syndrome_id, **kw):
    case = cases.new_case(ctx.locals._credentials, syndrome_id, **kw)
    precreate_case(ctx, case)
    return case


def go_id(ctx, id):
    """
    Given a check-digit protected entity ID, load the appropriate object
    and push the appropriate edit page.
    """
    if not id:
        return
    if id.isdigit():
        id = int(id)
        case = cases.edit_case(ctx.locals._credentials, id)
        ctx.locals.caseset = None
        edit_case(ctx, case, push=True)
        return
    else:
        id_type = id[0].upper()
        id_okay, id = checkdigit.check_checkdigit(id[1:])
        if id_okay and id_type == 'F':
            case, ef = cases.edit_form(ctx.locals._credentials, id)
            ctx.locals.caseset = None
            edit_case(ctx, case, push=True)
            ctx.push_page('caseform', ef)
            return
    raise PageError('Invalid ID')


def alternate(idx):
    if idx & 1:
        return 'darker'
    else:
        return 'lighter'
