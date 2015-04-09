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


import sys, os, datetime
from random import Random

sys.exit('''\
NOTE:
This script is currently non-functional due to changes in the application
internal API's. See populate_cases_random.py for hints on how to return
this script to functionality.''')
ddot = os.pardir
sys.path.insert(0, os.path.abspath(os.path.join(sys.path[0],ddot,ddot,'tools')))
import csv_load
sys.path.insert(0, '/var/www/cgi-bin/collection')
from casemgr import cases, credentials, syndrome, contact
from casemgr.schema import schema


def xform_date(date):
    if date:
        year, month, day = date[:4], date[4:6], date[6:]
        return '%s/%s/%s' % (day, month, year)

def makephone(r):
    ph = str(r.randint(40000000,99999999))
    return ph[0:4] + '-' + ph[4:]

def xform_person(record, person,r):
    person.surname = record.surname
    person.given_names = record.given_name
    person.dob = xform_date(record.date_of_birth)
    person.sex = record.sex.upper()
    person.street_address = (record.street_number + ' ' + 
                             record.address_1.title()).strip()
    person.locality = record.suburb.upper()
    person.state = record.state.lower()
    person.postcode = record.postcode
    person.home_phone = makephone(r)
    person.work_phone = makephone(r)

def main(args):
    r = Random()
    db = schema.define_db()
    cred = credentials.Credentials()
    cred.set_user(db, 'andrewm')
    cred.get_units(db)
    cred.set_unit(db, 0)
    cred.authenticate_user(db, 'andrewm')
    synd = [s for s in syndrome.get_syndromes(db, cred) if s.name == 'SARS'][0]
    for filename in args:
        f = open(filename)
        testrecs = []
        for rec in csv_load.load(f):
            testrecs.append(rec)
        f.close()
        testrecs_len = len(testrecs)
        try:
            count = 0
            while count < testrecs_len:
                record = testrecs[count]
                count += 1
                print count
                case = cases.new_case(db, cred, synd)
                d = str(datetime.datetime.now()).split()[0].split("-")
                t = str(datetime.datetime.now()).split()[1].split(":")[:-1]
                case.case_row.onset_datetime = d[2] + "/" + d[1] + "/" + d[0] + " " + t[0] + ":" + t[1]
                xform_person(record, case.person_row,r)
                case.update(db)
                for i in range(Random().choice([0,1,2,3,4,5,6,7,8910,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25])):
                    mycontacts = contact.Contacts(db,case)
                    mycontact = mycontacts.new_contact(db)
                    record = testrecs[count]
                    count += 1
                    xform_person(record,mycontact.person_row,r)
                    d = str(datetime.datetime.now()).split()[0].split("-")
                    t = str(datetime.datetime.now()).split()[1].split(":")[:-1]
                    mycontact.contact_row.contact_date = d[2] + "/" + d[1] + "/" + d[0] + " " + t[0] + ":" + t[1]
                    """
                    fu = contact.Followup(case,mycontact,db.new_row('followup_summary'))
                    fu.get_form_ui(db)
                    fu.followup_row = db.new_row(fu.form_ui.table)
                    fu.followup_row.contact_id = mycontact.contact_row.contact_id
                    fu.followuo_row.contact_date = ':'.join(str(datetime.datetime.now() - datetime.timedelta(2)).split(':')[:-1])
                    fu.summary.contact_id = mycontact.contact_row.contact_id
                    # self.summary.summary = ', '.join(summary).capitalize()
                    fu.summary.form_date = fu.followup_row.form_date
                    fu.summary.db_update()
                    fu.followup_row.followup_summary_id =fu.summary.followup_summary_id
                    fu.followup_row.db_update()
                    """
                    mycontact.update()
                db.commit()
        finally:
            f.close()

if __name__ == '__main__':
    main(sys.argv[1:])
