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
import time

from cocklebur import dbobj

from casemgr import globals, cases, syndrome, bulletins, search,\
                    caseset, tasksearch, reports

from pages import page_common, report_ops, search_ops, taskaction

import config

class SyndItem:
    """
    Represents a syndrome listed on the main page, with associated
    buttons and styling.
    """
    def __init__(self, syndromes, syndrome, cred):
        def report_options(menuitem, syndrome_id):
            reports_c = reports.reports_cache.get_synd_unit(syndrome_id, 
                                                            cred.unit.unit_id)
            for report in reports_c:
                name = 'report:%s:%s' % (report.report_params_id, 
                                         syndrome.syndrome_id)
                menuitem.add_drop(name, report.label)
        self.syndrome = syndrome
        self.syndrome_id = id = syndrome.syndrome_id
        self.record_count = syndrome.case_count
        view_only = 'VIEWONLY' in cred.rights
        self.menubar = page_common.MenuBar()
        if not view_only and syndromes.can_add(id):
            self.menubar.add_left('add:%s' % id, 'add')
        self.menubar.add_left('search:%s' % id, 'search')
        show_reports = cred.rights.any('EXPORT', 'PUBREP')
        if show_reports:
            menuitem = self.menubar.add_left('reports:%s' % id, 'reports')
            report_options(menuitem, id)
        menuitem = self.menubar.add_left('other:%s' % id, 'other actions',
                                         style='')
        menuitem.add_drop('printforms:%s' % id, 'Print blank forms')
        if 'EXPORT' in cred.rights:
            menuitem.add_drop('export:%s' % id, 'Export records')
        if 'IMPORT' in cred.rights:
            menuitem.add_drop('import:%s' % id, 'Import data')


def gen_synd_list(syndromes, credentials):
    return [SyndItem(syndromes, synd, credentials) for synd in syndromes]


class PageOps(page_common.PageOpsBase):
    def do_admin(self, ctx, ignore):
        if 'ADMIN' in ctx.locals._credentials.rights:
            ctx.push_page('admin')

    def do_tools(self, ctx, ignore):
        ctx.push_page('tools')

    def do_query_tasks(self, ctx, ignore):
        ctx.push_page('tasks')

    def do_syn_detail(self, ctx, syndrome_id):
        ctx.push_page('syn_detail', int(syndrome_id))

    def hide_bulletins(self, ctx):
        ctx.locals._credentials.prefs.set('bulletin_time', time.time())

    def do_bulletin_detail(self, ctx, bulletin_id):
        if bulletin_id.lower() == 'hide':
            self.hide_bulletins(ctx)
        else:
            ctx.push_page('bulletin_detail', int(bulletin_id))

    def do_hide_bulletins(self, ctx, ignore):
        self.hide_bulletins(ctx)

    def do_show_bulletins(self, ctx, ignore):
        ctx.locals._credentials.prefs.set('bulletin_time', None)

    # Not used by current home page
    #def do_search(self, ctx, ignore):
    #    ctx.push_page('search', search_ops.SearchOps(ctx.locals._credentials))

    def do_search(self, ctx, syndrome_id):
        ctx.push_page('search', search_ops.EditOps(ctx.locals._credentials, 
                                                   int(syndrome_id)))

    def do_quick_search(self, ctx, quick_search):
        if quick_search:
            ctx.locals.quick_search = None
            so = search_ops.SearchOps(ctx.locals._credentials)
            ctx.locals.search = search.Search(so)
            ctx.locals.search.quicksearch = quick_search
            ctx.locals.search.search(ctx.locals)
            ctx.locals.search.search_ops.result(ctx, ctx.locals.search.result)

    def do_add(self, ctx, syndrome_id):
        ctx.push_page('search', search_ops.NewCaseOps(ctx.locals._credentials, 
                                                      int(syndrome_id)))

    # Extra syndrome actions
    def do_reports(self, ctx, syndrome_id):
        if ctx.locals._credentials.rights.any('EXPORT', 'PUBREP'):
            ctx.push_page('report_menu', int(syndrome_id))

    def do_report(self, ctx, report_id, syndrome_id):
        if ctx.locals._credentials.rights.any('EXPORT', 'PUBREP'):
            reportparams = reports.load(int(report_id),
                                        ctx.locals._credentials)
            report_ops.run_report(ctx, reportparams)

    def do_printforms(self, ctx, syndrome_id):
        ctx.push_page('selprintforms', int(syndrome_id))

    def do_export(self, ctx, syndrome_id):
        if 'EXPORT' in ctx.locals._credentials.rights:
            ctx.push_page('export', int(syndrome_id))

    def do_import(self, ctx, syndrome_id):
        if 'IMPORT' in ctx.locals._credentials.rights:
            ctx.push_page('dataimp', int(syndrome_id))

    # Swine Flu special
    def do_crosstab_counts(self, ctx, syndrome_id):
        ctx.push_page('crosstab_counts', syndrome_id, None)

    def do_crosstab_counts_params(self, ctx, syndrome_id):
        ctx.push_page('crosstab_counts_params', syndrome_id)

    def do_recent_case(self, ctx, case_id):
        page_common.go_id(ctx, case_id)

    def do_task(self, ctx, task_id):
        try:
            taskaction.task_dispatch(ctx, int(task_id), ctx.push_page)
        except taskaction.TAError, e:
            ctx.add_error(e)
        

