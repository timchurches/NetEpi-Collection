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

"""
Metadata and methods to support the search / new case / edit case /
result pages
"""

from cocklebur import utils
from casemgr import globals, syndrome, cases

from pages import page_common, caseset_ops

import config

__metaclass__ = type

class SO_Base:

    show_quick = False
    show_caseset = False
    all_syndrome_result = False
    saved = None
    title = None
    pretext = ''
    context = 'search'

    def __init__(self, cred, syndrome_id=None):
        self.cred = cred
        self.syndrome_id = syndrome_id
        self.syndrome_name = None
        if self.syndrome_id is not None:
            self.syndrome_name = syndrome.syndromes[syndrome_id].name
        self.prefs = cred.prefs
        self.view_only = 'VIEWONLY' in cred.rights
        if self.title:
            self.title = self.title % dict(syndrome=self.syndrome_name)

    def result(self, ctx, result):
        if not result:
            description = None
            if result is not None:
                description = getattr(result, 'description', None)
            return self.result_none(ctx, description)
        if result.result_type == 'form':
            return self.result_form(ctx, result.summary_id)
        if result.error:
            return ctx.add_error(result.error)
        one_case = result.single_case()
        if hasattr(self, 'result_one') and one_case:
            self.result_one(ctx, one_case)
        else:
            self.result_many(ctx)

    def result_none(self, ctx, description):
        """ 
        Called when a search returns no results
        """
        if description is not None:
            ctx.msg('warn', 'Nothing found for %s' % description)
        else:
            ctx.msg('warn', 'Nothing found')

    def result_many(self, ctx):
        """
        Called when a search returns more than one case, or one case
        and the SearchOps instance has no result_one implementation.
        """
        ctx.push_page('result')

    def result_form(self, ctx, summary_id):
        """
        Called when a search matches a single form
        """
        ctx.msg('warn', 'Cannot use a form ID here')

    def result_caseset(self, ctx, confirmed, cs):
        pass

    def button_new(self):
        """
        Returns result footer button label and action (eg "New Person")
        """
        return None, None

    def button_edit(self):
        """
        Returns result header button label and action (unused?)
        """
        return None, None

    def button_case(self, id, syndrome_id):
        """
        Returns result per-case button label and action (eg "Edit Case")
        """
        return None, None

    def button_person(self, id):
        """
        Returns result per-person button label and action (eg "New Case")
        """
        return None, None

    def do(self, ctx, confirmed, op, *a):
        """
        Dispatch button actions (as defined above) to searchops methods
        """
        getattr(self, 'do_' + op)(ctx, confirmed, *a)

    def do_case(self, ctx, confirmed, case_id):
        pass


class SO_QuickSearch(SO_Base):

    show_quick = True
    show_caseset = True

    def result_one(self, ctx, case_id):
        ctx.locals.caseset = None
        case = cases.edit_case(ctx.locals._credentials, case_id)
        page_common.edit_case(ctx, case, push=True)

    def result_form(self, ctx, summary_id):
        case, ef = cases.edit_form(ctx.locals._credentials, summary_id)
        ctx.locals.caseset = None
        page_common.edit_case(ctx, case, push=True)
        ctx.push_page('caseform', ef)

    def result_caseset(self, ctx, confirmed, cs):
        caseset_ops.use_caseset(ctx, cs)


class SO_ResultEdit(SO_Base):

    pretext = ('OR enter some details of the case(s) you would like to edit '
               'or view:')

    def button_case(self, id, syndrome_id):
        if self.syndrome_id is not None and self.syndrome_id != syndrome_id:
            return None, None
        if self.view_only:
            label = 'View Case'
        else:
            label = 'Edit Case'
        return 'search_op:case:%s' % id, label

    def do_case(self, ctx, confirmed, case_id):
        selected = ctx.locals.search.result.get_selected()
        if selected:
            caseset_ops.make_caseset(ctx, selected,
                                     ctx.locals.search.result.description)
        else:
            ctx.locals.caseset = None
            case = cases.edit_case(ctx.locals._credentials, int(case_id))
            page_common.edit_case(ctx, case, push=True)


class SO_ResultNewCase(SO_Base):

    def button_person(self, id):
        if not self.view_only:
            return 'search_op:person_new_case:%s' % id, 'New Case'
        return None, None

    def do_person_new_case(self, ctx, confirmed, person_id):
        ctx.locals.caseset = None
        case = page_common.new_case(ctx, self.syndrome_id,
                                    from_search=ctx.locals.search,
                                    use_person_id=int(person_id))
        page_common.edit_case(ctx, case)


class SO_ResultNewPerson(SO_ResultNewCase):

    all_syndrome_result = True

    def button_new(self):
        return 'search_op:new', 'New ' + config.person_label

    def do_new(self, ctx, confirmed):
        ctx.locals.caseset = None
        case = page_common.new_case(ctx, self.syndrome_id,
                                    from_search=ctx.locals.search)
        page_common.edit_case(ctx, case)

    def result_none(self, ctx, description):
        ctx.locals.caseset = None
        case = page_common.new_case(ctx, self.syndrome_id,
                                    from_search=ctx.locals.search)
        page_common.edit_case(ctx, case)


class SearchOps(SO_QuickSearch,SO_ResultEdit,SO_Base):

    """
    Home page "search" button. Syndrome is not fixed, no ability to
    add new cases or persons.
    """
    title = 'Search'
    pretext = ('OR enter some details of the case(s) you would like to edit '
               'or view:')


class EditOps(SO_ResultNewCase,SO_QuickSearch,SO_ResultEdit,SO_Base):
    """
    Per-syndrome "edit case" button. Syndrome is fixed, so we can add new
    cases, but not new persons.
    """
    title = 'Edit case of: %(syndrome)s'


class NewCaseOps(SO_ResultNewPerson,SO_ResultEdit,SO_Base):
    """
    Per-syndrome "new case" button. Can add new persons, and different context
    demog fields are shown.
    """

    title = 'Add a case of: %(syndrome)s'
    pretext = ('Please search now to make sure the %s you are going to add is '
               'not already in the database:') % config.person_label.lower()
    context = 'person'


class AssocContactOps(SO_Base):

    pretext = ('Search for records to associate with this case')
    show_quick = True
    show_caseset = True

    def __init__(self, cred, syndrome_id, case, contacts):
        super(AssocContactOps, self).__init__(cred, syndrome_id)
        self.case_id = case.case_row.case_id
        self.contacts = contacts
        self.title = 'Associate records with %s' % case

    def button_case(self, id, syndrome_id):
        if self.contacts.is_contact(id):
            return None, 'already associated'
        else:
            return 'search_op:assoc:%s' % id, 'Assoc'

    def do_assoc(self, ctx, confirmed, id):
        selected = ctx.locals.search.result.get_selected()
        if selected:
            ctx.push_page('casecontacts_assoc', 'Add', selected)
        else:
            self.result_one(ctx, id)

    def result_one(self, ctx, id):
        ctx.push_page('casecontacts_assoc', 'Add', [int(id)])

    def result_caseset(self, ctx, confirmed, cs):
        ctx.push_page('casecontacts_assoc', 'Add', cs.case_ids)
