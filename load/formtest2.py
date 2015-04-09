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
# Standard modules
import sys
import re
import csv
import time
import os
import gzip
import logging
import traceback
from logging import debug, info, warning, error, fatal
from optparse import OptionParser
from random import Random
from datetime import datetime, timedelta
import urllib2

# http://wwwsearch.sourceforge.net/ClientForm/
# http://wwwsearch.sourceforge.net/ClientCookie/
import ClientForm, ClientCookie

def_log_format = '%(asctime)s: %(levelname)s %(message)s'

def makephone(r):
    ph = str(r.randint(40000000,99999999))
    return ph[0:4] + '-' + ph[4:]

def xform_date(date):
    if date:
        year, month, day = date[:4], date[4:6], date[6:]
        return '%s/%s/%s' % (day, month, year)

def xform_person(record, form, r):
    form["case.case_row.local_case_id"] = record['localid']
    form["case.person.surname"] = record['surname']
    form["case.person.given_names"] = record['given_names']
    dob = xform_date(record['DOB'])
    if dob != None:
        form["case.person.DOB"] = dob
    sex = record['sex'].upper()
    if sex != "":
        form["case.person.sex"] = [sex,]
    form["case.person.home_phone"] = makephone(r)
    form["case.person.work_phone"] = makephone(r)
    form["case.person.street_address"] = record['street_address']
    form["case.person.locality"] = record['locality']
    state = record['state'].upper()
    if state != "":
        form["case.person.state"] = [state,]
    form["case.person.postcode"] = record['postcode']
    onset_dt = datetime.now() - timedelta(r.uniform(1,64))
    onset_ymd = str(onset_dt).split()[0].split('-')
    onset_hms = str(onset_dt).split()[1].split(":")
    form["case.case_row.onset_datetime"] = '%s/%s/%s %s:%s' % (onset_ymd[2], onset_ymd[1], onset_ymd[0], onset_hms[0], onset_hms[1])
    return form

def xform_contact(record, form, r):
    form["contact.person.surname"] = record['surname']
    form["contact.person.given_names"] = record['given_names']
    dob = xform_date(record['DOB'])
    if dob != None:
        form["contact.person.DOB"] = dob
    sex = record['sex'].upper()
    if sex != "":
        form["contact.person.sex"] = [sex,]
    form["contact.person.home_phone"] = makephone(r)
    form["contact.person.work_phone"] = makephone(r)
    form["contact.person.street_address"] = record['street_address'].title()
    form["contact.person.locality"] = record['locality'].upper()
    state = record['state'].upper()
    if state != "":
        form["contact.person.state"] = [state,]
    form["contact.person.postcode"] = record['postcode']
    form["contact.contact_row.contact_date"] = "21/08/2003 12:01"
    contact_dt = datetime.now() - timedelta(r.uniform(1,64))
    contact_ymd = str(contact_dt).split()[0].split('-')
    contact_hms = str(contact_dt).split()[1].split(":")
    form["contact.contact_row.contact_date"] = '%s/%s/%s %s:%s' % (contact_ymd[2], contact_ymd[1], contact_ymd[0], contact_hms[0], contact_hms[1])
    return form
    
def sars_travel(form, r):
    form["form_sars_travel_00000.country"] = 'China'
    form["form_sars_travel_00000.arrival_date"] = '21/08/2003'
    form["form_sars_travel_00000.arrival_flight"] = 'CN2304'
    form["form_sars_travel_00000.departure_date"] = '25/08/2003'
    form["form_sars_travel_00000.departure_flight"] = 'CN0121'
    form["form_sars_travel_00000.duration"] = '4'
    return form

def rtfu(r):
    return [r.choice(["True","False","Unknown"]),]

def rmfu(r):
    return r.choice(["M","F","U"])

def xform_contact_followup(form, r):
    f = str(form)
    # print f
    formname = f[f.index("form_sars_followup_"):].split(".")[0]
    form[formname + ".first_temperature"] = str(r.normalvariate(36.7,1.0))
    form[formname + ".second_temperature"] = str(r.normalvariate(36.7,1.0))
    form[formname + ".antipyretic_medication"] = rtfu(r)
    form[formname + ".malaise"] = rtfu(r)
    form[formname + ".chills"] = rtfu(r)
    form[formname + ".rigors"] = rtfu(r)
    form[formname + ".headache"] = rtfu(r)
    form[formname + ".cough"] = rtfu(r)
    form[formname + ".diarrhoea"] = rtfu(r)
    form[formname + ".toilet_isolation"] = rtfu(r)
    form[formname + ".breathing_difficulty"] = rtfu(r)
    form[formname + ".other_household_symptoms"] = rtfu(r)
    form[formname + ".away_from_home"] = rtfu(r)
    form[formname + ".compliance_issues"] = rtfu(r)
    form[formname + ".other_comments"] = "The quality of mercy is not strained..."
    return form
    
class Person:
    def __init__(self, row, r):
        self.sex = row[1].strip()
        self.given_names = row[2].strip()
        self.surname = row[3].strip()
        self.street_address = row[4].strip() + ' ' + row[5].strip()
        self.locality = row[7].strip()
        self.postcode = row[8].strip()
        self.state = row[9].strip()
        self.DOB = row[10].strip()
        self.localid = row[11].strip()
        
    def __getitem__(self, i):
        return getattr(self, i)
        
