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

# Old systems may have form instance tables without an ON DELETE CASCADE
# constraint on the summary_id foreign key. These can be identified with:
#
#   SELECT l.relname 
#       FROM pg_constraint 
#       JOIN pg_class AS l ON (l.oid = conrelid)
#       JOIN pg_class AS f ON (f.oid = confrelid)
#       WHERE l.relname ~ 'form_.*_[0-9]{5}' and confdeltype='a';
#

import config
from casemgr import globals

class DropSyndromeError(globals.Error): pass

Error = DropSyndromeError

class ClearSyndrome:
    def __init__(self, syndrome_id):
        self.syndrome_id = syndrome_id
        self.case_count = None
        self.form_count = None
        self.task_count = None
        self.errors = []
        self.acknowledge = None

    def update_counts(self):
        self.errors = []

        # XXX CONTACT - warn about contacts here?

        query = globals.db.query('cases')
        query.where('syndrome_id = %s', self.syndrome_id)
        self.case_count = query.aggregate('count(*)')

        query = globals.db.query('case_form_summary')
        query.join('JOIN cases USING (case_id)')
        query.where('cases.syndrome_id = %s', self.syndrome_id)
        self.form_count = query.aggregate('count(*)')

        query = globals.db.query('tasks')
        query.join('JOIN cases USING (case_id)')
        query.where('cases.syndrome_id = %s', self.syndrome_id)
        self.task_count = query.aggregate('count(*)')

    def delete(self, last_case_count, last_form_count):
        if self.acknowledge != 'ACK':
            raise Error('Warning not acknowledged!')
        self.update_counts()
        if (self.case_count != last_case_count or 
            self.form_count != last_form_count):
            raise Error('Could not delete %s - case or form count changed!' %
                        config.syndrome_label)
        query = globals.db.query('tasks')
        sub = query.in_select('case_id', 'cases')
        sub.where('syndrome_id = %s', self.syndrome_id)
        query.delete()

        query = globals.db.query('cases')
        query.where('syndrome_id = %s', self.syndrome_id)
        query.delete()

        query = globals.db.query('persons')
        sub = query.in_select('person_id', 'persons')
        sub.join('LEFT JOIN cases USING (person_id)')
        sub.where('case_id IS null')
        query.delete()


class DropSyndrome(ClearSyndrome):
    def update_counts(self):
        ClearSyndrome.update_counts(self)

        query = globals.db.query('syndrome_types', for_update=True)
        query.where('syndrome_id = %s', self.syndrome_id)
        syndrome = query.fetchone()
        if not syndrome:
            raise Error('%s not found' % (config.syndrome_label))
        if syndrome.enabled:
            self.errors.append('%s is still enabled' % (config.syndrome_label))

    def delete(self, last_case_count, last_form_count):
        ClearSyndrome.delete(self, last_case_count, last_form_count)
        query = globals.db.query('syndrome_types')
        query.where('syndrome_id = %s', self.syndrome_id)
        query.delete()
