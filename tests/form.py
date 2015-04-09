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

# This module tests form object instantiation.

import unittest
from cocklebur import form_ui

class FormTest(unittest.TestCase):
    def minimal_form(self):
        form = form_ui.Form('A test form')
        self.assertEqual(form.text, 'A test form')
        self.assertEqual(form.name, None)
        self.assertEqual(form.version, None)
        self.assertEqual(form.form_type, 'case')
        self.assertEqual(form.allow_multiple, False)
        self.assertEqual(form.table, None)
        args = dict(name='testform_name', form_type='testform_type',
                    allow_multiple=True)
        form = form_ui.Form('A test form', **args)
        self.assertEqual(form.text, 'A test form')
        for k, v in args.items():
            av = getattr(form, k)
            self.assertEqual(av, v, '%s: attr %s != arg %s' % (k, av, v))

    def form_with_section_and_questions(self):
        form = form_ui.Form('A test form')
        section = form_ui.Section('A section')
        form.append(section)
        self.assertEqual(form.text, 'A test form')
        self.assertEqual(len(form), 1)
        self.assertEqual(len(form.children[0]), 0)
        self.assertEqual(form.children[0].text, 'A section')
        section.question('A question')
        self.assertEqual(len(form.children[0]), 1)
        question = form.children[0].children[0]
        self.assertEqual(question.text, 'A question')
        self.assertEqual(question.inputs, [])
        self.assertEqual(question.help, None)
        self.assertEqual(question.disabled, False)
        section.question('A second question', help='Some help', disabled=True)
        self.assertEqual(len(form.children[0]), 2)
        question = form.children[0].children[1]
        self.assertEqual(question.text, 'A second question')
        self.assertEqual(question.inputs, [])
        self.assertEqual(question.help, 'Some help')
        self.assertEqual(question.disabled, True)
        form.question('A form question')
        self.assertEqual(len(form), 2)
        question = form.children[1]
        self.assertEqual(question.text, 'A form question')


class FormSuite(unittest.TestSuite):
    test_list = (
        'minimal_form',
        'form_with_section_and_questions',
    )

    def __init__(self):
        unittest.TestSuite.__init__(self, map(FormTest, self.test_list))

def suite():
    return FormSuite()

if __name__ == '__main__':
    unittest.main(defaultTest='suite')

