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
from pages import page_common

import config

class PageOps(page_common.PageOpsLeaf):
    def unsaved_check(self, ctx):
        if ctx.locals.wikiedit.has_changed():
            ctx.add_error('WARNING: %s changes discarded' % 
                           ctx.locals.wikiedit.prompt)

    def commit(self, ctx):
        ctx.locals.wikiedit.update()

    def do_update(self, ctx, ignore):
        self.commit(ctx)
        ctx.pop_page()

pageops = PageOps()

class WikiEdit:
    def __init__(self, ns, field, prompt, title, style):
        self.ns = ns
        self.field = field
        self.prompt = prompt
        self.title = title
        self.style = style
        self.value = getattr(self.ns, self.field, '')

    def has_changed(self):
        return self.value != getattr(self.ns, self.field, '')

    def update(self):
        setattr(self.ns, self.field, self.value)

def page_enter(ctx, *args):
    ctx.locals.wikiedit = WikiEdit(*args)
    ctx.add_session_vars('wikiedit')

def page_leave(ctx):
    ctx.del_session_vars('wikedit')

def page_display(ctx):
    ctx.run_template('admin_wikiedit.html')

def page_process(ctx):
    pageops.page_process(ctx)
