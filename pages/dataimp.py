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

from casemgr import globals
from casemgr.dataimp import editor
from casemgr.dataimp.datasrc import DataImpSrc, NullDataImpSrc
from casemgr.tabs import Tabs

from pages import page_common

import config

class PageOps(page_common.PageOpsBase):

    def page_process(self, ctx):
        ctx.locals.editor.update_rules()
        src_file = getattr(ctx.locals, 'src_file', None)
        if src_file:
            if len(src_file) > 1:
                raise page_common.PageError('Choose one file')
            new_dataimp_src = DataImpSrc(src_file[0].filename, 
                                         src_file[0].file)
            if new_dataimp_src:
                if ctx.locals.dataimp_src:
                    ctx.locals.dataimp_src.release()
                ctx.locals.dataimp_src = new_dataimp_src
                self.update_preview(ctx)
                if (ctx.locals.dataimp_src.preview 
                        and ctx.locals.dataimp_src.preview.n_rows > 1000):
                    ctx.msg('warn', 'WARNING: importing a large number of records'
                                  ' may be very slow and time-outs may occur')

        page_common.PageOpsBase.page_process(self, ctx)

    def update_preview(self, ctx):
        if ctx.locals.dataimp_src:
            ctx.locals.dataimp_src.update_preview(ctx.locals.editor.importrules)
            if ctx.locals.dataimp_src.preview.error:
                ctx.add_error(ctx.locals.dataimp_src.preview.error)
            return not bool(ctx.locals.dataimp_src.preview.error)

    def unsaved_check(self, ctx):
        if ctx.locals.editor.has_changed():
            raise page_common.ConfirmSave

    def rollback(self, ctx):
        ctx.locals.editor.revert()

    def commit(self, ctx):
        ctx.locals.editor.save()
        globals.db.commit()
        ctx.add_message('Rule set %r saved' % 
                        ctx.locals.editor.importrules.name) 

    # Tab actions
    def do_tab(self, ctx, tab):
        if ctx.locals.dataimp_tabs.selected == 'params':
            self.update_preview(ctx)
        ctx.locals.dataimp_tabs.select(tab)

    def do_view(self, ctx, ignore):
        if ctx.locals.dataimp_src:
            if self.update_preview(ctx):
                ctx.push_page('dataimp_view')
        else:
            ctx.add_error('No data to view')

    def do_save(self, ctx, ignore):
        if not ctx.locals.editor.importrules.name:
            ctx.locals.dataimp_tabs.select('params')
            ctx.add_error('Specify a rule set name before saving') 
        else:
            self.commit(ctx)

    def do_revert(self, ctx, ignore):
        if ctx.locals.editor.has_changed():
            if not self.confirmed:
                raise page_common.ConfirmRevert
            ctx.locals.editor.revert()

    def do_export(self, ctx, ignore):
        downloader = page_common.download(ctx, 'importdef.xml')
        downloader.write(ctx.locals.editor.rules_xml())

    def do_import(self, ctx, ignore):
        if ctx.locals.dataimp_src:
            if self.update_preview(ctx):
                ctx.push_page('dataimp_preview')
        else:
            ctx.add_error('No data uploaded')

    # Rule sets tab
    def do_new(self, ctx, ignore):
        if ctx.locals.editor.has_changed() and not self.confirmed:
            raise page_common.ConfirmSave
        ctx.locals.editor = editor.new(ctx.locals.editor.syndrome_id)
        ctx.locals.dataimp_tabs.select('params')

    def do_load(self, ctx, id):
        if ctx.locals.editor.has_changed() and not self.confirmed:
            raise page_common.ConfirmSave
        syndrome_id = ctx.locals.editor.syndrome_id
        ctx.locals.editor = editor.load(ctx, syndrome_id, int(id))
        ctx.locals.dataimp_tabs.select('params')

    def do_imprules(self, ctx, ignore):
        if ctx.locals.confirm is not None:
            new_editor = ctx.locals.confirm.editor
        else:
            if len(ctx.locals.imprules_file) != 1:
                raise page_common.PageError('Choose one file')
            file = ctx.locals.imprules_file[0].file
            syndrome_id = ctx.locals.editor.syndrome_id
            new_editor = editor.load_file(ctx, syndrome_id, None, file)
            if ctx.locals.editor.has_changed():
                raise page_common.ConfirmSave(editor=new_editor)
        ctx.locals.editor = new_editor
        ctx.locals.dataimp_tabs.select('params')

    # Params tab
    def do_delete(self, ctx, ignore):
        if ctx.locals.editor.def_id is None:
            if not self.confirmed and ctx.locals.editor.has_changed():
                raise page_common.ConfirmDelete
            ctx.locals.editor.revert()
        else:
            if not self.confirmed:
                raise page_common.ConfirmDelete
            ctx.locals.editor.delete()
            globals.db.commit()
        ctx.locals.dataimp_tabs.select('select')

    # Fields tab
    def do_edit(self, ctx, group, field):
        ctx.push_page('dataimp_editfield', group, field)

    def do_add_field(self, ctx, field):
        ctx.locals.add_field = None
        group, field = ctx.locals.editor.add_field(field, ctx.locals.srcsel)
        ctx.push_page('dataimp_editfield', group, field)
        ctx.locals.srcsel = None

    def do_add_form(self, ctx, form):
        ctx.locals.add_form = None
        ctx.locals.editor.add_form(form)

    def do_del_form(self, ctx, form):
        ctx.locals.editor.del_form(form)

page_process = PageOps().page_process


def make_tabs():
    tabs = Tabs()
    tabs.add('select', 'Rule sets')
    tabs.spacer()
    tabs.add('params', 'Params')
    tabs.spacer()
    tabs.add('upload', 'Upload Data')
    tabs.add('view', 'View Data', action=True)
    tabs.spacer()
    tabs.add('fields', 'Fields')
    tabs.add('save', 'Save Rules', action=True)
    tabs.add('export', 'XML Export', action=True)
    tabs.add('revert', 'Revert Rules', action=True, danger=True)
    tabs.spacer()
    tabs.add('import', 'Import', action=True)
    tabs.done()
    return tabs

def page_enter(ctx, syndrome_id):
    ctx.locals.dataimp_tabs = make_tabs()
    ctx.locals.editor = editor.new(syndrome_id)
    ctx.locals.dataimp_src = NullDataImpSrc
    ctx.locals.srcsel = None
    ctx.add_session_vars('dataimp_tabs', 'editor', 'dataimp_src', 'srcsel')

def page_leave(ctx):
    dataimp_src = getattr(ctx.locals, 'dataimp_src', None)
    if dataimp_src:
        dataimp_src.release()
    ctx.del_session_vars('dataimp_tabs', 'editor', 'dataimp_src', 'srcsel')

def page_display(ctx):
    if not page_common.send_download(ctx):
        ctx.run_template('dataimp.html')
