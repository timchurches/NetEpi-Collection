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
from casemgr import logview, globals, tasks, paged_search, user_edit
from casemgr import persondupecfg, persondupe
from pages import page_common
import config

def can_sponsor(cred):
    return (config.user_registration_mode in ('invite', 'sponsor')
            and 'SPONSOR' in cred.rights)

class PageOps(page_common.PageOpsBase):

    def do_manualdupe(self, ctx, ignore):
        if 'DATAMGR' in ctx.locals._credentials.rights:
            ctx.push_page('manualdupe')

    def do_dupecfg(self, ctx, ignore):
        if 'DATAMGR' in ctx.locals._credentials.rights:
            ctx.push_page('dupepersons_config')
        
    def do_dupecases(self, ctx, ignore):
        if 'DATAMGR' in ctx.locals._credentials.rights:
            ctx.push_page('dupecases_config')

    def do_conflicts(self, ctx, ignore):
        if 'IMPORT' in ctx.locals._credentials.rights:
            dp = persondupe.loadconflicts(globals.db)
            ctx.push_page('dupepersons', dp, 'Import conflicts')

    def do_users(self, ctx, ignore):
        if 'UNITADMIN' in ctx.locals._credentials.rights:
            ctx.push_page('useradmin')

    def do_taskqueue(self, ctx, ignore):
        if 'TQADMIN' in ctx.locals._credentials.rights:
            prefs = ctx.locals._credentials.prefs
            query = tasks.user_workqueues_query(ctx.locals._credentials,
                                                order_by='name')
            search = paged_search.SortablePagedSearch(globals.db, prefs, query)
            ctx.push_page('user_queues', search)

    def do_details(self, ctx, ignore):
        ue = user_edit.EditSelf(ctx.locals._credentials)
        ctx.push_page('useredit', ue)

    def do_prefsedit(self, ctx, ignore):
        ctx.push_page('prefsedit')

    def do_viewlog(self, ctx, ignore):
        creds = ctx.locals._credentials
        log = logview.UserLogView(creds.prefs, 
                                  'Log for user %r' % creds.user.username,
                                  user_id=creds.user.user_id)
        ctx.push_page('logview', log)

    def do_user_browser(self, ctx, ignore):
        if config.user_browser:
            ctx.push_page('user_browser')

    def do_user_sponsor(self, ctx, ignore):
        if can_sponsor(ctx.locals._credentials):
            ctx.push_page('user_sponsor')

pageops = PageOps()


def page_display(ctx):
    ctx.run_template('tools.html')

def page_process(ctx):
    pageops.page_process(ctx)
