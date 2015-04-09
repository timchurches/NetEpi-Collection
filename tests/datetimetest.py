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
from cocklebur import datetime
from mx import DateTime
import operator

class Case(unittest.TestCase):

    def tearDown(self):
        datetime.set_date_style('DMY')

    def _test(self, fn, args, expect):
        result = fn(*args)
        self.assertEqual(result, expect, 
                         'input %s, expected %s, got %s' % \
                            (', '.join([str(a) for a in args]), expect, result))

    def parse_date(self):
        def _parse_date(arg, expect):
            self._test(datetime.parse_date, (arg,), expect)

        _parse_date('11/12/30', (1930, 12, 11))
        _parse_date('11/12/07', (2007, 12, 11))
        _parse_date('11/12/00', (2000, 12, 11))
        _parse_date('11/12/2000', (2000, 12, 11))
        _parse_date('11-12-00', (2000, 12, 11))
        _parse_date('11-12-2000', (2000, 12, 11))
        _parse_date('11-12-1900', (1900, 12, 11))
        _parse_date('1900-12-11', (1900, 12, 11))
        _parse_date('2007-12-11', (2007, 12, 11))
        self.assertRaises(datetime.Error, 
                          datetime.parse_date, '11/12')
        self.assertRaises(datetime.Error, 
                          datetime.parse_date, '11/12/30/03')
        self.assertEqual(datetime.set_date_style('MDY'), 'DMY')
        _parse_date('12/11/30', (1930, 12, 11))
        _parse_date('12-11-2000', (2000, 12, 11))
        _parse_date('2007-12-11', (2007, 12, 11))

    def parse_time(self):
        def _parse_time(arg, expect):
            self._test(datetime.parse_time, (arg,), expect)
        
        _parse_time('11:12', (11,12,0))
        _parse_time('11:12:13', (11,12,13))
        _parse_time('11:12:13', (11,12,13))
        self.assertRaises(datetime.Error,
                          datetime.parse_time, '11:12:13:14')
        self.assertRaises(datetime.Error,
                          datetime.parse_time, '-11:12:13')
        self.assertRaises(datetime.Error,
                          datetime.parse_time, '11:-12:13')
        self.assertRaises(datetime.Error,
                          datetime.parse_time, '24:00:00')

    def mx_parse_date(self):
        def _mx_parse_date(arg, expect):
            self._test(datetime.mx_parse_date, (arg,), expect)
        
        _mx_parse_date('11/12/30', DateTime.DateTime(1930, 12, 11))
        _mx_parse_date('11/12/30', DateTime.DateTime(1930, 12, 11, 11, 59, 59))
        self.assertRaises(datetime.Error,
                          datetime.mx_parse_date, '30/02/03')

    def mx_parse_time(self):
        def _mx_parse_time(arg, expect):
            self._test(datetime.mx_parse_time, (arg,), expect)
        
        _mx_parse_time('11:12', DateTime.DateTimeDelta(0, 11, 12))
        _mx_parse_time('11:12:13', DateTime.DateTimeDelta(0, 11, 12, 13))
        _mx_parse_time('11:12:13', DateTime.DateTimeDelta(0, 11, 12, 13.999))
        _mx_parse_time(DateTime.DateTimeDelta(0, 11, 12, 13.999),
                       DateTime.DateTimeDelta(0, 11, 12, 13.999))
        _mx_parse_time(DateTime.DateTime(2003, 02, 27, 11, 12, 13),
                       DateTime.DateTimeDelta(0, 11, 12, 13))
        self.assertRaises(datetime.Error,
                          datetime.mx_parse_time, '11:22:33:44')
        self.assertRaises(datetime.Error,
                          datetime.mx_parse_time,
                          DateTime.DateTimeDelta(0, 24, 0, 0))
        self.assertRaises(datetime.Error,
                          datetime.mx_parse_time,
                          DateTime.DateTimeDelta(1, 0, 0, 0))

    def mx_parse_datetime(self):
        def _mx_parse_datetime(arg, expect):
            self._test(datetime.mx_parse_datetime, (arg,), expect)
        
        _mx_parse_datetime('27/02/03 11:12:13', 
                           DateTime.DateTime(2003, 02, 27, 11, 12, 13))
        _mx_parse_datetime('11:12:13 27/02/03', 
                           DateTime.DateTime(2003, 02, 27, 11, 12, 13))
        _mx_parse_datetime('11:12:13 27/02/03', 
                           DateTime.DateTime(2003, 02, 27, 11, 12, 13.999))
        t = datetime.mx_parse_datetime('11:12:13 27/02/03')
        self._test(t.time, (), DateTime.DateTimeDelta(0, 11, 12, 13))
        self._test(t.date, (), DateTime.DateTime(2003, 02, 27))
        self.assertRaises(datetime.Error,
                          datetime.mx_parse_datetime, '11:12:13pm 27/02/03')
        self.assertRaises(datetime.Error,
                          datetime.mx_parse_datetime, '11:12:13 pm 27/02/03')

    def operators(self):
        def _test_op(a, op, b, expect):
            if a is None:
                aa = None
            else:
                aa = datetime.mx_parse_datetime(a)
            if b is None:
                bb = None
            elif type(b) is DateTime.DateTimeDeltaType:
                bb = b
            else:
                bb = datetime.mx_parse_datetime(b)
            r = op(aa, bb)
            self.assertEqual(r, expect, 
                             '%s %s %s, expected %s, got %s' %\
                                (a, op.__name__, b, expect, r))

        _test_op('1/1/03', operator.eq, '1/1/03', True)
        _test_op('1/1/03', operator.eq, '2/1/03', False)
        _test_op('1/1/03', operator.eq, None, False)

        _test_op('1/1/03', operator.ne, '1/1/03', False)
        _test_op('1/1/03', operator.ne, '2/1/03', True)
        _test_op('1/1/03', operator.ne, None, True)

        _test_op('1/1/03', operator.gt, '2/1/03', False)
        _test_op('2/1/03', operator.gt, '1/1/03', True)
        _test_op('2/1/03', operator.gt, None, True)
        _test_op('2/1/03', operator.lt, None, False)
        delta = DateTime.DateTimeDelta(1)
        _test_op('2/1/03', operator.add, delta,
                 DateTime.DateTime(2003,1,3))
        _test_op('2/1/03', operator.sub, delta,
                 DateTime.DateTime(2003,1,1))

    def relative(self):
        def _test(a, b, expect):
            a = datetime.mx_parse_datetime(a)
            b = datetime.mx_parse_datetime(b)
            got = datetime.relative(a, b)
            self.assertEqual(got, expect, 'got %s, expected %s' % (got, expect))
        _test('1/1/03 12:34:56', '1/1/03 12:34:56', 'in less than a minute')
        _test('1/1/03 12:33:56', '1/1/03 12:34:56', '1 minute ago')
        _test('1/1/03 12:35:56', '1/1/03 12:34:56', 'in 1 minute')
        _test('1/1/03 12:36:56', '1/1/03 12:34:56', 'in 2 minutes')
        _test('1/1/03 14:34:56', '1/1/03 12:34:56', 'in 2 hours')
        _test('3/1/03 12:34:56', '1/1/03 12:34:56', 'in 2 days')
        _test('15/1/03 12:34:56', '1/1/03 12:34:56', 'in 2 weeks')
        _test('1/3/03 12:34:56', '1/1/03 12:34:56', 'in 2 months')
        _test('1/1/05 12:34:56', '1/1/03 12:34:56', 'in 2 years')

    def parse_discrete(self):
        def _test(rel, ref, expect):
            ref = datetime.mx_parse_datetime(ref)
            expect = datetime.mx_parse_datetime(expect)
            got = datetime.parse_discrete(rel, ref)
            self.assertEqual(got, expect, 'got %s, expected %s' % (got, expect))
        _test('now', '1/1/03 12:34:56', '1/1/03 12:34:56')
        _test('tomorrow', '1/1/03 12:34:56', '2/1/03 07:00:00')
        _test('yesterday', '1/1/03 12:34:56', '31/12/02 07:00:00')
        _test('week', '1/1/03 12:34:56', '8/1/03 07:00:00')
        _test('monday', '1/1/03 12:34:56', '6/1/03 07:00:00')
        _test('tuesday', '1/1/03 12:34:56', '7/1/03 07:00:00')
        _test('wednesday', '1/1/03 12:34:56', '8/1/03 07:00:00')
        _test('thursday', '1/1/03 12:34:56', '2/1/03 07:00:00')
        _test('friday', '1/1/03 12:34:56', '3/1/03 07:00:00')
        _test('saturday', '1/1/03 12:34:56', '4/1/03 07:00:00')
        _test('sunday', '1/1/03 12:34:56', '5/1/03 07:00:00')
        # Hours
        _test('1h', '1/1/03 12:34:56', '1/1/03 13:34:56.00')
        _test('hour', '1/1/03 12:34:56', '1/1/03 13:34:56.00')
        _test('1 hour', '1/1/03 12:34:56', '1/1/03 13:34:56.00')
        _test('one hour', '1/1/03 12:34:56', '1/1/03 13:34:56.00')
        _test('2 hours', '1/1/03 12:34:56', '1/1/03 14:34:56.00')
        _test('two hours', '1/1/03 12:34:56', '1/1/03 14:34:56.00')
        _test('24 hours', '1/1/03 12:34:56', '2/1/03 12:34:56.00')
        _test('3/24', '1/1/03 12:34:56', '1/1/03 15:34:56.00')
        _test('three hours', '1/1/03 12:34:56', '1/1/03 15:34:56.00')
        _test('four hours', '1/1/03 12:34:56', '1/1/03 16:34:56.00')
        _test('five hours', '1/1/03 12:34:56', '1/1/03 17:34:56.00')
        _test('six hours', '1/1/03 12:34:56', '1/1/03 18:34:56.00')
        _test('seven hours', '1/1/03 12:34:56', '1/1/03 19:34:56.00')
        _test('eight hours', '1/1/03 12:34:56', '1/1/03 20:34:56.00')
        _test('nine hours', '1/1/03 12:34:56', '1/1/03 21:34:56.00')
        _test('ten hours', '1/1/03 12:34:56', '1/1/03 22:34:56.00')
        _test('2 hours ago', '1/1/03 12:34:56', '1/1/03 10:34:56.00')
        _test('two hours ago', '1/1/03 12:34:56', '1/1/03 10:34:56.00')
        # Days
        _test('1d', '1/1/03 12:34:56', '2/1/03 12:34:56.00')
        _test('day', '1/1/03 12:34:56', '2/1/03 12:34:56.00')
        _test('2 days', '1/1/03 12:34:56', '3/1/03 12:34:56.00')
        _test('3/7', '1/1/03 12:34:56', '4/1/03 12:34:56.00')
        _test('2 days ago', '1/1/03 12:34:56', '30/12/02 12:34:56.00')
        # Weeks
        _test('1w', '1/1/03 12:34:56', '8/1/03 07:00:00')
        _test('week', '1/1/03 12:34:56', '8/1/03 07:00:00')
        _test('2 weeks', '1/1/03 12:34:56', '15/1/03 07:00:00')
        _test('3/52', '1/1/03 12:34:56', '22/1/03 07:00:00')
        _test('12/52', '1/1/03 12:34:56', '26/3/03 07:00:00')
        # Fortnight
        _test('fortnight', '1/1/03 12:34:56', '15/1/03 07:00:00')
        # Months
        _test('1m', '1/1/03 12:34:56', '1/2/03 07:00:00')
        _test('2 months', '1/1/03 12:34:56', '1/3/03 07:00:00')
        _test('3/12', '1/1/03 12:34:56', '1/4/03 07:00:00')
        # Years
        _test('1y', '1/1/03 12:34:56', '1/1/04 07:00:00')
        _test('1 year', '1/1/03 12:34:56', '1/1/04 07:00:00')
        _test('1 yr', '1/1/03 12:34:56', '1/1/04 07:00:00')
        _test('2y', '1/1/03 12:34:56', '1/1/05 07:00:00')
        _test('2 yrs', '1/1/03 12:34:56', '1/1/05 07:00:00')
        _test('two yrs', '1/1/03 12:34:56', '1/1/05 07:00:00')
        _test('two years', '1/1/03 12:34:56', '1/1/05 07:00:00')
        _test('1 year ago', '1/1/03 12:34:56', '1/1/02 07:00:00')
        _test('two years ago', '1/1/03 12:34:56', '1/1/01 07:00:00')
        # Error handling
        self.assertRaises(datetime.Error, datetime.parse_discrete,
                          'sdfkjhgksjfdg')
        self.assertRaises(datetime.Error, datetime.parse_discrete,
                          'one two three')
        self.assertRaises(datetime.Error, datetime.parse_discrete,
                          'one ago')
        self.assertRaises(datetime.Error, datetime.parse_discrete,
                          'now days ago')

class Suite(unittest.TestSuite):
    test_list = (
        'parse_date',
        'parse_time',
        'mx_parse_date',
        'mx_parse_time',
        'mx_parse_datetime',
        'operators',
        'relative',
        'parse_discrete',
    )
    def __init__(self):
        unittest.TestSuite.__init__(self, map(Case, self.test_list))

def suite():
    return Suite()

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
