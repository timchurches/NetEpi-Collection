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
from casemgr import globals, reports
from pages import page_common, report_ops
import config

class PageOps(page_common.PageOpsBase):

    def do_report(self, ctx, report_id):
        if ctx.locals._credentials.rights.any('EXPORT', 'PUBREP'):
            reportparams = reports.load(int(report_id),
                                        ctx.locals._credentials)
            report_ops.run_report(ctx, reportparams)

    def do_edit(self, ctx, report_id):
        if 'EXPORT' in ctx.locals._credentials.rights:
            reportparams = reports.load(int(report_id),
                                        ctx.locals._credentials)
            ctx.push_page('report_edit', reportparams)

    def do_new(self, ctx, ignore):
        if 'EXPORT' in ctx.locals._credentials.rights:
            reportparams = reports.new_report(ctx.locals.report_syndrome_id)
            ctx.push_page('report_edit', reportparams)

    def do_upload(self, ctx, ignore):
        ctx.locals.report_upload_mode = True

    def do_report_import_cancel(self, ctx, ignore):
        ctx.locals.report_upload_mode = False

    def do_report_import(self, ctx, ignore):
        if 'EXPORT' not in ctx.locals._credentials.rights:
            return
        if len(ctx.locals.report_import_file) != 1:
            raise page_common.PageError('Choose one file')
        reportparams = reports.parse_file(ctx.locals.report_syndrome_id,
                                          ctx.locals.report_import_file[0].file)
        ctx.push_page('report_edit', reportparams)
        ctx.locals.report_upload_mode = False


pageops = PageOps()


def page_enter(ctx, syndrome_id):
    ctx.locals.report_syndrome_id = syndrome_id
    ctx.locals.report_upload_mode = False
    ctx.add_session_vars('report_syndrome_id', 'report_upload_mode')

def page_leave(ctx):
    ctx.del_session_vars('report_syndrome_id', 'report_upload_mode')

def page_display(ctx):
    ctx.locals.user_reports = reports.ReportMenu(ctx.locals._credentials,
                                                 ctx.locals.report_syndrome_id)
    ctx.locals.can_edit = 'EXPORT' in ctx.locals._credentials.rights
    ctx.run_template('report_menu.html')

page_process = pageops.page_process
