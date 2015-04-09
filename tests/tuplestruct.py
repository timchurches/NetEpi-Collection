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
import cPickle
from cocklebur.tuplestruct import TupleStruct

class SS(TupleStruct): __slots__ = 'a', 'b'

class Case(unittest.TestCase):
    def _test(self, ss):
        self.assertEqual((ss.a, ss.b), (3, 4))
        self.assertEqual(tuple(ss), (3, 4))
        self.assertEqual((ss[0], ss[1]), (3, 4))
        self.assertEqual(len(ss), 2)
        self.assertRaises(AttributeError, getattr, ss, 'x')

    def runTest(self):
        self.assertRaises(TypeError, SS, 1)
        self.assertRaises(TypeError, SS, 1, 2, 3)
        ss = SS(3, 4)
        self._test(ss)

        self.assertRaises(TypeError, SS, a=1)
        self.assertRaises(TypeError, SS, a=1, b=2, c=3)
        ss = SS(b=4, a=3)
        self._test(ss)

        ss = cPickle.loads(cPickle.dumps(ss))
        self._test(ss)

def suite():
    return Case()

if __name__ == '__main__':
    unittest.main(defaultTest='suite')

