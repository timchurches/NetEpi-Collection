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
from casemgr import globals, paged_search, logview
from pages import page_common
import config

class PageOps(page_common.PageOpsBase):
    def do_add(self, ctx, ignore):
        ctx.locals.user_result.reset()
        ctx.push_page('admin_user', None)

    def do_edit(self, ctx, user_id):
        ctx.locals.user_result.reset()
        ctx.push_page('admin_user', int(user_id))

    def do_showlogs(self, ctx, user_id):
        query = globals.db.query('users')
        query.where('user_id = %s', user_id)
        username = query.fetchone().username
        log = logview.AdminLogView(ctx.locals._credentials.prefs, 
                                    'Log for user %r' % username, 
                                    user_id=user_id)
        ctx.push_page('logview', log)

pageops = PageOps()


def page_enter(ctx, user_result):
    user_result.headers = [
        ('enabled', 'Enabled'),
        ('username', 'Username'),
        ('fullname', 'Full Name'),
        ('title', 'Title'),
        (None, config.unit_label),
    ]
    ctx.locals.user_result = user_result
    paged_search.push_pager(ctx, ctx.locals.user_result)
    ctx.add_session_vars('user_result')
 
def page_leave(ctx):
    paged_search.pop_pager(ctx)
    ctx.del_session_vars('user_result')

def page_display(ctx):
    user_ids = [pkey[0] for pkey in ctx.locals.user_result.page_pkeys()]
    ctx.locals.users_units = globals.db.participation_table('unit_users',
                                                            'user_id', 
                                                            'unit_id')
    ctx.locals.users_units.preload(user_ids)
    ctx.locals.title = 'Users'
    if hasattr(ctx.locals, 'unit'):
        ctx.locals.title += ' for %s %s' % (config.unit_label, ctx.locals.unit.name)
    ctx.run_template('admin_users.html')

def page_process(ctx):
    if pageops.page_process(ctx):
        return
