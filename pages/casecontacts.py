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

from cocklebur import dbobj, utils
from casemgr import globals, paged_search, contacts, caseset
from pages import page_common, search_ops, caseset_ops
import config

class ConfirmRemove(page_common.Confirm):
    mode = 'remove_selected'
    title = 'Dissociate selected records?'
    message = 'Dissociate selected records?'
    buttons = [
        ('continue', 'No'),
        ('confirm', 'Yes'),
    ]


class PageOps(page_common.PageOpsBase):
    
    def do_remove_selected(self, ctx, ignore):
        keys = ctx.locals.contacts.selected or ctx.locals.contacts.pkeys
        case_ids = [k[0] for k in keys]
        if len(case_ids) > 1 and not self.confirmed:
            raise ConfirmRemove(message='Dissociate %d cases with ID %s?' % 
                              (len(case_ids), ctx.locals.case.case_row.case_id))
        contacts.dissociate_contacts(ctx.locals.case.case_row.case_id, case_ids)
        case = ctx.locals.case
        cs_name = '%d records dissocated from %s, %s (ID %s)' % (
                len(case_ids), case.person.surname, 
                case.person.given_names, case.case_row.case_id)
        ctx.locals.casesets.use(ctx.locals._credentials, 
                                caseset.CaseSet(case_ids, cs_name))
        ctx.locals.contacts.select([])
        ctx.locals.contacts.reset()
        ctx.locals.case.user_log('Dissociated ID(s) %s' % 
                                    utils.commalist(case_ids, 'and'))
        globals.db.commit()

    def do_makecaseset(self, ctx, id):
        ctx.pop_page()
        if ctx.locals.contacts.selected:
            case_ids = ctx.locals.contacts.selected_case_ids()
            caseset_ops.make_caseset(ctx, case_ids,
                'Select %ss of ID %s' % (config.contact_label.lower(), 
                                         ctx.locals.case.case_row.case_id))
        else:
            cs = caseset.ContactCaseSet(ctx.locals._credentials,
                                        ctx.locals.case.case_row.case_id)
            caseset_ops.use_caseset(ctx, cs)

    def do_add_contacts(self, ctx, id):
        ops = search_ops.AssocContactOps(ctx.locals._credentials,
                                         int(ctx.locals.contact_syndrome),
                                         ctx.locals.case,
                                         ctx.locals.contacts)
        ctx.locals.contacts.reset()
        ctx.push_page('search', ops)

    def do_editcontacts(self, ctx, ignore):
        if ctx.locals.contacts.selected:
            case_ids = ctx.locals.contacts.selected_case_ids()
            ctx.push_page('casecontacts_assoc', 'Update', case_ids)

pageops = PageOps()



def page_enter(ctx):
    ctx.locals.contacts = contacts.ContactSearch(ctx.locals._credentials.prefs, 
                                               ctx.locals.case.case_row.case_id,
                                               ctx.locals.case.deleted)
    paged_search.push_pager(ctx, ctx.locals.contacts)
    ctx.add_session_vars('contacts')


def page_leave(ctx):
    paged_search.pop_pager(ctx)
    ctx.del_session_vars('contacts')


def page_display(ctx):
    ctx.run_template('casecontacts.html')


def page_process(ctx):
    try:
        ctx.locals.contacts.page_process(ctx)
        if pageops.page_process(ctx):
            return
    except dbobj.DatabaseError, e:
        ctx.add_error(e)
