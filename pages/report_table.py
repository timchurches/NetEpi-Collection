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
from casemgr import globals, caseaccess
from pages import page_common, report_ops

import config

class PageOps(page_common.PageOpsBase):

    def do_key(self, ctx, key):
        page_common.go_id(ctx, key)

    def do_refresh(self, ctx, ignore):
        ctx.pop_page()
        report_ops.run_report(ctx, ctx.locals.reportgen.params)

page_process = PageOps().page_process


class ConfirmReport(page_common.Confirm):
    mode = 'confirm'
    title = 'Large report'
    buttons = [
        ('back', 'No'),
        ('continue', 'Yes'),
    ]

    def button_back(self, pageops, ctx):
        ctx.pop_page()


def page_enter(ctx, reportgen):
    ctx.locals.reportgen = reportgen
    ctx.add_session_vars('reportgen')
    if len(ctx.locals.reportgen) > 5000:
        raise ConfirmReport(message='This report has %s records and may take '
                            'a considerable time to run. Do you wish to '
                            'continue?' % len(ctx.locals.reportgen))

def page_leave(ctx):
    ctx.del_session_vars('reportgen')

def page_display(ctx):
    ctx.run_template('report_table.html')
