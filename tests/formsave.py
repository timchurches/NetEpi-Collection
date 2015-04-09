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

import os
import shutil
from cStringIO import StringIO
import unittest

from cocklebur import form_ui
from cocklebur.form_ui.xmlsave import xmlsave
from cocklebur.form_ui.xmlload import xmlload
from cocklebur.form_ui.pysave import pysave
from cocklebur.form_ui.pyload import pyload

scratchdir = os.path.join(os.path.dirname(__file__), 'scratch')
scratchfile = os.path.join(scratchdir, 'testform.py')

class _FormSaveTests(unittest.TestCase):
    def _test(self, form):
        try:
            os.mkdir(scratchdir)
            f = open(scratchfile, 'w')
            try:
                self.save(f, form)
            finally:
                f.close()
#            print open(scratchfile, 'r').read()
            f = open(scratchfile, 'r')
            try:
                loaded = self.load(f)
            finally:
                f.close()
            self.assertEqual(form, loaded)
        finally:
            shutil.rmtree(scratchdir)

    def runTest(self):
        # Some string that will cause a parse error from all our loaders:
        self.assertRaises(form_ui.FormParseError, self.load, StringIO('<abc'))

        form = form_ui.Form('Test form', name='testform',
                            form_type='abc', allow_multiple=True)
        self._test(form)

        section = form_ui.Section('Section A')
        form.append(section)
        self._test(form)

        form.question(text='Question A', 
            input=form_ui.TextInput('input_a', summary='xyz blah'))
        section.question(text='Question B', 
            disabled=True, help='AbC<p>dEf&gh',
            trigger_mode='enable',
            triggers=['input_c'],
            input=form_ui.TextInput('input_b', 
                pre_text='pretextxx', post_text='posttextyy', maxsize=10))
        self._test(form)

        section.question(text='Question C', 
            input=form_ui.CheckBoxes('input_c',
                choices = [
                    ('a', 'Choice A'),
                    ('b', 'Choice B')],
                skips = [
                    form_ui.Skip('input_c', ['a'], True),
                    form_ui.Skip('input_c', ['b'], 
                        not_selected=True, show_msg=False, 
                        skip_remaining=False)],
                default='b', required=True,
                direction='horizontal'))

        section.question(text='Question D', 
            inputs = [
                form_ui.FloatInput('input_da',
                    minimum=10, maximum=20),
                form_ui.IntInput('input_db',
                    minimum=10, maximum=20)])

        self._test(form)

class XMLTests(_FormSaveTests):
    def save(self, f, form):
        xmlsave(f, form)

    def load(self, f):
        return xmlload(f)

    # For backtraces
    def runTest(self):
        _FormSaveTests.runTest(self)

class PYTests(_FormSaveTests):
    def save(self, f, form):
        pysave(f, form)

    def load(self, f):
        return pyload(f)

    # For backtraces
    def runTest(self):
        _FormSaveTests.runTest(self)

def suite():
    suite = unittest.TestSuite()
    suite.addTest(XMLTests())
    suite.addTest(PYTests())
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
