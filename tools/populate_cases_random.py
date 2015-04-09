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
import sys, os
import getpass
import random

sys.path.insert(0, os.path.abspath(os.path.join(sys.path[0],os.pardir)))
sys.path.insert(0, os.getcwd())
try:
    from casemgr import globals
except IOError, e:
    sys.exit('%s\nThis script must be run from the application cgi-bin directory' % e)
from casemgr import cases, credentials, syndrome
import config

def xform_date(date):
    if date:
        year, month, day = date[:4], date[4:6], date[6:]
        return '%s/%s/%s' % (day, month, year)

words=[w.strip() for w in open('/usr/share/dict/words')]

def random_phone():
    num = ''.join([random.choice('0123456789') for c in range(8)])
    return num[:4] + '-' + num[4:]

def random_person(person):
    person.surname = random.choice(words).capitalize()
    person.given_names = ' '.join([random.choice(words).capitalize()
                                   for i in range(random.randint(1,2))])
    person.dob = '%s/%s/%s' % (random.randint(1,28),
                               random.randint(1,12),
                               random.randint(1920,2003))
                    
    person.sex = random.choice(['M', 'F'])
    person.street_address = '%s %s %s' % (random.randint(1,100),
                                          random.choice(words).capitalize(),
                                          random.choice(['St', 'Lane', 'Rd', 'Close', 'Ave']))
    person.locality = random.choice(words).capitalize()
    person.home_phone = random_phone()
    person.work_phone = random_phone()
    person.state = random.choice(['NSW', 'NSW', 'NSW', 'NSW', 'NSW', 'NSW', 'Vic', 'QLD', 'ACT', 'WA', 'NT', 'SA'])

    person.postcode = '%s' % random.randint(2000, 2999)

def main(args):
    user = raw_input('%s Username: ' % (config.apptitle))
    passwd = getpass.getpass()
    cred = credentials.Credentials()
    cred.authenticate_user(globals.db, user, passwd)
    synd = [s for s in syndrome.syndromes if s.name == 'SARS'][0]
    for record in xrange(int(args[0])):
        case = cases.new_case(cred, synd.syndrome_id, None)
        random_person(case.person)
        case.update()
        globals.db.commit()

if __name__ == '__main__':
    ourname = os.path.basename(sys.argv[0])
    if len(sys.argv) != 2:
        sys.exit('Usage: %s <case_count>' % ourname)
    main(sys.argv[1:])

