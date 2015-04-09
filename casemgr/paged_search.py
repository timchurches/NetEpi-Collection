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

# Standard Lib
import time
try:
    set
except NameError:
    from sets import Set as set

# Application
from cocklebur import dbobj

class Pager(object):
    results_per_page = 10
    prev_pager = None

    def reset_page(self):
        self.go_page = None
        self.page = 1

    def result_count(self):
        # This must be overridden
        return 0

    def page_length(self):
        # Because CGI field merging will turn ints into strs.
        return int(self.results_per_page)

    def pages(self):
        results_per = self.page_length()
        return (self.result_count() + results_per - 1) / results_per

    def has_pages(self):
        return self.pages() > 1

    def cur_page(self):
        return self.page

    def page_jump(self):
        if self.go_page:
            for p in self.go_page:
                p = int(p[len('Page '):])
                if p != self.page and 1 <= p <= self.pages():
                    self.page = p
                    break
            self.go_page = None

    def has_prev(self):
        return self.page > 1

    def has_next(self):
        return self.page < self.pages()

    def prev(self):
        self.go_page = None
        if self.has_prev():
            self.page -= 1

    def next(self):
        self.go_page = None
        if self.has_next():
            self.page += 1

    def do(self, cmd, *args):
        # New-style dispatch, but can't handle page jumps?
        if cmd == 'prev':
            self.prev()
        elif cmd == 'next':
            self.next()
        elif cmd == 'orderby':
            self.set_order_by(*args)

    def page_process(self, ctx):
        # Old-style co-operative dispatch
        if ctx.req_equals('search_reset'):
            self.reset()
        elif ctx.req_equals('results_prev_page'):
            self.prev()
        elif ctx.req_equals('results_next_page'):
            self.next()
        else:
            self.page_jump()
            return False
        return True

    def page_list(self):
        return ['Page %s' % (i + 1) for i in range(self.pages())]


class PagerSelect(Pager):

    def __init__(self):
        self.selected = set()
        self.page_selected = []

    def _selected_to_page(self):
        self.page_selected = [i for i, key in enumerate(self.page_pkeys())
                              if key in self.selected]

    def _page_to_selected(self):
        page_keys = self.page_pkeys()
        self.selected.difference_update(page_keys)
        for idx in self.page_selected:
            self.selected.add(page_keys[int(idx)])

    def select(self, selected):
        self.selected = set(selected)
        self._selected_to_page()

    def do(self, cmd, *args):
        self._page_to_selected()
        if cmd == 'select_all':
            self.selected = set(self.pkeys)
        elif cmd == 'select_none':
            self.selected = set()
        else:
            Pager.do(self, cmd, *args)
        self._selected_to_page()

    def page_process(self, ctx):
        self._page_to_selected()
        Pager.page_process(self, ctx)
        self._selected_to_page()


class PagedSearch(Pager):

    results_per_page_options = [10, 25, 50, 100]

    def __init__(self, db, prefs, table, title=None, selected=[]):
        Pager.__init__(self)
        self.db = db
        self.prefs = prefs
        self.table = table
        self.title = title
        self.results_per_page = prefs.get('results_per_page')
        self.reset()

    def reset(self):
        self.new_search()

    def new_search(self):
        self.reset_page()
        self.search_time = 0
        self.page_time = 0
        self.pkeys = None
        self.error = ''
        self.empty = True

    def __len__(self):
        if self.pkeys is not None:
            return len(self.pkeys)

    def set_error(self, err):
        self.error = str(err)
        self.pkeys = None

    def fetch_pkeys(self, query):
        st = time.time()
        pkeys = []
        last = None
        for keys in query.fetchkeys():
            # Strip duplicate keys if they are consecutive
            if keys == last:
                continue
            pkeys.append(keys)
            last = keys
        self.empty = not pkeys
        if self.empty:
            self.set_error('Nothing found')
        self.pkeys = pkeys
        self.search_time = time.time() - st

    def result_count(self):
        if self.pkeys is None:
            return 0
        return len(self.pkeys)

    def page_pkeys(self):
        if self.pkeys is not None:
            page_len = self.page_length()
            start = (self.cur_page() - 1) * page_len
            end = start + page_len
            return self.pkeys[start:end]

    def page_rows(self):
        query = self.db.query(self.table)
        return query.fetchall_by_keys(self.page_pkeys())

    def result_page(self, *args):
        st = time.time() 
        rows = []
        if not self.error:
            rows = self.page_rows(*args)
        self.page_time = time.time() - st
        return rows


class SortablePagedSearch(PagedSearch):

    def __init__(self, db, prefs, query=None, title=None):
        if query is not None:
            self.query = query
        PagedSearch.__init__(self, db, prefs, None, title)
        assert self.query is not None
        self.table = self.query.table_desc.name
        self.order_by = self.query.order_by
        self.fetch_pkeys(self.query)

    def set_order_by(self, order_by):
        if order_by.endswith('_desc'):
            order_by = order_by[:-len('_desc')] + ' DESC'
        self.order_by = self.query.order_by = order_by
        self.reset()

    def result_count(self):
        if self.pkeys is None:
            self.fetch_pkeys(self.query)
        return PagedSearch.result_count(self)

    def page_pkeys(self):
        if self.order_by != self.query.order_by:
            self.query.order_by = self.order_by
            self.fetch_pkeys(self.query)
        elif self.pkeys is None:
            # Refresh
            self.fetch_pkeys(self.query)
        return PagedSearch.page_pkeys(self)

    def fetch_pkeys(self, query):
        try:
            PagedSearch.fetch_pkeys(self, query)
        except dbobj.DatabaseError, e:
            self.db.rollback()
            self.set_error(e)
            self.pkeys = []


def push_pager(ctx, pager):
    """
    We maintain a stack of pagers (implemented as a linked list), as the input
    names in the page templates are hard-coded (this is mainly a crutch for the
    page_select macro).
    """
    pager.prev_pager = getattr(ctx.locals, 'paged_search', None)
    ctx.locals.paged_search = pager
    if pager.prev_pager is None:
        ctx.add_session_vars('paged_search')

def pop_pager(ctx):
    paged_search = getattr(ctx.locals, 'paged_search', None)
    if paged_search is not None:
        ctx.locals.paged_search = paged_search.prev_pager
        if ctx.locals.paged_search is None:
            ctx.del_session_vars('paged_search')
