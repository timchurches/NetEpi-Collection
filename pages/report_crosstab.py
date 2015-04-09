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
from casemgr import globals, syndrome, demogfields
from casemgr.reports.crosstab import TOTAL, HEAD
from pages import page_common, caseset_ops
import config

class PageOps(page_common.PageOpsBase):
    def do_key(self, ctx, *coords):
        case_ids = ctx.locals.crosstab.get_key_case_ids(*coords)
        cell_desc = ctx.locals.crosstab.desc_key(*coords)
        caseset_ops.make_caseset(ctx, case_ids, cell_desc)

page_process = PageOps().page_process


def page_enter(ctx, crosstab):
    ctx.locals.crosstab = crosstab
    ctx.add_session_vars('crosstab')

def page_leave(ctx):
    ctx.del_session_vars('crosstab')

def page_display(ctx):
    ctx.run_template('report_crosstab.html')
