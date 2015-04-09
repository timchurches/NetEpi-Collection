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
from casemgr import globals, personmerge, persondupe, cases
from pages import page_common, caseset_ops
import config


class PageOps(page_common.PageOpsBase):
    def do_showmerge(self, ctx, ignore):
        ctx.locals.personmerge.normalise()
        ctx.push_page('mergeperson_detail')

    def do_exclude(self, ctx, ignore):
        ctx.locals.personmerge.exclude()
        ctx.pop_page()

    def do_include(self, ctx, ignore):
        ctx.locals.personmerge.include()

    def do_cases(self, ctx, ignore):
        caseset_ops.make_caseset(ctx, ctx.locals.personmerge.cases(),
                            'Cases associated with a prospective person merge')


pageops = PageOps()

def page_enter(ctx, personmerge):
    ctx.locals.personmerge = personmerge
    ctx.add_session_vars('personmerge')
    if config.debug:
        desc = persondupe.explain_dupe(ctx.locals._credentials.prefs,
                                       personmerge.person_a,
                                       personmerge.person_b)
        ctx.add_message('Similarity: %s' % desc)

def page_leave(ctx):
    try:
        likely = ctx.locals.likely
        personmerge = ctx.locals.personmerge
    except AttributeError:
        pass
    else:
        likely.set_cur_exclude(personmerge.status, personmerge.exclude_reason)
    ctx.del_session_vars('personmerge')
    ctx.locals.caseset = None

def page_display(ctx):
    ctx.run_template('mergeperson.html')

def page_process(ctx):
    if pageops.page_process(ctx):
        return
