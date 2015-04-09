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
import os
from cocklebur.filename_safe import filename_safe
from casemgr import globals, caseaccess, cases, reports
from casemgr.tabs import Tabs
from pages import page_common, caseset_ops, report_ops
import config


def cancel_add_filter(ctx):
    if ctx.locals.add_filter:
        ctx.locals.add_filter.abort()
        ctx.locals.add_filter = None

def add_filter(ctx):
    if ctx.locals.add_filter and ctx.locals.add_filter.is_complete():
        filter = ctx.locals.add_filter.add()
        if hasattr(filter, 'children'):
            ctx.locals.add_filter = ctx.locals.reportparams.filter_adder(filter)
            ctx.locals.edit_filter = ctx.locals.add_filter.placeholder
        else:
            ctx.locals.edit_filter = filter
            ctx.locals.add_filter = None


class PageOps(page_common.PageOpsBase):

    def check_unsaved_or_confirmed(self, ctx):
        ctx.locals.reportparams.autosave(ctx.locals._credentials)
        globals.db.commit()

    def do_col(self, ctx, op, group_index, col_index=None):
        group_index = int(group_index)
        if col_index:
            col_index = int(col_index)
        ctx.locals.reportparams.colop(op, group_index, col_index)

    def do_addcaseperson(self, ctx, ignore):
        ctx.locals.reportparams.add_caseperson()

    def do_add_order(self, ctx, ignore):
        ctx.locals.reportparams.add_order()

    def do_del_order(self, ctx, index):
        ctx.locals.reportparams.del_order(int(index))

    def do_save(self, ctx, ignore):
        if (not ctx.locals.reportparams.label or 
                not ctx.locals.reportparams.label.strip()):
            ctx.locals.report_tabs.select('info')
            raise page_common.PageError('A report name must be specified')
        ctx.locals.reportparams.save(ctx.locals._credentials)
        globals.db.commit()
        ctx.add_message('Report parameters saved')

    def do_delete(self, ctx, ignore):
        ctx.locals.delete_confirm = True

    def do_delete_cancel(self, ctx, ignore):
        ctx.locals.delete_confirm = False

    def do_delete_confirm(self, ctx, ignore):
        if ctx.locals.reportparams.loaded_from_id:
            reports.delete(ctx.locals.reportparams.loaded_from_id)
            globals.db.commit()
        ctx.locals.delete_confirm = False
        ctx.locals.reportparams.autosave(ctx.locals._credentials)
        ctx.pop_page()

    def do_tab(self, ctx, pagetab):
        ctx.locals.delete_confirm = False
        ctx.locals.report_tabs.select(pagetab)

    def do_report(self, ctx, ignore):
        report_ops.run_report(ctx, ctx.locals.reportparams)

    def do_edit(self, ctx, ignore):
        case_ids = ctx.locals.reportparams.get_case_ids(ctx.locals._credentials)
        caseset_ops.make_caseset(ctx, case_ids, 'Report cases')

    def do_export(self, ctx, ignore):
        report_ops.report_export(ctx, ctx.locals.reportparams)

    def do_params_download(self, ctx, ignore):
        if ctx.locals.reportparams.label:
            name = filename_safe(ctx.locals.reportparams.label)
        else:
            name = 'reportparams'
        downloader = page_common.download(ctx, name + '.xml')
        ctx.locals.reportparams.xmlsave(downloader)

    def do_filteradd(self, ctx, path):
        cancel_add_filter(ctx)
        parent = ctx.locals.reportparams.path_filter(path)
        ctx.locals.add_filter = ctx.locals.reportparams.filter_adder(parent)
        ctx.locals.edit_filter = ctx.locals.add_filter.placeholder

    def do_filteraddexpr(self, ctx, ignore):
        add_filter(ctx)

    def do_filteredit(self, ctx, path):
        cancel_add_filter(ctx)
        filter = ctx.locals.reportparams.path_filter(path)
        if filter.op == 'placeholder':
            # Whoops, old placeholder - delete and go back into add filter mode
            # This shouldn't happen, but if it does, try to be nice about it.
            path = '.'.join(path.split('.')[:-1])
            parent = ctx.locals.reportparams.path_filter(path)
            parent.children.remove(filter)
            self.do_filteradd(ctx, path)
        else:
            ctx.locals.add_filter = None
            ctx.locals.edit_filter = ctx.locals.reportparams.path_filter(path)

    def do_filterdelete(self, ctx, ignore):
        if ctx.locals.edit_filter:
            if ctx.locals.reportparams.del_filter(ctx.locals.edit_filter):
                ctx.locals.edit_filter = None

    def do_filterclose(self, ctx, ignore):
        cancel_add_filter(ctx)
        ctx.locals.edit_filter = None

    def do_filterconj(self, ctx, path):
        filter = ctx.locals.reportparams.path_filter(path)
        filter.toggle_conj()

pageops = PageOps()

def default_tab(ctx):
    ctx.locals.report_tabs.select('info')


def mktabs(report_params):
    tabs = Tabs()
    tabs.add('info', 'Info')
    if report_params.show_filters:
        tabs.add('filters', 'Filters')
    if report_params.show_orderby:
        tabs.add('orderby', 'Order By')
    if report_params.show_filters:
        tabs.add('edit', 'Cases', action=True, accesskey='e')
    if report_params.show_columns:
        tabs.spacer()
        tabs.add('columns', 'Columns')
        tabs.add('forms', 'Forms')
    if report_params.show_axes:
        tabs.add('crosstab', 'Axes')
    if report_params.show_epicurve:
        tabs.add('epicurve', 'Time series')
    if report_params.show_contactvis:
        tabs.add('contactvis', 'Params')
    if report_params.show_filters and report_params.show_columns:
        tabs.add('export', 'Export', accesskey='x')
    tabs.add('report', 'Report', action=True, accesskey='r')
    tabs.spacer()
    tabs.add('save', 'Save', action=True, accesskey='s')
    return tabs.done()


def reset(ctx):
    default_tab(ctx)
    ctx.locals.delete_confirm = False
    ctx.locals.caseset = None


def page_enter(ctx, reportparams):
    ctx.locals.reportparams = reportparams
    ctx.locals.report_tabs = mktabs(reportparams)
    ctx.locals.edit_filter = None
    ctx.locals.add_filter = None
    reset(ctx)
    if ctx.locals.reportparams.loaded_from_id is not None:
        ctx.add_messages(ctx.locals.reportparams.check())
    ctx.add_session_vars('report_tabs', 'reportparams', 'delete_confirm',
                         'edit_filter', 'add_filter')

def page_leave(ctx):
    ctx.del_session_vars('report_tabs', 'reportparams', 'delete_confirm',
                         'edit_filter', 'add_filter')

def page_display(ctx):
    if not page_common.send_download(ctx):
        ctx.run_template('report_edit.html')


def page_process(ctx):
    params = ctx.locals.reportparams
    if getattr(ctx.locals, 'add_form', None):
        params.add_form(ctx.locals.add_form)
    add_filter(ctx)
    ctx.locals.add_form = None
    params.cols_update()
    set_type = getattr(ctx.locals, 'set_type', None)
    if set_type and set_type != params.report_type:
        ctx.locals.reportparams = params.change_type(set_type, msgs=ctx)
        ctx.locals.report_tabs = mktabs(ctx.locals.reportparams)
    try:
        pageops.page_process(ctx)
    except reports.ReportParamError, e:
        ctx.add_error(e)
