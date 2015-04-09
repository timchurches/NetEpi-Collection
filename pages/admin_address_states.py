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
from casemgr import globals, addressstate
from pages import page_common
import config


class PageOps(page_common.PageOpsLeaf):
    def unsaved_check(self, ctx):
         if ctx.locals.address_states.has_changed():
            ctx.add_error('WARNING: address state changes discarded')

    def commit(self, ctx):
        if ctx.locals.address_states.has_changed():
            ctx.locals.address_states.update()
            globals.db.commit()
            globals.notify.notify('address_states')
        ctx.add_message('Updated states')

    def do_update(self, ctx, ignore):
        self.commit(ctx)
        ctx.pop_page()

    def do_del(self, ctx, index):
        ctx.locals.address_states.delete(int(index))

    def do_add(self, ctx, ignore):
        ctx.locals.address_states.new()


pageops = PageOps()

def page_enter(ctx):
    ctx.locals.address_states = addressstate.EditAddressStates()
    ctx.add_session_vars('address_states')

def page_leave(ctx):
    ctx.del_session_vars('address_states')

def page_display(ctx):
    ctx.run_template('admin_address_states.html')

def page_process(ctx):
    pageops.page_process(ctx)