pageops = PageOps()


def cred_init(ctx):
    cred = ctx.locals._credentials
    ctx.locals.syndromes = syndrome.UnitSyndromesView(cred)
    cred.prefs.set('current_unit', cred.unit.unit_id)


def page_enter(ctx):
    cred = ctx.locals._credentials
    if cred.prefs.lost_reason:
        ctx.add_error('Unable to restore user preferences (%s)' % 
                        cred.prefs.lost_reason)
        cred.prefs.lost_reason = None
    for msg in cred.messages:
        ctx.add_message(msg)
    del cred.messages[:]
    cred_init(ctx)
    ctx.locals.bulletins = bulletins.Bulletins(globals.db, cred)
    ctx.locals.casesets = caseset.CaseSets(cred)
    ctx.locals.quick_tasks = tasksearch.QuickTasks(ctx.locals._credentials)
    ctx.locals.task = None
    ctx.locals.case = None
    ctx.locals.search = None
    ctx.locals.caseset = None
    ctx.locals.double_trap = False
    ctx.add_session_vars('syndromes', 'bulletins', 'casesets', 'quick_tasks',
                         'task', 'case', 'search', 'caseset', 'double_trap')


def page_display(ctx):
    hide_time = ctx.locals._credentials.prefs.get('bulletin_time')
    ctx.locals.bulletin_list = ctx.locals.bulletins.get_bulletins(hide_time)
    # User may have aborted via the "home" button - release stuff...
    page_common.idle(ctx)
    ctx.locals.synd_list = gen_synd_list(ctx.locals.syndromes,
                                         ctx.locals._credentials)
    ctx.locals.unit_select = ctx.locals._credentials.unit.unit_id
    ctx.locals.quick_tasks.refresh()
    ctx.run_template('main.html')


def page_process(ctx):
    ctx.locals.double_trap = False
    cred = ctx.locals._credentials
    # Does the user wish to change units?
    try:
        unit_select = int(ctx.locals.unit_select)
    except (ValueError, AttributeError):
        pass
    else:
        if unit_select != cred.unit.unit_id:
            cred.set_unit(globals.db, unit_select)
            cred_init(ctx)

    # Any "More options..." selections?
    syndextra = getattr(ctx.locals, 'syndextra', [])
    ctx.locals.syndextra = []
    for op in syndextra:
        if op:
            fields = op.split(':')
            meth = getattr(pageops, 'do_%s' % fields[0], None)
            if meth:
                try:
                    return meth(ctx, *map(int, fields[1:]))
                except pageops.app_errors, e:
                    globals.db.rollback()
                    ctx.add_error(e)
    # Otherwise, defer to normal page dispatch
    pageops.page_process(ctx)
