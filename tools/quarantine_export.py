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

"""
Quick and dirty script to extract persons currently in quarantine
in NSW NetEpi Collection during swine flu response of 2009
"""

import sys
import csv
import ocpgdb
from mx import DateTime

order_by = 'surname', 'given_names', 'id'

now = DateTime.now()


def tablename(db, formname):
    curs = db.cursor()
    curs.execute('select cur_version from forms where label = %s', [formname])
    row = curs.fetchone()
    assert row is not None
    return 'form_%s_%05d' % (formname, row[0])


def age(dob):
    if not dob:
        return ''
    age = (now - dob).days
    if not age or age < 0:
        return ''
    if round(age) == 1:
        return '%.0f day' % age
    if age < 10:
        return '%.0f days' % age
    if age < 90:
        return '%.0f weeks' % (age / 7)
    years = age / 365.25
    if years < 1:
        return '%.0f months' % (age / 30.5)
    if years < 2:
        return '%.0f year' % years
    return '%.0f years' % years


def duration(v):
    if not v:
        return ''
    days = (now - v).days
    if days < 0:
        return ''
    return '%.0f days' % days


class Record:

    cols = (
        'id', 'surname', 'given_names', 'dob', 'age', 'sex', 'interpreter_req', 
        'start_date', 'duration',
        'home_phone', 'work_phone', 'mobile_phone',
        'e_mail', 
        'street_address', 'locality', 'state', 'postcode', 'country',
        'alt_street_address', 'alt_locality', 'alt_state', 'alt_postcode', 'alt_country',
        'passport_number', 'passport_country',
        'passport_number_2', 'passport_country_2',
    )

    def __init__(self, cols, row):
        for col, value in zip(cols, row):
            if isinstance(value, str):
                value = value.strip()
            setattr(self, col, value)
        self.age = age(self.dob)
        self.duration = duration(self.start_date)
        if self.dob_is_approx:
            self.dob = ''
        for col in ('dob', 'start_date'):
            value = getattr(self, col)
            if value:
                setattr(self, col, value.strftime('%Y-%m-%d'))

    def values(self):
        return [getattr(self, col) for col in self.cols]


class Query:

    demog_cols = (
        'case_id', 'surname', 'given_names', 'dob', 'dob_is_approx',
        'sex', 'interpreter_req', 
        'home_phone', 'work_phone', 'mobile_phone',
        'e_mail', 
        'street_address', 'locality', 'state', 'postcode', 'country',
        'alt_street_address', 'alt_locality', 'alt_state', 'alt_postcode', 'alt_country',
        'passport_number', 'passport_country',
        'passport_number_2', 'passport_country_2',
    )

    def query(self, db):
        table = tablename(db, self.form)
        cols = ','.join(('person_id', self.start_col) + self.demog_cols)
        colmap = {'case_id': 'id', self.start_col: 'start_date'}
        query = '''\
select %s
    from persons
    join cases using (person_id)
    join case_form_summary using (case_id)
    join %s using (summary_id)
    where not deleted and %s = 'True' and %s is null
    ''' % (cols, table, self.in_quar_col, self.finished_col)
        curs = db.cursor()
        curs.execute(query)
        cols = [colmap.get(d[0], d[0]) for d in curs.description]
        while True:
            rows = curs.fetchmany(200)
            if not rows:
                break
            for row in rows:
                yield Record(cols, row)


class CaseQuery(Query):
    form = 'swineflu'
    in_quar_col = 'home_isolation'
    start_col = 'home_isolation_start'
    finished_col = 'home_isolation_finished'


class ContactQuery(Query):
    form = 'sf_contact'
    in_quar_col = 'quarantined'
    start_col = 'quarantine_start'
    finished_col = 'quarantine_finished'


class Records(dict):

    def add(self, record):
        self[record.person_id] = record

    def sorted(self):
        dsu = [([getattr(r, c) for c in order_by], r) for r in self.itervalues()]
        dsu.sort()
        return [p[1] for p in dsu]


def main(dbname):
    db = ocpgdb.connect(database=dbname, use_mx_datetime=True)
    persons = Records()
    for row in ContactQuery().query(db):
        persons.add(row)
    for row in CaseQuery().query(db):
        persons.add(row)

    writer = csv.writer(sys.stdout)
    writer.writerow(Record.cols)
    for record in persons.sorted():
        writer.writerow(record.values())


def usage():
    sys.exit('Usage: %s <database>' % sys.argv[0])

if __name__ == '__main__':
    if len(sys.argv) != 2:
        usage()
    main(*sys.argv[1:])
