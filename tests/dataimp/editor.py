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
#

import unittest
from cStringIO import StringIO

from tests import testcommon

from casemgr.dataimp import editor
#from casemgr.dataimp.elements import *


edit_new_xml = '''\
<?xml version="1.0"?>
<importrules name="" mode="named" encoding="utf-8" fieldsep="," srclabel="import" conflicts="ignore" />
'''

edit_demog_field_xml = '''\
<?xml version="1.0"?>
<importrules name="" mode="named" encoding="utf-8" fieldsep="," srclabel="import" conflicts="ignore">
 <source field="given_names" src="None" />
</importrules>
'''

edit_form_field_xml = '''\
<?xml version="1.0"?>
<importrules name="" mode="named" encoding="utf-8" fieldsep="," srclabel="import" conflicts="ignore">
 <form name="sars_exposure" version="1">
  <source field="Contact_duration" src="None" />
 </form>
</importrules>
'''

edit_xmas = '''\
<?xml version="1.0"?>
<importrules name="foo" mode="named" encoding="utf-8" fieldsep="," srclabel="import" conflicts="ignore">
 <agesource field="DOB" src="age" />
 <source field="case_status" src="status">
  <translate match="confirm" to="positive" ignorecase="yes" />
  <regexp match="un.*" to="negative" />
 </source>
 <source field="given_names" src="first_name" />
 <ignore field="surname" />
 <fixed field="tags" value="fred" />
 <form name="sars_exposure" version="1">
  <source field="Contact_duration" src="duration" />
 </form>
</importrules>
'''

