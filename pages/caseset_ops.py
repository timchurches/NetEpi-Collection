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

import sys, os
import config
from cocklebur import pageops
from cocklebur.pageops import Confirm, ConfirmSave
from casemgr import globals, caseset, reports
from pages import page_common


def use_caseset(ctx, cs):
    ctx.locals.caseset = ctx.locals.casesets.use(ctx.locals._credentials, cs)
    if ctx.locals.case is not None:
        try:
            ctx.locals.caseset.seek_case(ctx.locals.case.case_row.case_id)
        except ValueError:
            pass
    if ctx.locals.case is None or cs.cur() != ctx.locals.case.case_row.case_id:
        case = ctx.locals.caseset.edit_cur(ctx.locals._credentials)
        page_common.edit_case(ctx, case, push=True)


def make_caseset(ctx, case_ids, name=None):
    if case_ids:
        use_caseset(ctx, caseset.CaseSet(case_ids, name))
    else:
        ctx.add_error('No matching records found')


def person_caseset(ctx, case):
    cs = caseset.PersonCaseSet(ctx.locals._credentials, case.case_row.person_id)
    cs.seek_case(case.case_row.case_id)
    if len(cs) > 1:
        use_caseset(ctx, cs)
    else:
        ctx.add_error('No matching records found')


def caseset_remove(ctx, case_id):
    if ctx.locals.caseset is not None:
        ctx.locals.caseset.remove(case_id)
        if ctx.locals.caseset.caseset_id:
            if not ctx.locals.caseset:
                ctx.locals.casesets.delete(ctx.locals.caseset)
            else:
                ctx.locals.casesets.save(ctx.locals.caseset)
            globals.db.commit()
            ctx.msg('info', 'Caseset saved')
        if not ctx.locals.caseset:
            ctx.locals.caseset = None


def caseset_seek(ctx, delta):
    try:
        ctx.locals.caseset.seek(delta)
    except IndexError:
        return
    case = ctx.locals.caseset.edit_cur(ctx.locals._credentials)
    page_common.edit_case(ctx, case)


class CasesetOps(pageops.PageOpsBase):
    """
    Handle actions resulting from the blue "caseset" banner bar
    """

    def do_caseset_close(self, ctx, ignore):
        ctx.locals.caseset = None

    def do_caseset_remove(self, ctx, ignore):
        if ctx.locals.case:
            self.check_unsaved_or_confirmed(ctx)
            caseset_remove(ctx, ctx.locals.case.case_row.case_id)
            if ctx.locals.caseset is not None:
                case = ctx.locals.caseset.edit_cur(ctx.locals._credentials)
                page_common.edit_case(ctx, case)

    def do_caseset_add(self, ctx, id):
        if not ctx.locals.case:
            return
        case_id = ctx.locals.case.case_row.case_id
        if not id:
            cs = caseset.CaseSet()
            cs.append(case_id)
        else:
            cs = ctx.locals.casesets.load(int(id))
            if cs is None or cs.dynamic:
                return
            cs.append(case_id)
            ctx.locals.casesets.save(cs)
            globals.db.commit()
        ctx.msg('info', 'Added ID %s to case set %r' % (case_id, cs.name))
        if ctx.locals.caseset is None:
            ctx.locals.caseset = cs

    def do_caseset_seek(self, ctx, offset):
        self.check_unsaved_or_confirmed(ctx)
        caseset_seek(ctx, int(offset))
    
    def do_caseset_person(self, ctx, ignore):
        if ctx.locals.case:
            person_caseset(ctx, ctx.locals.case)

    def do_casesets_action(self, ctx, action):
        ctx.locals.casesets_action = None
        args = action.split(':')
        action = args.pop(0)
        if action == 'save':
            ctx.locals.casesets.save(ctx.locals.caseset)
            globals.db.commit()
            ctx.msg('info', 'Caseset saved')
        elif action == 'delete':
            ctx.locals.casesets.delete(ctx.locals.caseset)
            globals.db.commit()
            ctx.msg('info', 'Caseset deleted')
        elif action == 'load':
            if ctx.locals.case and ctx.locals.case.has_changed():
                raise ConfirmSave
            cs = ctx.locals.casesets.load(int(args[0]))
            use_caseset(ctx, cs)
        elif action == 'sort':
            ctx.locals.caseset.sort_by(*args)
        elif action == 'rename':
            ctx.locals.casesets.new_name = ctx.locals.caseset.name
        elif action == 'rename_okay':
            ctx.locals.casesets.rename(ctx.locals.caseset, 
                                       ctx.locals.casesets.new_name)
            if ctx.locals.caseset.caseset_id is not None:
                globals.db.commit()
                ctx.msg('info', 'Caseset saved')
            ctx.locals.casesets.new_name = None
        elif action == 'rename_cancel':
            ctx.locals.casesets.new_name = None
        elif action == 'report':
            self.check_unsaved_or_confirmed(ctx)
            syndrome_id = ctx.locals.case.case_row.syndrome_id
            ctx.pop_page('main')
            ctx.push_page('report_menu', syndrome_id)
            reportparams = reports.new_report(syndrome_id)
            reportparams.label = ctx.locals.caseset.name
            reportparams.caseset_filter(ctx.locals.caseset.case_ids,
                                        ctx.locals.caseset.name)
            ctx.push_page('report_edit', reportparams)
