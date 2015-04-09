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

from casemgr import dataexport, exportselect
from pages import page_common

import config


class PageOps(page_common.PageOpsBase):
    def do_select_all(self, ctx, ignore):
        ctx.locals.exportsel.select_all_forms()

    def do_clear_all(self, ctx, ignore):
        ctx.locals.exportsel.clear_forms()

    def do_doexport(self, ctx, ignore):
        if ctx.locals.changed:
            ctx.add_message('Mode has changed, check parameters')
        else:
            es = ctx.locals.exportsel
            page_common.csv_download(ctx, es.row_gen(), es.filename())

    def page_process(self, ctx):
        ctx.locals.changed = ctx.locals.exportsel.refresh(ctx.locals._credentials)
        page_common.PageOpsBase.page_process(self, ctx)

page_process = PageOps().page_process


def page_enter(ctx, syndrome_id):
    ctx.locals.exportsel = exportselect.ExportSelect(syndrome_id)
    ctx.locals.exportsel.refresh(ctx.locals._credentials)
    ctx.add_session_vars('exportsel')

def page_leave(ctx):
    ctx.del_session_vars('exportsel')

def page_display(ctx):
    if not page_common.send_download(ctx):
        ctx.run_template('export.html')
