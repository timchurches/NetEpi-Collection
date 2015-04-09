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

from casemgr import globals, persondupe
from casemgr.dataimp.dataimp import DataImp, PreviewImport, locked_case_ids

from pages import page_common, caseset_ops

import config

class PageOps(page_common.PageOpsBase):

    def do_import(self, ctx, ignore):
        imp = DataImp(ctx.locals._credentials,
                      ctx.locals.editor.syndrome_id, 
                      ctx.locals.dataimp_src, 
                      ctx.locals.editor.importrules)
        if imp.errors:
            for error in imp.errors.get(None):
                ctx.msg('err', error)
        else:
            globals.db.commit()
            ctx.add_message(imp.status)
            ctx.locals.dataimp_src.release()
            ctx.locals.dataimp_tabs.select('select')
            if imp.locked_cases:
                ctx.add_message('record ID(s) %s were source-locked and have '
                                'not been updated.' % 
                                ', '.join(map(str, imp.locked_cases)))
#                caseset_ops.make_caseset(ctx, imp.locked_cases,
#                            'Data import source-locked cases')
            if imp.conflict_cnt:
                dp = persondupe.loadconflicts(globals.db)
                ctx.push_page('dupepersons', dp, 'Import conflicts')
            else:
                ctx.pop_page()

    def do_excluded(self, ctx, ignore):
        case_ids = locked_case_ids(ctx.locals._credentials,
                                   ctx.locals.editor.syndrome_id, 
                                   ctx.locals.dataimp_src, 
                                   ctx.locals.editor.importrules)
        caseset_ops.make_caseset(ctx, case_ids,
                            'Data import source-locked cases')



page_process = PageOps().page_process

def page_display(ctx):
    ctx.locals.preview = PreviewImport(ctx.locals._credentials,
                                       ctx.locals.editor.syndrome_id, 
                                       ctx.locals.dataimp_src, 
                                       ctx.locals.editor.importrules)
    if ctx.locals.preview.errors:
        for error in ctx.locals.preview.errors.get():
            ctx.msg('err', error)
        ctx.msg('err', '%s error(s) occurred - fix before importing' %\
                                        ctx.locals.preview.errors.count())
    ctx.run_template('dataimp_preview.html')
