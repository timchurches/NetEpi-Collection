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
import difflib
import itertools

from cocklebur import dbobj

from casemgr import globals

from casemgr.admin import formmeta, tablediff

from pages import page_common

import config

class ConfirmSave(page_common.ConfirmSave):
    message = 'You have made changes to this form that have not been saved yet'
    buttons = [
        ('continue', 'Continue Editing'),
        ('savefirst', 'Save First'),
    ]

null_rollforward_msg = ('No fields are to be rolled forward! Either create a '
                        'new form, or roll forward some fields.')

class PageOps(page_common.PageOpsBase):
    def unsaved_check(self, ctx):
        if ctx.locals.form_meta.has_changed():
            raise ConfirmSave

    def commit(self, ctx):
        assert ctx.locals.form_meta.name
        ctx.locals.form_meta.save(globals.db)

    def do_back(self, ctx, ignore):
        # Don't want the standard do_back's check_unsaved_or_confirmed()
        ctx.pop_page()

    def do_deploy(self, ctx, ignore):
        if not ctx.locals.diffs.okay():
            raise page_common.PageError('Resolve column incompatibilities first')
        if ctx.locals.diffs.is_drop_all():
            raise page_common.PageError(null_rollforward_msg)
        rollforward_map = ctx.locals.diffs.rollforward_map()
        self.check_unsaved_or_confirmed(ctx)
        if ctx.locals.form_meta.has_changed():
            ctx.locals.form_meta.save(globals.db)
        ctx.locals.form_meta.deploy(globals.db, rollforward_map)
        ctx.pop_page()

    def do_rename(self, ctx, ignore):
        try:
            ctx.locals.diffs.rename(ctx.locals.old_select, 
                                    ctx.locals.new_select)
        except tablediff.TableDiffError, e:
            raise page_common.PageError(str(e))

    def do_recreate(self, ctx, ignore):
        try:
            ctx.locals.diffs.recreate(ctx.locals.old_select,
                                      ctx.locals.new_select)
        except tablediff.TableDiffError, e:
            raise page_common.PageError(str(e))

pageops = PageOps()


def page_enter(ctx):
    deployed_table = globals.formlib.tablename(ctx.locals.form_meta.name, 
                                           ctx.locals.form_meta.vers_deployed())
    try:
        table_desc_a = globals.db.get_table(deployed_table)
    except KeyError:
        table_desc_a = None
    form = ctx.locals.form_meta.to_form()
    form.update_columns()
    table_desc_b = dbobj.table_describer.TableDescriber(None, 'xx')
    for column in form.columns:
        table_desc_b.column(column.name, column.type, **column.kwargs)
    ctx.locals.diffs = tablediff.describe_changes(table_desc_a, table_desc_b)
    ctx.locals.old_select = ctx.locals.new_select = None
    ctx.add_session_vars('diffs', 'old_select', 'new_select')

def page_leave(ctx):
    ctx.del_session_vars('diffs', 'old_select', 'new_select')

def page_display(ctx):
    if ctx.locals.diffs.is_drop_all() and not ctx.req_equals('deploy'):
        ctx.msg('warn', null_rollforward_msg)
    ctx.run_template('admin_form_deploy.html')

def page_process(ctx):
    try:
        if pageops.page_process(ctx):
            return
    except formmeta.Errors, e:
        ctx.add_error(e)
