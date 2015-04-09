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

from mx import DateTime

from cocklebur import agelib

from tests import testcommon

class AgeTestCase(unittest.TestCase):
    
    def test_parse_age(self):
        self.assertRaises(agelib.Error, agelib.Age.parse, '')
        self.assertRaises(agelib.Error, agelib.Age.parse, 'x')
        self.assertRaises(agelib.Error, agelib.Age.parse, 'x/y')
        self.assertRaises(agelib.Error, agelib.Age.parse, '1/y')
        self.assertRaises(agelib.Error, agelib.Age.parse, '1/1')
        self.assertRaises(agelib.Error, agelib.Age.parse, '1x')
        self.assertRaises(agelib.Error, agelib.Age.parse, '8/24')
        self.assertRaises(agelib.Error, agelib.Age.parse, '43/60')
        self.assertRaises(agelib.Error, agelib.Age.parse, 'years')
        self.assertRaises(agelib.Error, agelib.Age.parse, '1 fortnight')
        self.assertRaises(agelib.Error, agelib.Age.parse, '140')
        self.assertRaises(agelib.Error, agelib.Age.parse, '4/12/24')
        self.assertEqual(agelib.Age.parse('4/12'), (4, 'm'))
        self.assertEqual(agelib.Age.parse('3/52'), (3, 'w'))
        self.assertEqual(agelib.Age.parse('5/7'), (5, 'd'))
        self.assertEqual(agelib.Age.parse('6'), (6, 'y'))
        self.assertEqual(agelib.Age.parse('41'), (41, 'y'))
        self.assertEqual(agelib.Age.parse('6y'), (6, 'y'))
        self.assertEqual(agelib.Age.parse('6 years'), (6, 'y'))
        self.assertEqual(agelib.Age.parse('3w'), (3, 'w'))
        self.assertEqual(agelib.Age.parse('3 weeks'), (3, 'w'))
        self.assertEqual(agelib.Age.parse('4m'), (4, 'm'))
        self.assertEqual(agelib.Age.parse('4 Months'), (4, 'm'))
        self.assertEqual(agelib.Age.parse('5d'), (5, 'd'))
        self.assertEqual(agelib.Age.parse('5days'), (5, 'd'))

    def test_agestr(self):
        dt = DateTime.DateTime
        now = dt(2010,7,16,13,52,38)
        self.assertEqual(agelib.agestr(None, now), None)
        self.assertEqual(agelib.agestr('', now), None)
        self.assertEqual(agelib.agestr(dt(2010,7,17,0,0,0), now), '??')
        self.assertEqual(agelib.agestr(dt(2010,7,16,6,0,0), now), '0d')
        self.assertEqual(agelib.agestr(dt(2010,7,14,0,0,0), now), '2d')
        self.assertEqual(agelib.agestr(dt(2010,6,16,0,0,0), now), '4w')
        self.assertEqual(agelib.agestr(dt(2010,4,17,0,0,0), now), '12w')
        self.assertEqual(agelib.agestr(dt(2010,4,16,0,0,0), now), '3m')
        self.assertEqual(agelib.agestr(dt(2007,7,17,6,0,0), now), '35m')
        self.assertEqual(agelib.agestr(dt(2007,7,16,6,0,0), now), '3y')

    def test_parse_dob_or_age(self):
        dt = DateTime.DateTime
        now = dt(2010,7,16,13,52,38)
        parse = agelib.parse_dob_or_age
        self.assertEqual(parse(None, now), (None, None))
        self.assertEqual(parse('1d', now), (dt(2010,7,15,13,52,38), 1))
        self.assertEqual(parse('1 day', now), (dt(2010,7,15,13,52,38), 1))
        self.assertEqual(parse('1/7', now), (dt(2010,7,15,13,52,38), 1))
        self.assertEqual(parse('1w', now), (dt(2010,7,9,13,52,38), 7))
        self.assertEqual(parse('1 week', now), (dt(2010,7,9,13,52,38), 7))
        self.assertEqual(parse('1m', now), (dt(2010,6,16,13,52,38), 31))
        self.assertEqual(parse('1 month', now), (dt(2010,6,16,13,52,38), 31))
        self.assertEqual(parse('1y', now), (dt(2009,7,16,13,52,38), 366))
        self.assertEqual(parse('1 year', now), (dt(2009,7,16,13,52,38), 366))
        self.assertEqual(parse('2001-2-3', now), (dt(2001,2,3), 0))