class PersonsSource:
    """
    Read CSV files containing dummy person details, return them
    one person at a time.
    """
    def __init__(self, files):
        self.files = files
        self.files_iter = iter(self.files)
        self.row_iter = None
        self.r = Random()

    def __iter__(self):
        return self

    def next(self):
        while 1:
            if self.row_iter is None:
                filename = self.files_iter.next()
                if filename.endswith('.gz'):
                    f = gzip.GzipFile(filename)
                else:
                    f = open(filename)
                self.row_iter = csv.reader(f)
                self.row_iter.next()            # Eat header
            try:
                row = Person(self.row_iter.next(),self.r)
                # print row.sex # debug
                if row.surname:
                    return row
            except StopIteration:
                self.row_iter = None

class ResponseRecorder:
    def __init__(self, response):
        self._response = response
        self._data = []

    def read(self, *size):
        buf = self._response.read(*size)
        self._data.append(buf)
        return buf

    def get_buffer(self):
        return ''.join(self._data)

    def __getattr__(self, a):
        if a.startswith('_'):
            raise AttributeError(a)
        return getattr(self._response, a)

class InteractError(Exception): pass

class FormInteract:
    time_history = 10
    def __init__(self, url, debug = False, use_lynx=True):
        self.url = url
        self.default_form = None
        self.forms = None
        self.count = 0
        self.times = []
        self.debug = debug
        self.use_lynx = use_lynx

    def get(self):
        self._get(self.url)

    def _get(self, req):
        starttime = time.time()
        try:
            self.response = ResponseRecorder(ClientCookie.urlopen(req))
        except urllib2.HTTPError, e:
            # urllib2.HTTPError instances are also Response objects
            self.response = ResponseRecorder(e)
            self.response.read()
            try:
                url = req.get_full_url()
            except AttributeError:
                url = req
            raise InteractError('%s: %s' % (url, e))
        self.forms = ClientForm.ParseResponse(self.response)
        self.default_form = 0
        interact_time = time.time() - starttime
        self.times = [interact_time] + self.times[:self.time_history - 1]
#        info(' interaction took %.3fs' % interact_time)         # XXX
        self.count += 1

    def av_time(self):
        return sum(self.times) / len(self.times)

    def read(self):
        return self.response

    def set_current_form(self, n):
        assert n < len(self.forms)
        self.default_form = n

    def current_form(self):
        return self.forms[self.default_form]

    """
    def __setitem__(self, n, v):
        self.current_form()[n] = v

    def __getitem__(self, n):
        return self.current_form()[n]

    def set(n, v):
        self.current_form().set(n, v)
    """
    def __contains__(self, n):
        try:
            self[n]
        except AttributeError:
            return False
        else:
            return True

    def __getattr__(self, a):
        if self.forms:
            return getattr(self.current_form(), a)
        else:
            raise AttributeError(a)

    def __setitem__(self, i, v):
        try:
            self.current_form()[i] = v
        except ClientForm.ControlNotFoundError, e:
            raise InteractError(str(e))

    def click(self, button_name):
        try:
            self._get(self.current_form().click(button_name))
        except ClientForm.ControlNotFoundError, e:
            raise InteractError(str(e))

    def expect(self, regexp):
        response_text = self.response.get_buffer()
        if not re.search(regexp, response_text, re.IGNORECASE + re.MULTILINE):
            raise InteractError('Expected: %r' % regexp)

    def dump_response(self):
        response_text = self.response.get_buffer()
        if self.use_lynx:
            try:
                 w = os.popen('/usr/bin/lynx -stdin -dump', 'w')
                 w.write(response_text)
                 w.close()
                 return
            except:
                pass
        info('Last response:\n' + response_text)

def random_sleep(r, interval):
    if interval:
        time.sleep(r.gauss(interval, interval / 6))

