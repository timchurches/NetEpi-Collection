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
from cStringIO import StringIO

from cocklebur import xmlparse

class Parser(xmlparse.XMLParse):
    root_tag = 'top'

    class top(xmlparse.ContainerNode):
        subtags = ('next', 'attr')
        permit_attrs = ('x', 'y')

    class next(xmlparse.Node):
        pass

    class attr(xmlparse.Node):
        permit_attrs = ('one', 'two:int', 'three:bool', 'four:float', 
                        'five:str', 'six:unicode')


class XMLParseTests(unittest.TestCase):
    def _test(self, xml):
        return Parser().parse(StringIO(xml))

    def _exc(self, xml):
        self.assertRaises(xmlparse.ParseError, self._test, xml)

    def test_basic(self):
        self._test('<top />')
        self._test('<?xml version="1.0" encoding="UTF-8"?><top />')
        self._test('<top></top>')
        self._test('<top>cdata</top>')
        self._test('\n<top></top>')
        self._test('<top><next /></top>')
        self._test('<top><next></next></top>')

    def test_tree(self):
        top = self._test('<top x="1" y=\'2\'>A\nB<next>\nC\n</next>\nD\n</top>')
        self.assertEqual(top.name, 'top')
        self.assertEqual(top.get_text(), 'A\nB\nD\n')
        self.assertEqual(top.attrs, dict(x='1', y='2'))
        self.assertEqual(len(top.children), 1)
        next = top.children[0]
        self.assertEqual(next.name, 'next')
        self.assertEqual(next.attrs, {})
        self.assertEqual(next.get_text(), '\nC\n')

    def test_types(self):
        top = self._exc('<top><attr two="x" /></top>')
        top = self._exc('<top><attr two="." /></top>')
        top = self._exc('<top><attr two="" /></top>')
        top = self._exc('<top><attr three="1" /></top>')
        top = self._exc('<top><attr three="bah" /></top>')
        top = self._exc('<top><attr four="x" /></top>')
        top = self._exc('<top><attr four="." /></top>')
        top = self._exc('<top><attr four="" /></top>')
        top = self._test('<top><attr one="xx" two="2" three="yes" four="4.4" '
                         'five="yy" six="zz" /><attr two="1000000000000" '
                         'three="no" four="-1e20" /></top>')
        self.assertEqual(top.name, 'top')
        self.assertEqual(top.get_text(), '')
        self.assertEqual(top.attrs, {})
        self.assertEqual(len(top.children), 2)
        attr = top.children[0]
        self.assertEqual(attr.name, 'attr')
        self.assertEqual(attr.get_text(), '')
        self.assertEqual(attr.attrs, 
            dict(one="xx", two=2, three=True, four=4.4, five="yy", six=u"zz"))
        attr = top.children[1]
        self.assertEqual(attr.name, 'attr')
        self.assertEqual(attr.get_text(), '')
        self.assertEqual(attr.attrs, 
            dict(two=1000000000000L, three=False, four=-1e20))

    def test_errors(self):
        self._exc('')                           # No top level
        self._exc('</top>')                     # No top level
        self._exc('<?xml version="1.0" encoding="UTF-8"?>')
        self._exc('<top>')                      # Not closed
        self._exc('<top z="1" />')              # Unknown attribute
        self._exc('<top></pot>')                # Not closed
        self._exc('cdata<top></top>')
        self._exc('<top></top>cdata')
        self._exc('<top></top></top>')          # closed twice
        self._exc('<top/></top>')               # closed twice
        self._exc('<next />')                   # Not valid top-level
        self._exc('<unknown />')                # Unknown tag
        self._exc('<top><next></top>')          # <next> not closed
        self._exc('<top><top /></top>')         # <top> not allowed in <top>
        self._exc('<top/><top />')              # multiple top levels
        

class suite(unittest.TestSuite):
    test_list = (
        'test_basic',
        'test_tree',
        'test_types',
        'test_errors',
    )
    def __init__(self):
        unittest.TestSuite.__init__(self, map(XMLParseTests, self.test_list))

if __name__ == '__main__':
    unittest.main(defaultTest='suite')

