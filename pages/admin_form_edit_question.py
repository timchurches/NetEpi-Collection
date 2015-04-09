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
import copy
from pages import page_common

import config

class PageOps(page_common.PageOpsBase):
    def unsaved_check(self, ctx):
        if ctx.locals.form_meta.has_changed():
            raise page_common.ConfirmSave

    def commit(self, ctx):
        raise NotImplementedError()

    def rollback(self, ctx):
        ctx.locals.question.rollback()

    def do_cancel(self, ctx, ignore):
        # Don't use common method as we can't check for modifications to the
        # question object (yet).
        self.rollback(ctx)
        ctx.pop_page()

    def do_okay(self, ctx, ignore):
        if self.first_error is None:
            ctx.locals.question.commit()
            ctx.pop_page()
        else:
            ctx.locals.selected = 'input_%s' % self.first_error

    def do_op(self, ctx, *args):
        selected = ctx.locals.question.op(*args)
        if selected is not None:
            ctx.locals.selected = 'input_%s' % selected

    def _labelidx(self, ctx):
        return [int(label.replace('select:input_', '')) 
                for label in ctx.locals.cutsel.split(',')]

    def do_copy(self, ctx, ignore):
        ctx.locals.feq_cutbuff = ctx.locals.question.copy(self._labelidx(ctx))

    def do_cut(self, ctx, ignore):
        ctx.locals.feq_cutbuff = ctx.locals.question.cut(self._labelidx(ctx))
        ctx.locals.selected = 'question'

    def do_paste(self, ctx, index):
        if ctx.locals.feq_cutbuff:
            index = int(index)
            ctx.locals.question.paste(index, ctx.locals.feq_cutbuff)
            ctx.locals.selected = 'input_%s' % index


pageops = PageOps()

def page_enter(ctx, question):
    ctx.locals.question = question
    ctx.locals.selected = 'question'
    ctx.add_session_vars('question', 'selected')

def page_leave(ctx):
    ctx.del_session_vars('question', 'selected')

def page_display(ctx):
    ctx.locals.form_disabled = True
    ctx.run_template('admin_form_edit_question.html')

def page_process(ctx):
    ctx.locals.question.clear_err()
    for input in ctx.locals.question.inputs:
        input.page_process()
    pageops.first_error = ctx.locals.question.check()
    if pageops.page_process(ctx):
        return
