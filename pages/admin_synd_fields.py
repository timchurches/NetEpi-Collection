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
from cocklebur import dbobj
from casemgr import demogfields, globals
from pages import page_common
import config

class PageOps(page_common.PageOpsLeaf):
    def unsaved_check(self, ctx):
        if ctx.locals.demog_fields.has_changed():
            ctx.add_error('WARNING: demographic field changes discarded')

    def commit(self, ctx):
        ctx.locals.demog_fields.update(globals.db)
        globals.db.commit()
        ctx.add_message('Updated demographic fields')
        globals.notify.notify('demogfields', 
                              ctx.locals.demog_fields.syndrome_id)

    def do_update(self, ctx, ignore):
        self.commit(ctx)
        ctx.pop_page()

    def do_dflt(self, ctx, group, index):
        index = int(index)
        ctx.locals.demog_fields[index].reset()
        ctx.locals.cur = group

    def do_grp(self, ctx, op, group):
        if group == 'None':
            group = None
        fields = ctx.locals.demog_fields.group(group)
        ctx.locals.cur = group
        if op == 'on':
            for field in fields:
                field.set(True)
        elif op == 'dflt':
            for field in fields:
                field.reset()
        else:
            for field in fields:
                field.set(False)

pageops = PageOps()


def page_enter(ctx, syndrome_id):
    ctx.locals.demog_fields = demogfields.DemogFields(globals.db, syndrome_id,
                                                      save_initial=True)
    ctx.locals.cur = None
    ctx.add_session_vars('demog_fields', 'cur')

def page_leave(ctx):
    ctx.del_session_vars('demog_fields', 'cur')

def page_display(ctx):
    ctx.locals.contexts = demogfields.contexts
    try:
        synd = ctx.locals.syndrome
    except AttributeError:
        ctx.locals.title = 'Global %s Fields' % config.syndrome_label
    else:
        ctx.locals.title = '%s Fields for %s' %\
            (config.syndrome_label, synd.name)
    ctx.run_template('admin_synd_fields.html')

def page_process(ctx):
    pageops.page_process(ctx)
