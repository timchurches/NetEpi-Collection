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
import unittest
from mx.DateTime import DateTime

import testcommon

from casemgr import persondupe, persondupecfg


class NGramWrapper(persondupe.NGram):
    ngram_map = {}

    def __init__(self, *values):
        self.fields = []
        for i, v in enumerate(values):
            fn = 'field_%d' % i
            setattr(self, fn, v)
            self.fields.append(fn)
        persondupe.NGram.__init__(self, None, self)


class NGramTest(unittest.TestCase):
    def runTest(self):
        # Name matching
        a = NGramWrapper('Smith')
        b = NGramWrapper('Smithe')
        c = NGramWrapper('Smith', 'Smith')
        d = NGramWrapper('Jane', 'Smith')
        e = NGramWrapper('Jane', 'Clark')
        for ng in (a, b, c, d, e):
            ng.prescan()
        # Invalid to compare to self in current implementation
        # self.assertAlmostEqual(a.match(a), 1.00, 2)
        self.assertAlmostEqual(a.match(b), 0.73, 2)
        self.assertAlmostEqual(b.match(a), 0.73, 2)
        self.assertAlmostEqual(a.match(c), 1.00, 2)
        self.assertAlmostEqual(a.match(d), 0.71, 2)
        self.assertAlmostEqual(d.match(a), 0.71, 2)
        self.assertAlmostEqual(a.match(e), 0.00, 2)
        self.assertAlmostEqual(e.match(a), 0.00, 2)
        # Phone number matching?
        a = NGramWrapper('1234-5678')
        b = NGramWrapper('1234-5678', '1234-1234')
        c = NGramWrapper('1234-5678', '4321-0982')
        d = NGramWrapper('12312123', '4321-0982')
        for ng in (a, b, c, d):
            ng.prescan()
        self.assertAlmostEqual(a.match(b), 0.86, 2)
        self.assertAlmostEqual(a.match(c), 0.67, 2)
        self.assertAlmostEqual(a.match(d), 0.00, 2)

class Person:
    id = 0
    def __init__(self, surname, given_names, sex=None, DOB=None, DOB_prec=0,
                 street_address=None, locality=None, 
                 state=None, postcode=None, country=None,
                 alt_street_address=None, alt_locality=None, 
                 alt_state=None, alt_postcode=None, alt_country=None,
                 work_street_address=None, work_locality=None, 
                 work_state=None, work_postcode=None, work_country=None,
                 passport_number=None, passport_country=None,
                 passport_number_2=None, passport_country_2=None,
                 home_phone=None, work_phone=None,
                 mobile_phone=None, fax_phone=None,
                 e_mail=None, last_update=None):
        self.__dict__.update(vars())
        if self.DOB:
            self.DOB = DateTime(*[int(d) for d in self.DOB.split('-')])
        Person.id += 1
        self.person_id = self.id
        self.last_update = None


class MatchPersons(persondupe.MatchPersons):
    """
    We subclass so we can override methods that touch the db
    """
    test_records = [
        Person('Smith', 'John'),
        Person('Smithe', 'John'),
        Person('Jackson', 'John'),
        Person('John', 'Jackson'),
        Person('Jane', 'Doe'),
        Person('Doe', 'Jane', street_address='4/34 Smith St', DOB='1960-5-5'),
        Person('Jones', 'Jane', street_address='4/34 Smith St', DOB='1960-5-5'),
    ]
    
    def lock(self, db):
        pass

    def load(self, db, update_only):
        assert not update_only
        matchers = persondupe.get_matchers(persondupecfg.new_persondupecfg())
        for row in self.test_records:
            self.records.append(persondupe.Record(row, matchers))
        self.last_run = None


class PersonDupeTest(unittest.TestCase):
    def runTest(self):
        real_dupe_lock = persondupe.dupe_lock
        persondupe.dupe_lock = lambda a, b: None
        try:
            mp = MatchPersons(None)
        finally:
            persondupe.dupe_lock = real_dupe_lock
        likely = [(pair.low_person_id, pair.high_person_id) 
                   for pair in mp.dupes.sorted()]
        self.assertEqual(likely, [
            (6, 7),
            (3, 4),
            (5, 6),
            (1, 2),
        ])
        

def suite():
    suite = unittest.TestSuite()
    suite.addTest(NGramTest())
    suite.addTest(PersonDupeTest())
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
