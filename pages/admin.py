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
from cocklebur import datetime
from casemgr import globals, syndrome, logview, rights
from casemgr.casestatus import EditSyndromeCaseStates
from casemgr.caseassignment import EditSyndromeCaseAssignment
from casemgr.admin.search import Searches
from pages import page_common
import config

# NOTE: Much of the logic of this page is implemented in the
# casemgr.admin.search module.

class PageOps(page_common.PageOpsBase):

    def do_demog_fields(self, ctx, ignore):
        ctx.push_page('admin_synd_fields', None)

    def do_case_status(self, ctx, ignore):
        ctx.push_page('admin_synd_categ', EditSyndromeCaseStates(None))

    def do_case_assignment(self, ctx, ignore):
        ctx.push_page('admin_synd_categ', EditSyndromeCaseAssignment(None))

    def do_address_states(self, ctx, ignore):
        ctx.push_page('admin_address_states')

    def do_contact_types(self, ctx, ignore):
        ctx.push_page('admin_contact_types')

    def do_new(self, ctx, search_name):
        ctx.locals.admin_search.new(ctx, search_name, 
                                    ctx.locals._credentials.prefs)

    def do_search(self, ctx, search_name):
        ctx.locals.admin_search.search(ctx, search_name, 
                                       ctx.locals._credentials.prefs)

    def do_reset(self, ctx, ignore):
        ctx.locals.admin_search.reset()

    def do_system_log(self, ctx, ignore):
        log = logview.SystemLogView(ctx.locals._credentials.prefs, 'System log')
        ctx.push_page('logview', log)

    def do_view_rights(self, ctx, ignore):
        ctx.push_page('admin_view_right', ctx.locals.view_right)

pageops = PageOps()


def page_enter(ctx):
    ctx.locals.admin_search = Searches()
    ctx.locals.form_cutbuff = None
    ctx.locals.feq_cutbuff = None
    ctx.add_session_vars('admin_search', 'form_cutbuff', 'feq_cutbuff')

def page_leave(ctx):
    ctx.del_session_vars('admin_search', 'form_cutbuff', 'feq_cutbuff')

def page_display(ctx):
    query = globals.db.query('groups', order_by='group_name')
    ctx.locals.group_options = query.fetchcols(('group_id', 'group_name'))
    ctx.locals.group_options.insert(0, ('', 'Any'))
    ctx.locals.synd_options = syndrome.syndromes.optionexpr()
    ctx.locals.synd_options.insert(0, ('', ''))
    ctx.locals.rights_options = rights.available.options
    ctx.run_template('admin.html')

def page_process(ctx):
    ctx.locals.admin_search.clear_errors()
    if pageops.page_process(ctx):
        return
