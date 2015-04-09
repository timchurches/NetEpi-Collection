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

from cocklebur import dbobj, form_ui
from cocklebur.form_ui.xmlsave import xmlsave
from cocklebur.form_ui.xmlload import xmlload

import config

from casemgr import globals

from casemgr.admin import formedit, formmeta

from pages import page_common


class DummyFormData: pass


class SetMode(Exception): pass


class ConfirmSave(page_common.ConfirmSave):
    message = 'You have made changes to this form that have not been saved yet'


class PageOps(page_common.PageOpsBase):
    def unsaved_check(self, ctx):
        if ctx.locals.form_meta.has_changed():
            raise ConfirmSave

    def commit(self, ctx):
        if not ctx.locals.form_meta.name:
            if ctx.locals.confirm:
                raise SetMode('saveas_' + ctx.locals.confirm.action)
        ctx.locals.form_meta.save(globals.db)

    def rollback(self, ctx):
        if ctx.locals.form_meta.has_changed():
            try:
                ctx.locals.form_meta.load_version(ctx.locals.form_meta.version)
            except form_ui.NoFormError:
                pass

    def do_preview(self, ctx, ignore):
        ctx.push_page('admin_form_preview')

    def do_deploy(self, ctx, ignore):
        if config.form_rollforward:
            if not ctx.locals.form_meta.name:
                raise SetMode('saveas_deploy')
            ctx.locals.mode = 'edit'
            ctx.push_page('admin_form_deploy')
        else:
            self.check_unsaved_or_confirmed(ctx)
            ctx.locals.form_meta.deploy(globals.db)

    def do_vers(self, ctx, version):
        self.check_unsaved_or_confirmed(ctx)
        ctx.locals.form_meta.load_version(version)
        ctx.locals.mode = 'edit'

    def do_diff(self, ctx, ignore):
        name = ctx.locals.form_meta.name
        to_form = ctx.locals.form_meta.to_form()
        query = globals.db.query('forms')
        query.where('label = %s', name)
        row = query.fetchone()
        from_form = globals.formlib.load(name, row.cur_version)
        from_label = 'Deployed (version %s)' % from_form.version
        to_label = 'Current'
        if ctx.locals.form_meta.version < row.cur_version:
            from_form, to_form = to_form, from_form
            from_label, to_label = to_label, from_label
        ctx.push_page('admin_form_diff', from_form, to_form, 
                                         from_label, to_label)

    def do_rename(self, ctx, ignore):
        self.check_unsaved_or_confirmed(ctx)
        ctx.locals.new_name = ctx.locals.form_meta.name
        ctx.locals.mode = 'rename'

    def do_import(self, ctx, ignore):
        self.check_unsaved_or_confirmed(ctx)
        ctx.locals.mode = 'import'

    def do_export(self, ctx, ignore):
        form_meta = ctx.locals.form_meta
        downloader = page_common.download(ctx, form_meta.name + '.xml',
                                          content_type='text/xml')
        xmlsave(downloader, form_meta.to_form())

    def do_import_form(self, ctx, ignore):
        if len(ctx.locals.import_form) != 1:
            ctx.locals.mode = 'edit'
            raise formmeta.Error('Upload only one file at a time')
        formfile = ctx.locals.import_form[0]
        try:
            ctx.locals.form_meta.from_form(xmlload(formfile.file))
        except formmeta.Errors, e:
            ctx.add_error(e)
        else:
            ctx.locals.mode = 'edit'

    def do_save(self, ctx, ignore):
        ctx.locals.form_meta.save(globals.db)

    def do_saveas(self, ctx, ignore):
        ctx.locals.new_name = ctx.locals.form_meta.name
        ctx.locals.mode = 'saveas'

    def do_delete(self, ctx, ignore):
        ctx.locals.mode = 'delete_confirm'

    def do_delete_okay(self, ctx, ignore):
        ctx.locals.form_meta.delete(globals.db)
        ctx.pop_page()

    def do_delete_cancel(self, ctx, ignore):
        ctx.locals.mode = 'edit'

    def do_name_okay(self, ctx, ignore):
        # Save As/Rename - okay
        try:
            if ctx.locals.mode == 'rename':
                ctx.locals.form_meta.rename(globals.db, ctx.locals.new_name)
                ctx.locals.mode = 'edit'
            elif ctx.locals.mode.startswith('saveas'):
                ctx.locals.form_meta.save_as(globals.db, ctx.locals.new_name)
                if ctx.locals.mode.startswith('saveas_'):
                    self.dispatch(ctx, ctx.locals.mode[len('saveas_'):], [None])
                else:
                    ctx.locals.mode = 'edit'
        except formmeta.Errors, e:
            ctx.add_error(e)

    def do_name_cancel(self, ctx, ignore):
        # Save As/Rename - cancel
        ctx.locals.mode = 'edit'

    def do_add_question(self, ctx, path):
        question = ctx.locals.form_meta.root.new_question(path)
        ctx.push_page('admin_form_edit_question', question)

    def do_add_section(self, ctx, path):
        ctx.locals.section_edit = ctx.locals.form_meta.root.new_section(path)

    def do_edit(self, ctx, path):
        if ctx.locals.section_edit:
            ctx.locals.section_edit.rollback()
            ctx.locals.section_edit = None
        root = ctx.locals.form_meta.root
        if path[0] == 'Q':
            ctx.push_page('admin_form_edit_question', root.edit_question(path))
        elif path[0] == 'S':
            ctx.locals.section_edit = root.edit_section(path)

    def do_section_edit_ok(self, ctx, ignore):
        ctx.locals.section_edit.commit()
        ctx.locals.section_edit = None

    def do_section_edit_cancel(self, ctx, ignore):
        ctx.locals.section_edit.rollback()
        ctx.locals.section_edit = None

    def do_copy(self, ctx, ignore):
        root = ctx.locals.form_meta.root
        ctx.locals.form_cutbuff = root.copy(ctx.locals.selected)

    def do_cut(self, ctx, ignore):
        root = ctx.locals.form_meta.root
        ctx.locals.form_cutbuff = root.cut(ctx.locals.selected)

    def do_paste(self, ctx, path):
        if ctx.locals.form_cutbuff:
            ctx.locals.form_meta.root.paste(path, ctx.locals.form_cutbuff)

