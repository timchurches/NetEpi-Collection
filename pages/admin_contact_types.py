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

from cocklebur import utils
from casemgr import globals, contacts

from pages import page_common

import config


class PageOps(page_common.PageOpsBase):
    
    def do_new(self, ctx, ignore):
        if ctx.locals.new_contact_type:
            contacts.new_contact_type(ctx.locals.new_contact_type.strip())
            globals.db.commit()
        ctx.locals.new_contact_type = None

    def do_edit(self, ctx, contact_type_id):
        ctx.push_page('admin_contact_type', int(contact_type_id))

pageops = PageOps()


def page_enter(ctx):
    pass

def page_leave(ctx):
    pass

def page_display(ctx):
    ctx.locals.contact_types = contacts.ContactTypesAdmin()
    ctx.run_template('admin_contact_types.html')

def page_process(ctx):
    pageops.page_process(ctx)