class DataImpEditorTest(testcommon.AppTestCase):

    create_tables = testcommon.AppTestCase.create_tables + (
        'syndrome_case_status',
        'import_defs',
    )

    def test_new(self):
        e = editor.new(1)
        self.assertEqual(e.rules_xml(), edit_new_xml)
        self.failIf(e.has_changed())
        v = e.view()
        self.assertEqual(v.add_options,
            [('', 'Choose...'), ('sars_exposure', 'Exposure History (SARS)')])
        self.assertEqual(v.unused_cols, [])
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0].name, '')
        self.assertEqual(v[0].label, 'Demographic fields')
        self.assertEqual(v[0], [])

    def test_edit_field(self):
        e = editor.new(1)
        e.add_field('.given_names')
        self.failUnless(e.has_changed())
        self.assertEqual(e.rules_xml(), edit_demog_field_xml)
        # View
        v = e.view()
        self.assertEqual(len(v[0]), 1)
        self.assertEqual(v[0][0].name, 'given_names')
        self.assertEqual(v[0][0].action_desc, 'source column None')

        # Edit
        f = e.edit_field('', 'given_names')
        # action:source
        self.assertEqual(f.selected.action_name, 'source')
        self.assertEqual(f.selected.src, None)
        f.selected.src = 'given_names'
        e.save_edit_field(f)
        self.assertEqual(e.rules_xml(), '''\
<?xml version="1.0"?>
<importrules name="" mode="named" encoding="utf-8" fieldsep="," srclabel="import" conflicts="ignore">
 <source field="given_names" src="given_names" />
</importrules>
''')
        # action:fixed
        f.set_action('fixed')
        f.selected.value = 'fred'
        e.save_edit_field(f)
        self.assertEqual(e.rules_xml(), '''\
<?xml version="1.0"?>
<importrules name="" mode="named" encoding="utf-8" fieldsep="," srclabel="import" conflicts="ignore">
 <fixed field="given_names" value="fred" />
</importrules>
''')
        # action:ignore
        f.set_action('ignore')
        e.save_edit_field(f)
        self.assertEqual(e.rules_xml(), '''\
<?xml version="1.0"?>
<importrules name="" mode="named" encoding="utf-8" fieldsep="," srclabel="import" conflicts="ignore">
 <ignore field="given_names" />
</importrules>
''')
        # action:agesource
        e = editor.new(1)
        e.add_field('.DOB')
        f = e.edit_field('', 'DOB')
        self.assertEqual(f.selected.action_name, 'source')
        f.set_action('agesource')
        f.selected.src = 'dob'
        f.selected.src = 'age'
        e.save_edit_field(f)
        self.assertEqual(e.rules_xml(), '''\
<?xml version="1.0"?>
<importrules name="" mode="named" encoding="utf-8" fieldsep="," srclabel="import" conflicts="ignore">
 <agesource field="DOB" src="age" />
</importrules>
''')
        # translation
        e = editor.new(1)
        e.add_field('.case_status')
        f = e.edit_field('', 'case_status')
        self.assertEqual(f.selected.action_name, 'source')
        f.selected.src = 'status'
        e.save_edit_field(f)
        self.assertEqual(e.rules_xml(), '''\
<?xml version="1.0"?>
<importrules name="" mode="named" encoding="utf-8" fieldsep="," srclabel="import" conflicts="ignore">
 <source field="case_status" src="status" />
</importrules>
''')
        self.assertEqual(f.translations, [])
        f.add_translate(regexp=False)
        f.add_translate(regexp=True)
        self.assertEqual(len(f.translations), 2)
        f.translations[0].match = 'confirm'
        f.translations[0].to = 'positive'
        f.translations[0].ignorecase = 'True'
        f.translations[1].match = 'un.*'
        f.translations[1].to = 'negative'
        f.translations[1].ignorecase = 'False'
        e.save_edit_field(f)
        self.assertEqual(e.rules_xml(), '''\
<?xml version="1.0"?>
<importrules name="" mode="named" encoding="utf-8" fieldsep="," srclabel="import" conflicts="ignore">
 <source field="case_status" src="status">
  <translate match="confirm" to="positive" ignorecase="yes" />
  <regexp match="un.*" to="negative" />
 </source>
</importrules>
''')

    def test_add_form(self):
        e = editor.new(1)
        e.add_form('sars_exposure')
        v = e.view()
        self.assertEqual(v.add_options, [])
        self.assertEqual(len(v), 2)
        self.assertEqual(v[1].name, 'sars_exposure')
        self.assertEqual(v[1].label, 'Exposure History (SARS)')
        self.assertEqual(v[1].add_options, [
            ('', 'Choose...'),
            ('sars_exposure.Contact_duration', 'Contact duration (hours)'),
            ('sars_exposure.Close_contact', 'Contact with case'),
            ('sars_exposure.Contact_date_first', 'Date of first contact'),
            ('sars_exposure.Contact_favourite_food', 'Favourite foods'),
            ('sars_exposure.Contact_date_last', 'Most recent contact')
        ])
        e.add_field('sars_exposure.Contact_duration')
        self.failUnless(e.has_changed())
        self.assertEqual(e.rules_xml(), edit_form_field_xml)
        v = e.view()
        self.assertEqual(v[0], [])
        self.assertEqual(len(v[1]), 1)
        self.assertEqual(v[1][0].name, 'Contact_duration')
        self.assertEqual(v[1][0].action_desc, 'source column None')

        # Delete form
        e.del_form('sars_exposure')
        self.assertEqual(e.rules_xml(), edit_new_xml)

        # Edit form
        e = editor.new(1)
        e.add_form('sars_exposure')
        e.add_field('sars_exposure.Contact_duration')
        self.assertEqual(e.rules_xml(), edit_form_field_xml)
        f = e.edit_field('sars_exposure', 'Contact_duration')
        self.assertEqual(f.selected.action_name, 'source')
        self.assertEqual(f.selected.src, None)
        f.selected.src = 'duration'
        e.save_edit_field(f)
        self.assertEqual(e.rules_xml(), '''\
<?xml version="1.0"?>
<importrules name="" mode="named" encoding="utf-8" fieldsep="," srclabel="import" conflicts="ignore">
 <form name="sars_exposure" version="1">
  <source field="Contact_duration" src="duration" />
 </form>
</importrules>
''')

    def test_round_trip(self):
        # Test in-memory round-trip
        f = StringIO(edit_xmas)
        e = editor.load_file(None, 1, None, f)
        self.assertEqual(e.rules_xml(), edit_xmas)
        # Now test DB round-trip
        e.save()
        self.assertEqual(e.def_id, 1)
        e = editor.load(None, 1, 1)
        self.assertEqual(e.rules_xml(), edit_xmas)
        self.assertEqual(e.available(), [(1, 'foo')])
        # Resave
        e.save()
        self.assertEqual(e.available(), [(1, 'foo')])
        # Duplicate name
        f = StringIO(edit_xmas)
        e = editor.load_file(None, 1, None, f)
        self.assertRaises(editor.Error, e.save)
        # Check delete def
        e = editor.load(None, 1, 1)
        e.delete()
        self.assertEqual(e.available(), [])
        self.assertRaises(editor.Error, editor.load, None, 1, 1)


if __name__ == '__main__':
    unittest.main()
