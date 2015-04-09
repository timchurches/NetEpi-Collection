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

from casemgr import person

import testcommon

class SoftTitleCase(unittest.TestCase):

    def test(self):
        def test(inp, expect):
            self.assertEqual(person.soft_titlecase(inp), expect)
        test('fred flintstone', 'Fred Flintstone')
        test('FRED FLINTSTONE', 'Fred Flintstone')
        test('fred flintstonE', 'Fred flintstonE')
        test('Fred flintstonE', 'Fred flintstonE')
        test('Barney von Rubble', 'Barney von Rubble')
        test('barney von Rubble', 'barney von Rubble')
        test('barney von rubble', 'Barney von Rubble')
        test('michael o\'rourke', 'Michael O\'Rourke')
        test('Michael O\'Rourke', 'Michael O\'Rourke')
        test('rip van winkle', 'Rip Van Winkle')        # hmm
        test('jane smith-jones', 'Jane Smith-Jones')
        test('McNamara', 'McNamara')
        test('frog\'s hollow', 'Frog\'s Hollow')
        test('No address supplied', 'No address supplied')
        test('nORTHSTYNE rOAD', 'nORTHSTYNE rOAD')      # Could do better
        test('"neverseen" hidden valley', '"Neverseen" Hidden Valley')
        test("'neverseen' hidden valley", "'neverseen' Hidden Valley") #Hmm
        test("'Neverseen' Hidden Valley", "'Neverseen' Hidden Valley")
