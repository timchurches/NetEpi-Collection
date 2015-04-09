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

from cocklebur import utils, dbobj
from casemgr import globals, contacts

from pages import page_common

import config

class MergeConfirm(page_common.Confirm):
    title = 'Merge contact types'
    buttons = [
        ('continue', 'No'),
        ('confirm', 'Yes, Continue'),
    ]


class DeleteConfirm(page_common.Confirm):
    title = 'Delete contact type'
    buttons = [
        ('continue', 'No'),
        ('confirm', 'Yes, Continue'),
    ]


class PageOps(page_common.PageOpsBase):
    
    def do_rename(self, ctx, ignore):
        if ctx.locals.contact_type.name != ctx.locals.contact_type.new_name:
            try:
                ctx.locals.contact_type.rename()
            except dbobj.DuplicateKeyError:
                raise dbobj.DuplicateKeyError('Name is already used')
            globals.db.commit()
            ctx.msg('info', 'Renamed contact type %r to %r' % 
                        (ctx.locals.contact_type.name, 
                        ctx.locals.contact_type.new_name))
            ctx.pop_page()

    def do_merge(self, ctx, ignore):
        ct = ctx.locals.contact_type
        if not ct.merge_to_id:
            return
        if not self.confirmed:
            raise MergeConfirm(message='This will merge %d contact(s) of type '
                               '%r into %r. This cannot be undone. Are you '
                               'sure you wish to proceed?' % 
                             (ct.count, ct.name, ct.type_label(ct.merge_to_id)))
        ct.merge()
        ctx.msg('info', 'Merged %d contact(s) of type %r to %r' % 
                        (ct.count, ct.name, ct.type_label(ct.merge_to_id)))
                     
        globals.db.commit()
        ctx.pop_page()

    def do_delete(self, ctx, ignore):
        ct = ctx.locals.contact_type
        if not self.confirmed:
            raise DeleteConfirm(message='This will delete %d contact(s) of '
                                'type %r. This cannot be undone. Are you '
                                'sure you wish to proceed?' % 
                                (ct.count, ct.name))
        ct.delete()
        ctx.msg('info', 'Deleted %d contact(s) of type %r' % 
                        (ct.count, ct.name))
        globals.db.commit()
        ctx.pop_page()


pageops = PageOps()


def page_enter(ctx, contact_type_id):
    ctx.locals.contact_type = contacts.ContactTypeEdit(contact_type_id)
    ctx.add_session_vars('contact_type')

def page_leave(ctx):
    ctx.del_session_vars('contact_type')

def page_display(ctx):
    ctx.locals.contact_type.refresh()
    ctx.run_template('admin_contact_type.html')

def page_process(ctx):
    pageops.page_process(ctx)
