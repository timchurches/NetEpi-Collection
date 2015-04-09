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
import os, sys
import shutil
import unittest
import copy
from cStringIO import StringIO

from cocklebur import dbobj
from cocklebur import form_ui

import testcommon
import formcommon

#dbobj.execute_debug(1)

thisdir = os.path.dirname(__file__)
scratchdir = os.path.join(thisdir, 'scratch')

class _FormLibTests(unittest.TestCase):

    def runTest(self):
        # No forms to start with
        self.assertEqual(list(self.formlib), [])
        self.assertEqual(len(self.formlib), 0)
        self.assertRaises(form_ui.NoFormError, 
                          self.formlib.load, 'testform', 1)
        self.assertEqual(self.formlib.versions('testform'), [])

        # Create a form, save and restore
        testform = formcommon.get_testform()
        saved_version = self.formlib.save(testform, 'testform')
        self.assertEqual(saved_version, 1)
        self.assertEqual(testform.version, 1)
        self.assertEqual(testform.name, 'testform')
        self.assertEqual(testform.table, 'form_testform_00001')
        self.assertEqual(len(self.formlib), 1)
        available = list(self.formlib)
        self.assertEqual(len(available), 1)
        self.assertEqual(available[0].name, 'testform')
        self.assertEqual(available[0].version, 1)
        self.assertEqual(self.formlib.versions('testform'), [1])
        loadedform = available[0].load()
        self.assertEqual(testform, loadedform)
        self.assertEqual(loadedform.version, 1)
        self.assertEqual(loadedform.name, 'testform')
        self.assertEqual(loadedform.table, 'form_testform_00001')

        # Modify the form, save and restore
        newform = copy.deepcopy(testform)
        newform.text = 'Modified test form'
        newform.children[1].text = 'Modified Third Question'
        del newform.children[1].inputs[0].choices[2]
        saved_version = self.formlib.save(newform, 'testform')
        self.assertEqual(saved_version, 2)
        self.assertEqual(len(self.formlib), 2)
        available = list(self.formlib)
        self.assertEqual(len(available), 2)
        self.assertEqual(available[0].name, 'testform')
        self.assertEqual(available[0].version, 1)
        self.assertEqual(available[1].version, 2)
        self.assertEqual(self.formlib.versions('testform'), [1, 2])
        loadedform = available[0].load()
        self.assertEqual(testform, loadedform)
        loadedform = available[1].load()
        self.assertEqual(newform, loadedform)
        self.assertEqual(loadedform.version, 2)
        self.assertEqual(loadedform.name, 'testform')
        self.assertEqual(loadedform.table, 'form_testform_00002')

        # Save As
        saved_version = self.formlib.save(newform, 'altform')
        self.assertEqual(saved_version, 1)
        self.assertEqual(len(self.formlib), 3)
        available = list(self.formlib)
        self.assertEqual(len(available), 3)
        self.assertEqual(available[0].name, 'altform')
        self.assertEqual(available[0].version, 1) 
        self.assertEqual(available[1].name, 'testform')
        self.assertEqual(available[2].name, 'testform')
        self.assertEqual(newform.version, 1)
        self.assertEqual(newform.name, 'altform')
        self.assertEqual(newform.table, 'form_altform_00001')

        # Rename the form
        self.assertRaises(form_ui.DuplicateFormError, self.formlib.rename, 
                          'testform', 'altform')
        self.assertRaises(form_ui.NoFormError, self.formlib.rename, 
                          'noform', 'newtestform')
        self.formlib.rename('testform', 'newtestform')
        available = list(self.formlib)
        self.assertEqual(len(available), 3)
        self.assertEqual(available[0].name, 'altform')
        self.assertEqual(available[1].name, 'newtestform')
        self.assertEqual(available[1].version, 1)
        self.assertEqual(available[2].name, 'newtestform')
        self.assertEqual(available[2].version, 2)

        # Delete the form
        self.assertRaises(form_ui.NoFormError, self.formlib.delete, 'noform')
        self.formlib.delete('newtestform')
        available = list(self.formlib)
        self.assertEqual(len(available), 1)
        self.assertEqual(available[0].name, 'altform')


class FormLibPyFilesCase(_FormLibTests):

    def setUp(self):
        os.mkdir(scratchdir)
        self.formlib = form_ui.FormLibPyFiles(scratchdir)

    def tearDown(self):
        shutil.rmtree(scratchdir)


class FormLibXMLDBCase(_FormLibTests, testcommon.DBTestCase):

    def setUp(self):
        td = self.new_table('form_defs')
        td.column('name', dbobj.StringColumn)
        td.column('version', dbobj.IntColumn)
        td.column('xmldef', dbobj.StringColumn)
        td.add_index('fd_namever_idx', ['name', 'version'], unique=True)
        td.add_index('fd_name_idx', ['name'])
        td.create()
        self.formlib = form_ui.FormLibXMLDB(self.db, 'form_defs')


def suite():
    suite = unittest.TestSuite()
    suite.addTest(FormLibPyFilesCase())
    suite.addTest(FormLibXMLDBCase())
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')

