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
import re

from mx import DateTime

double_nl_re = re.compile('\n\n', re.MULTILINE)
nl_re = re.compile('\n', re.MULTILINE)


class Bulletin:
    def __init__(self, bulletin_row):
        self.bulletin_id = bulletin_row.bulletin_id
        self.post_date = bulletin_row.post_date
        self.expiry_date = bulletin_row.expiry_date
        self.title = bulletin_row.title
        self.synopsis = bulletin_row.synopsis
        self.detail = bulletin_row.detail

class Bulletins:
    def __init__(self, db, credentials):
        self.db = db
        self.credentials = credentials
        self.bulletins = None

    def __getstate__(self):
        return self.db, self.credentials

    def __setstate__(self, state):
        self.db, self.credentials = state
        self.bulletins = None

    def load(self, hide_time=None):
        query = self.db.query('bulletins', 
                            distinct = True, order_by = 'post_date DESC')
        if 'ACCESSALL' not in self.credentials.rights:
            query.join('JOIN group_bulletins USING (bulletin_id)')
            query.join('JOIN unit_groups USING (group_id)')
            query.where('unit_groups.unit_id = %s', 
                        self.credentials.unit.unit_id)
        if hide_time:
            query.where('bulletins.post_date > %s', 
                        DateTime.DateTimeFromTicks(hide_time))
        sub = query.sub_expr('OR')
        sub.where('bulletins.post_date is null')
        sub.where('bulletins.post_date <= CURRENT_TIMESTAMP')
        sub = query.sub_expr('OR')
        sub.where('bulletins.expiry_date is null')
        sub.where('bulletins.expiry_date > CURRENT_TIMESTAMP')
        self.bulletins = query.fetchall()

    def get_bulletins(self, hide_time):
        if self.bulletins is None:
            self.load(hide_time)
        return self.bulletins

    def get_bulletin(self, bulletin_id):
        query = self.db.query('bulletins')
        query.where('bulletin_id = %s', bulletin_id)
        return Bulletin(query.fetchone())

