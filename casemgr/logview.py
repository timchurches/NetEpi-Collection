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

try:
    set
except NameError:
    from sets import Set as set

from cocklebur import dbobj

from casemgr import globals, paged_search, unituser


class LogColumns:
    def __init__(self, name, label):
        self.name = name
        self.label = label
        self.wide = (self.name == 'event_type')

    def pretty_row(self, row):
        value = getattr(row, self.name)
        if self.label == 'Date':
            return value.date()
        elif self.label == 'Time':
            return value.time()
        elif self.label == 'User':
            return row.username
        else:
            return value


class LogView(paged_search.SortablePagedSearch):
    table = 'user_log'

    def __init__(self, prefs, title, 
                 user_id=None, case_id=None):
        query = globals.db.query(self.table, order_by='event_timestamp')
        if user_id is not None:
            query.where('user_id = %s', user_id)
        if case_id is not None:
            query.where('case_id = %s', case_id)
        paged_search.SortablePagedSearch.__init__(self, globals.db, prefs, 
                                                  title=title, query=query)

    def cols(self):
        return [LogColumns(*c) for c in self.headers]

    def ncols(self):
        return len(self.headers)


class LogViewWithUser(LogView):

    def page_rows(self):
        rows = paged_search.SortablePagedSearch.page_rows(self)
        unituser.users.fetch(*[log.user_id for log in rows])
        for row in rows:
            row.username = unituser.users[row.user_id].username
        return rows


class SystemLogView(LogViewWithUser):
    table = 'admin_log'
    headers = [
        ('event_timestamp', 'Date'),
        ('event_timestamp', 'Time'),
        ('user_id', 'User'),
        ('remote_addr', 'Remote IP'),
        ('forwarded_addr', 'Forwarded IP'),
        ('event_type', 'Event'),
    ]


class AdminLogView(LogView):
    headers = [
        ('event_timestamp', 'Date'),
        ('event_timestamp', 'Time'),
        ('case_id', 'Case ID'),
        ('remote_addr', 'Remote IP'),
        ('forwarded_addr', 'Forwarded IP'),
        ('event_type', 'Event'),
    ]


class UserLogView(LogView):
    headers = [
        ('event_timestamp', 'Date'),
        ('event_timestamp', 'Time'),
        ('case_id', 'Case ID'),
        ('event_type', 'Event'),
    ]


class CaseLogView(LogViewWithUser):
    headers = [
        ('event_timestamp', 'Date'),
        ('event_timestamp', 'Time'),
        ('user_id', 'User'),
        ('case_id', 'Case ID'),
        ('event_type', 'Event'),
    ]
