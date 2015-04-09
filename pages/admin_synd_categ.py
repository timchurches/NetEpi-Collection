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
from casemgr import globals
from pages import page_common
import config


class PageOps(page_common.PageOpsLeaf):
    def unsaved_check(self, ctx):
         if ctx.locals.syndcateg.has_changed():
            ctx.add_error('WARNING: %s changes discarded' %
                           ctx.locals.syndcateg.title)

    def commit(self, ctx):
        if ctx.locals.syndcateg.has_changed():
            ctx.locals.syndcateg.update()
            globals.db.commit()
            globals.notify.notify('syndromes')
        ctx.add_message('Updated %s' % ctx.locals.syndcateg.title)

    def do_update(self, ctx, ignore):
        self.commit(ctx)
        ctx.pop_page()

    def do_up(self, ctx, index):
        ctx.locals.syndcateg.move_up(int(index))

    def do_dn(self, ctx, index):
        ctx.locals.syndcateg.move_down(int(index))

    def do_del(self, ctx, index):
        ctx.locals.syndcateg.delete(int(index))

    def do_add(self, ctx, ignore):
        ctx.locals.syndcateg.new()


pageops = PageOps()

def page_enter(ctx, syndcateg):
    ctx.locals.syndcateg = syndcateg
    ctx.add_session_vars('syndcateg')

def page_leave(ctx):
    ctx.del_session_vars('syndcateg')

def page_display(ctx):
    try:
        synd = ctx.locals.syndrome
    except AttributeError:
        ctx.locals.title = 'Common %s' % ctx.locals.syndcateg.title
    else:
        ctx.locals.title = '%s for %s' % (ctx.locals.syndcateg.title, synd.name)
    ctx.run_template('admin_synd_categ.html')

def page_process(ctx):
    ctx.locals.syndcateg.reorder()
    pageops.page_process(ctx)
