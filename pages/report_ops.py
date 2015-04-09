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

from cocklebur import datetime
from casemgr import reports
from pages import page_common
import config

class ConfirmReport(page_common.Confirm):
    mode = 'confirm'
    title = 'Large report'
    buttons = [
        ('discard', 'No'),
        ('continue', 'Yes'),
    ]


def run_report(ctx, reportparams):
    try:
        rpt = reportparams.report(ctx.locals._credentials, msgs=ctx)
    except reports.ReportParamError, e:
        ctx.add_error(e)
    else:
        if ctx.have_errors():
            return
        if not rpt:
            raise reports.ReportParamError('No matching records found')
        else:
            ctx.push_page('report_' + rpt.render, rpt)


def report_export(ctx, reportparams):
    # Consistency check (form versions)
    msgs = reportparams.check()
    ctx.add_messages(msgs)
    if msgs.have_errors():
        # XXX Uh oh - warnings go into a black hole?
        return
    try:
        row_gen = reportparams.export_rows(ctx.locals._credentials)
    except reports.ReportParamError, e:
        ctx.add_error(e)
    else:
        filename = datetime.now().strftime(config.appname + '-%Y%m%d-%H%M.csv')
        page_common.csv_download(ctx, row_gen, filename)