def main():
    optparse = OptionParser(usage='Usage: %prog --username=<username> --password=<password> [options] <persons.csv> ...')
    optparse.add_option('-C', '--no-contacts', 
                        dest='no_contacts', action='store_true',
                        help='if given, only create cases, no contacts')
    optparse.add_option('--sars-travel', 
                        dest='sars_travel', action='store_true',
                        help='if given, fill in a number of sars travel forms')
    optparse.add_option('--use_lynx', 
                        dest='use_lynx', action='store_true',
                        help='if given, program will use /usr/bin/lynx to extract clean HTML')
    optparse.add_option('-F', '--log-format', dest='log_format',
                        default=def_log_format,
                        help='log format string (default: %s)' % def_log_format)
    optparse.add_option('-l', '--log', dest='log', action='append',
                        help='specify log targets')
    optparse.add_option('-q', '--quiet', dest='quiet', action='store_true',
                        help='disable normal output')
    optparse.add_option('--retry', dest='retry', action='store_true',
                        help='retry after errors')
    optparse.add_option('-U', '--url', dest='url',
                        default='http://127.0.0.1/cgi-bin/casemgr/app.py',
                        help='specify application URL [default: URL]')
    optparse.add_option('-s', '--sleep', dest='sleep', type='float',
                        help='sleep SLEEP seconds between interactions')
    optparse.add_option('--skip', dest='skip', type='int',
                        help='skip SKIP rows into the person data')
    optparse.add_option('-D', '--debug', dest='debug', action='store_true',
                        help='enable debugging')
    optparse.add_option('-u', '--username', dest='username',default = "",
                        help='username to use to login to NetEpi Collection')
    optparse.add_option('-p', '--password', dest='password', default="",
                        help='password to use to login to NetEpi Collection')

    options, args = optparse.parse_args()
    if not args:
        optparse.error('Must specify at least one person.csv file')

    if len(options.username) == 0 or len(options.password) == 0:
        optparse.error('Must specify username= and password= paramaters')

    root_logger = logging.getLogger()
    if options.debug:
        root_logger.setLevel(logging.DEBUG)
    else:
        root_logger.setLevel(logging.INFO)
    formatter = logging.Formatter(options.log_format)
    if not options.quiet:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
    if options.log:
        for log in options.log:
            handler = logging.FileHandler(log)
            handler.setFormatter(formatter)
            root_logger.addHandler(handler)

    r = Random()
    total_count = 0
    restart_count = 0
    persons = PersonsSource(args)
    if options.skip:
        n = 0
        for n, record in enumerate(persons):
            if n + 1 == options.skip:
                break
        else:
            sys.exit('Can\'t skip %d rows - only %d rows of persons' %\
                     (options.skip, n))
    while 1:
        interact = FormInteract(options.url, debug = options.debug, use_lynx = options.use_lynx)
        try:
            interact.get()
            interact["username"] = options.username
            interact["password"] = options.password
            interact.click('login')
            interact.expect('Welcome')
            info('Logged in')

            for case_count in xrange(1,100000):
                i_count = interact.count
                record = persons.next()
                case_start = time.time()
                interact.click('new:2')
                interact.click('do_search')
                interact.click('new_case')
                xform_person(record, interact, r)
                interact.click('update')
                total_count += 1
                info("add case took %.2fs, %d/%d(%d) cases" % \
                     ((time.time() - case_start), case_count, 
                      total_count, restart_count))
                random_sleep(r, options.sleep)
                if options.sars_travel:
                    for sars_travel_count in range(1, r.randint(2, 5)):
                        interact.click('new:sars_travel')
                        form_start = time.time()
                        sars_travel(interact, r)
                        interact.click('form_submit')
                        info('  %5d - added a form, took %.2f seconds' % \
                            (sars_travel_count, time.time() - form_start))
                # Unable to get contacts creation working reliably - bug in FormClient??
                # It works fine interactively and with Selenium!!!
                if False:
                # if not options.no_contacts:
                    interact.click('contacts')
                    # for contact_count in range(1, r.randint(2,5)):
                    for contact_count in range(1,2):
                        contact_start = time.time()
                        interact.click('add_contact')
                        interact.click('do_search')
                        interact.click('new_contact')
                        record = persons.next()
                        xform_contact(record, interact, r)
                        interact.click('update')
                        interact.click('back')
                        info('  %5d - added a contact, took %.2f seconds' % \
                            (contact_count, time.time() - contact_start))
                        random_sleep(r, options.sleep)
                interact.click('action')
                info('    total time %.2f, %d/%d interactions, %.2fs av' % \
                     ((time.time() - case_start), interact.count - i_count, 
                      interact.count, interact.av_time()))
        except (KeyboardInterrupt, StopIteration):
            sys.exit(0)
        except:
            error('\n'.join(traceback.format_exception(*sys.exc_info())))
            interact.dump_response()
            ClientCookie.install_opener(None)   # Should discard CookieJar
        if not options.retry:
            break
        restart_count += 1
        info('Exception thrown (%d times so far), sleeping 20 seconds' % restart_count)
        time.sleep(20)
        
            
if __name__ == '__main__':
    main()

"""
# Not currently used
for t in range(10):
    form = do_click(form,"new")[0]
    f = str(form)
    formname = f[f.index("form_sars_followup_"):].split(".")[0]
    form[formname + ".first_temperature"] = "37.3"
    form[formname + ".second_temperature"] = "37.8"
    form[formname + ".antipyretic_medication"] = ["True",]
    form[formname + ".malaise"] = ["True",]
    form[formname + ".chills"] = ["False",]
    form[formname + ".rigors"] = ["Unknown",]
    form[formname + ".headache"] = ["False",]
    form[formname + ".cough"] = ["True",]
    form[formname + ".diarrhoea"] = ["True",]
    form[formname + ".toilet_isolation"] = ["False",]
    form[formname + ".breathing_difficulty"] = ["Unknown",]
    form[formname + ".other_household_symptoms"] = ["True",]
    form[formname + ".away_from_home"] = ["None",]
    form[formname + ".compliance_issues"] = ["False",]
    form[formname + ".other_comments"] = "The quality of mercy is not strained..."
    # print form
    form = do_click(form,"form_submit")[0]
# print form

"""
