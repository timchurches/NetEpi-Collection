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
from casemgr import globals, persondupecfg, persondupe
from pages import page_common

import config

def get_dupecfg(ctx):
    config = ctx.locals._credentials.prefs.get('persondupecfg')
    if config is None:
        config = persondupecfg.new_persondupecfg()
    return config.start_editing()


def save_dupecfg(ctx):
    ctx.locals.dupecfg.stop_editing()
    ctx.locals._credentials.prefs.set('persondupecfg', ctx.locals.dupecfg)
    ctx.locals._credentials.prefs.commit(globals.db, immediate=True)
    ctx.locals.dupecfg = ctx.locals.dupecfg.start_editing()
    ctx.add_message('Duplicate %s matching configuration saved' % 
                    config.person_label)


class PageOps(page_common.PageOpsBase):

    def do_edit(self, ctx, index):
        ctx.push_page('dupepersons_config_edit', int(index))

    def do_new(self, ctx, ignore):
        ctx.push_page('dupepersons_config_edit', None)

    def do_reset(self, ctx, ignore):
        ctx.locals.dupecfg.reset()

    def do_revert(self, ctx, ignore):
        ctx.locals.dupecfg = get_dupecfg(ctx)

    def do_save(self, ctx, ignore):
        save_dupecfg(ctx)

    def do_view(self, ctx, ignore):
        ctx.locals.dupecfg.stop_editing()
        ctx.locals.last_dupe = persondupe.last_run(globals.db)
        try:
            dp = persondupe.loaddupe(globals.db)
        except persondupe.DupeRunning, m:
            ctx.add_error(m)
            # Explicit rollback so page_display can perform TX
            globals.db.rollback()
        else:
            ctx.push_page('dupepersons', dp,
                          'Possible duplicate %s records' % config.person_label)

    def do_scan(self, ctx, updated_only):
        save_dupecfg(ctx)
        persondupe.persondupe(globals.db, ctx.locals.dupecfg,
                              updated_only=bool(updated_only))
        ctx.add_message('Cross-check initiated - this will take some time')

page_process = PageOps().page_process


def page_enter(ctx):
    # XXX
    ctx.locals.dupecfg = get_dupecfg(ctx)
    ctx.locals.last_dupe = persondupe.last_run(globals.db)
    ctx.add_session_vars('dupecfg', 'last_dupe')


def page_leave(ctx):
    ctx.del_session_vars('dupecfg', 'last_dupe')


def page_display(ctx):
    ctx.run_template('dupepersons_config.html')

