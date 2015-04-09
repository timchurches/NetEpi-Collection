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

from time import time
from casemgr import globals, demogfields, paged_search, persondupe, personmerge
from pages import page_common
import config


class LikelyMatches(paged_search.Pager):

    def __init__(self, likely, title):
        self.title = title
        self.show_excluded = False
        self.current = None
        self.full_likely = likely
        self.last_run = persondupe.last_run(globals.db)
        self.new_search()

    def new_search(self):
        self.reset_page()
        self.filter_likely()

    def filter_likely(self):
        included = [m for m in self.full_likely 
                    if m.status != persondupe.STATUS_EXCLUDED]
        self.exclude_count = len(self.full_likely) - len(included)
        if self.show_excluded:
            self.likely = self.full_likely
        else:
            self.likely = included

    def set_show_excluded(self, show_excluded):
        self.show_excluded = show_excluded
        self.page = 1

    def result_count(self):
        return len(self.likely)

    def result_page(self):
        st = time()
        self.filter_likely()
        page_length = self.page_length()
        start = (self.page - 1) * page_length
        end = min(start + page_length, len(self.likely))
        persons = globals.db.table_dict('persons')
        for pair in self.likely[start:end]:
            persons.want(pair.low_person_id)
            persons.want(pair.high_person_id)
        persons.preload()
        page = []
        for i in range(start, end):
            pair = self.likely[i]
            try:
                person_a = persons[pair.low_person_id]
                person_b = persons[pair.high_person_id] 
            except KeyError:
                continue        # Possibly someone else merging.
            page.append((i, pair, person_a, person_b))
        self.page_time = time() - st
        return page

    def page_offs(self, index):
        return self.likely[(self.page - 1) * self.page_length() + index]

    def set_cur(self, index):
        self.current = self.likely[index]
        return self.current

    def set_cur_exclude(self, status, exclude_reason):
        if self.current is not None:
            self.current.status = status
            self.current.exclude_reason = exclude_reason

    def stats(self):
        return ''


class PageOps(page_common.PageOpsBase):
    def do_view(self, ctx, index):
        matchpair = ctx.locals.likely.set_cur(int(index))
        merge = personmerge.Merge(matchpair.low_person_id, 
                                  matchpair.high_person_id)
        ctx.push_page('mergeperson', merge)

    def do_excluded(self, ctx, op):
        ctx.locals.likely.set_show_excluded(op == 'show')

pageops = PageOps()


def page_enter(ctx, dp, title):
    ctx.locals.likely = LikelyMatches(dp, title)
    paged_search.push_pager(ctx, ctx.locals.likely)
    ctx.add_session_vars('likely')

def page_leave(ctx):
    paged_search.pop_pager(ctx)
    ctx.del_session_vars('likely')

show_fields = (
    'surname', 'given_names', 'sex', 'DOB', 
    'street_address', 'locality', 'state',
)

def page_display(ctx):
    ctx.locals.page = ctx.locals.likely.result_page()
    fields = demogfields.get_demog_fields(globals.db, None)
    ctx.locals.fields = [f for f in fields.context_fields('result')
                         if f.name in show_fields]
    if not ctx.locals.likely.full_likely:
        ctx.add_error('No duplicate matches found')
    elif not ctx.locals.page:
        ctx.add_message('No duplicate matches found (%d match(es) excluded)' %
                        ctx.locals.likely.exclude_count)
    ctx.run_template('dupepersons.html')

def page_process(ctx):
    if pageops.page_process(ctx):
        return
    elif ctx.locals.likely.page_process(ctx):
        return
