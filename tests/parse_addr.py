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

from cocklebur.utils import parse_addr

class AddressTest(unittest.TestCase):

    def _test(self, addr, user, domain):
        self.assertEqual(parse_addr(addr), (user, domain))

    def bad_address(self):
        self.assertRaises(ValueError, parse_addr, '')
        self.assertRaises(ValueError, parse_addr, '@')
        self.assertRaises(ValueError, parse_addr, 'foo@')
        self.assertRaises(ValueError, parse_addr, '@example.com')
        self.assertRaises(ValueError, parse_addr, 'foo@example')
        self.assertRaises(ValueError, parse_addr, '<foo@example>')
        self.assertRaises(ValueError, parse_addr, 'foo@bah@example.com')

    def bare_address(self):
        self._test('foo@example.com', 'foo', 'example.com')
        self._test('foo@example.com.au', 'foo', 'example.com.au')
        self._test(' foo@example.com ', 'foo', 'example.com')
        self._test(' foo@example.com. ', 'foo', 'example.com')
        self._test('(biz@flibble.com) foo@example.com', 'foo', 'example.com')
        self._test('(biz@flibble.com) foo@example.com.', 'foo', 'example.com')
        self._test('foo@example.com (biz@flibble.com)', 'foo', 'example.com')
        self._test('foo@example.com. (biz@flibble.com)', 'foo', 'example.com')
        self._test('foo@EXAMPLE.com (biz@flibble.com)', 'foo', 'example.com')

    def delim_address(self):
        self._test('<foo@example.com>', 'foo', 'example.com')
        self._test('<foo@example.com.>', 'foo', 'example.com')
        self._test('<foo@example.com.au>', 'foo', 'example.com.au')
        self._test(' <foo@example.com> ', 'foo', 'example.com')
        self._test('biz@flibble.com <foo@example.com>', 'foo', 'example.com')
        self._test('<foo@example.com> biz@flibble.com', 'foo', 'example.com')
        self._test('"biz@flibble.com" <foo@example.com>', 'foo', 'example.com')
        self._test('<foo@example.com> "biz@flibble.com"', 'foo', 'example.com')
        self._test('<foo@EXAMPLE.com> "biz@flibble.com"', 'foo', 'example.com')


class suite(unittest.TestSuite):
    test_list = (
        'bad_address',
        'bare_address',
        'delim_address',
    )
    def __init__(self):
        unittest.TestSuite.__init__(self, map(AddressTest, self.test_list))


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
