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
from casemgr import user_search
from pages import page_common

import config

class PageOps(page_common.PageOpsBase):
    def do_reset(self, ctx, pref):
        prefs = ctx.locals._credentials.prefs
        prefs.reset(pref)
        setattr(ctx.locals, pref, str(prefs.get(pref)))

pageops = PageOps()


pref_list = (
    'phonetic_search',
    'results_per_page',
    'font_size',
    'jscalendar',
    'nobble_back_button',
    'date_style',
)

def page_enter(ctx):
    prefs = ctx.locals._credentials.prefs
    for pref in pref_list:
        setattr(ctx.locals, pref, str(prefs.get(pref)))
        ctx.add_session_vars(pref)
    user = ctx.locals._credentials.user
    ctx.locals.privacy = user_search.PrivacyEdit(user.user_id)
    ctx.add_session_vars('privacy')

def page_display(ctx):
    ctx.run_template('prefsedit.html')

def page_process(ctx):
    prefs = ctx.locals._credentials.prefs
    for pref in pref_list:
        prefs.set_from_str(pref, getattr(ctx.locals, pref))
    if pageops.page_process(ctx):
        return

def page_leave(ctx):
    if hasattr(ctx.locals, 'privacy'):
        ctx.locals.privacy.update()
    for pref in pref_list:
        ctx.del_session_vars(pref)
    ctx.del_session_vars('privacy')
