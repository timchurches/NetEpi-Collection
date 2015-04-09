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

# Standard Python Libs
import sys
import time
import cPickle

# Application modules
import config
from cocklebur import dbobj, datetime


class Preferences:
    # Batch fetch user prefs on creation, save changed prefs on command.
    commit_delay = 10
    debug = False
    n_recent = 16

    defaults = {
        'bulletin_time': None,
        'contact_viz': None,
        'current_unit': None,
        'date_style': config.date_style,
        'font_size': '10pt',
        'jscalendar': True,
        'nobble_back_button': config.nobble_back_button,
        'persons_per_page': 10,
        'persons_order': None,
        'phonetic_search': True,
        'results_per_page': 25,
        'ts_params': None,
        'recent_cases': None,
    }

    def __init__(self, user_id, preferences):
        self.user_id = user_id
        self.need_commit = False
        self.commit_time = time.time()
        self.preferences = {}
        self.lost_reason = None
        if preferences:
            try:
                self.preferences = cPickle.loads(str(preferences))
            except Exception, e:
                self.lost_reason = str(e)
        self.apply()

    def reset_all(self):
        self.preferences = {}
        self.need_commit = True

    def reset(self, name):
        try:
            del self.preferences[name]
            self.need_commit = True
        except KeyError:
            pass

    def set(self, name, value):
        old_value = self.preferences.get(name)
        if self.debug:
            print >> sys.stderr, 'PREFS set %s, changed %s, old %r, value %r' %\
                (name, old_value != value, old_value, value)
        if old_value != value:
            if name == 'date_style':
                datetime.set_date_style(value)
            if value == self.defaults.get(name):
                self.reset(name)
            else:
                self.preferences[name] = value
            self.need_commit = True

    def set_from_str(self, name, value):
        default_type = type(self.defaults[name])
        if default_type is bool:
            value = (value == 'True')
        else:
            value = default_type(value)
        self.set(name, value)

    def get(self, name, default=None):
        if default is None:
            default = self.defaults.get(name)
        return self.preferences.get(name, default)

    def set_recent_case(self, case_id, label):
        recent_cases = self.preferences.get('recent_cases')
        if recent_cases is None:
            recent_cases = [(case_id, label)]
        else:
            recent_cases = [(i, l) for i, l in recent_cases if i != case_id]
            del recent_cases[self.n_recent-1:]
            recent_cases.insert(0, (case_id, label))
        self.preferences['recent_cases'] = recent_cases
        self.need_commit = True

    def get_recent_cases(self):
        return list(self.preferences.get('recent_cases', []))

    def apply(self):
        # Some preferences effect libraries
        datetime.set_date_style(self.get('date_style'))

    def commit(self, db, immediate=False):
        self.apply()
        now = time.time()
        if self.debug:
            print >> sys.stderr, "PREFS commit, immediate %s, need_commit %s, when %s" % (immediate, self.need_commit, (now - (self.commit_time + self.commit_delay)))
        if (self.need_commit and 
            (immediate or self.commit_time + self.commit_delay < now)):
            if self.preferences:
                data = dbobj.Binary(cPickle.dumps(self.preferences))
            else:
                data = None
            try:
                curs = db.cursor()
                try:
                    dbobj.execute(curs, 'UPDATE users SET preferences=%s'
                                        ' WHERE user_id = %s',
                                        (data, self.user_id))
                finally:
                    curs.close()
            except dbobj.DatabaseError:
                db.rollback()
                raise
            else:
                db.commit()
                self.commit_time = now
                self.need_commit = False