pageops = PageOps()


def page_enter(ctx, name):
    cred = ctx.locals._credentials
    if name is None:
        form_row = globals.db.new_row('forms')
    else:
        query = globals.db.query('forms')
        query.where('label = %s', name)
        form_row = query.fetchone()
    try:
        ctx.locals.form_meta = formmeta.FormMeta(form_row, cred)
    except formmeta.Errors, e:
        ctx.add_error(e)
        ctx.pop_page()
        return
    ctx.add_session_vars('form_meta')
    ctx.locals.section_edit = None
    ctx.add_session_vars('section_edit')
    ctx.locals.mode = 'edit'
    ctx.add_session_vars('mode')
    ctx.locals.vers_select = ''
    ctx.add_session_vars('vers_select')
    ctx.locals.form_data = DummyFormData()
    ctx.add_session_vars('form_data')

def page_leave(ctx):
    ctx.del_session_vars('form_meta', 'section_edit', 'mode', 
                         'vers_select', 'form_data')

def page_display(ctx):
    if not page_common.send_download(ctx):
        form_meta = ctx.locals.form_meta
        if ctx.locals.mode == 'edit':
            ctx.locals.vers_select = form_meta.version
        ctx.locals.used_by = form_meta.used_by(globals.db)
        ctx.locals.form_disabled = True
        ctx.run_template('admin_form_edit.html')

def page_process(ctx):
    try:
        if pageops.page_process(ctx):
            return
        elif ctx.locals.form_meta.vers_changed(ctx.locals.vers_select):
            pageops.dispatch(ctx, 'vers', (ctx.locals.vers_select,))
    except SetMode, e:
        ctx.locals.mode = e.args[0]
    except formmeta.Errors, e:
        ctx.add_error(e)
        ctx.locals.mode = 'edit'
