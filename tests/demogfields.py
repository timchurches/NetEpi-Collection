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
import unittest

from cocklebur import dbobj

import testcommon

from casemgr import demogfields

#dbobj.execute_debug(1)

thisdir = os.path.dirname(__file__)
scratchdir = os.path.join(thisdir, 'scratch')

CD_FIELD = 2    # Pick an arbitrary field to test - case definition

class DemogFieldsTest(testcommon.DBTestCase):

    def setUp(self):
        td = self.new_table(demogfields.DEMOG_TABLE)
        # This needs to be kept in sync the schema, unfortunately - we can't
        # use the schema directly, or we'd have to create all the dependancies
        # as well.
        td.column('synddf_id', dbobj.SerialColumn, primary_key = True)
        td.column('syndrome_id', dbobj.IntColumn)
        td.column('name', dbobj.StringColumn)
        td.column('label', dbobj.StringColumn)
        td.column('show_case', dbobj.BooleanColumn, default = 'True')
        td.column('show_form', dbobj.BooleanColumn, default = 'True')
        td.column('show_search', dbobj.BooleanColumn, default = 'True')
        td.column('show_person', dbobj.BooleanColumn, default = 'True')
        td.add_index('sdf_syndrome_id', ['syndrome_id'])
        td.add_index('sdf_si_name_idx', ['syndrome_id', 'name'], unique=True)
        td.create()
        self.db.commit()

    def execute(self, cmd, args):
        curs = self.db.cursor()
        try:
            dbobj.execute(curs, cmd % demogfields.DEMOG_TABLE, args)
        finally:
            curs.close()

    def user(self):
        # Check defaults derived from classes with no local override
        common_fields = demogfields.get_demog_fields(self.db, None)
        self.assertEqual(common_fields[CD_FIELD].name, 'case_definition')
        self.assertEqual(common_fields[CD_FIELD].show('case'), True)
        self.assertEqual(common_fields[CD_FIELD].show('search'), True)
        self.assertEqual(common_fields[CD_FIELD].show('person'), False)

        # Syndrome-specific fields with no override
        synd_fields = demogfields.get_demog_fields(self.db, None)
        self.assertEqual(synd_fields[CD_FIELD].name, 'case_definition')
        self.assertEqual(synd_fields[CD_FIELD].show('case'), True)
        self.assertEqual(synd_fields[CD_FIELD].show('search'), True)
        self.assertEqual(synd_fields[CD_FIELD].show('person'), False)

        # Now check defaults with db-derived common override
        self.execute('INSERT INTO %s (name, label, show_case)'
                     ' VALUES (%%s, %%s, %%s)',
                     ('case_definition', 'LABEL', False))
        demogfields.flush()
        common_fields = demogfields.get_demog_fields(self.db, None)
        self.assertEqual(common_fields[CD_FIELD].name, 'case_definition')
        self.assertEqual(common_fields[CD_FIELD].label, 'LABEL')
        self.assertEqual(common_fields[CD_FIELD].show('case'), False)
        self.assertEqual(common_fields[CD_FIELD].show('search'), True)
        self.assertEqual(common_fields[CD_FIELD].show('person'), False)

        # Syndrome-specific fields with common override
        demogfields.flush()
        synd_fields = demogfields.get_demog_fields(self.db, 1)
        self.assertEqual(synd_fields[CD_FIELD].name, 'case_definition')
        self.assertEqual(synd_fields[CD_FIELD].label, 'LABEL')
        self.assertEqual(synd_fields[CD_FIELD].show('case'), False)
        self.assertEqual(synd_fields[CD_FIELD].show('search'), True)
        self.assertEqual(synd_fields[CD_FIELD].show('person'), False)

        # Now check Syndrome-specific with Syndrome-specific override
        self.execute('INSERT INTO %s (syndrome_id, name, label, show_search)'
                     ' VALUES (%%s, %%s, %%s, %%s)',
                     (1, 'case_definition', 'FROG', False))
        demogfields.flush()
        synd_fields = demogfields.get_demog_fields(self.db, 1)
        self.assertEqual(synd_fields[CD_FIELD].name, 'case_definition')
        self.assertEqual(synd_fields[CD_FIELD].label, 'FROG')
        self.assertEqual(synd_fields[CD_FIELD].show('case'), True)
        self.assertEqual(synd_fields[CD_FIELD].show('search'), False)
        self.assertEqual(synd_fields[CD_FIELD].show('person'), False)

        # And verify common values have not changed
        demogfields.flush()
        common_fields = demogfields.get_demog_fields(self.db, None)
        self.assertEqual(common_fields[CD_FIELD].name, 'case_definition')
        self.assertEqual(common_fields[CD_FIELD].label, 'LABEL')
        self.assertEqual(common_fields[CD_FIELD].show('case'), False)
        self.assertEqual(common_fields[CD_FIELD].show('search'), True)
        self.assertEqual(common_fields[CD_FIELD].show('person'), False)

    def admin(self):
        def _check(label, show_case, show_form, show_search, show_person):
            def _assert(field, want):
                got = getattr(fields[CD_FIELD], field)
                self.assertEqual(got, want, 'field %r: got %r wanted %r' % 
                                        (field, got, want))
            _assert('name', 'case_definition')
            if label:
                _assert('label', label)
            _assert('show_case', show_case)
            _assert('show_form', show_form)
            _assert('show_search', show_search)
            _assert('show_person', show_person)

        #dbobj.execute_debug(1)

        # Check initial state, per syndrome
        fields = demogfields.DemogFields(self.db, 1)
        _check(None, True, True, True, False)

        # Now edit, commit, and reload
        fields[CD_FIELD].label = 'SALAMANDA'
        fields[CD_FIELD].show_form = False
        fields.update(self.db)
        fields = demogfields.DemogFields(self.db, 1)
        _check('SALAMANDA', True, False, True, False)

        # Common/default initial state
        fields = demogfields.DemogFields(self.db, None)
        _check(None, True, True, True, False)

        # Now edit, commit, and reload
        fields[CD_FIELD].label = 'CATFISH'
        fields[CD_FIELD].show_search = False
        fields.update(self.db)
        fields = demogfields.DemogFields(self.db, None)
        _check('CATFISH', True, True, False, False)

    def field_api(self):
        def _field_api(field):
            self.failUnless(hasattr(field, 'disabled'))
            self.failUnless(hasattr(field, 'entity'))
            self.failUnless(hasattr(field, 'field'))
            self.failUnless(hasattr(field, 'hideable'))
            self.failUnless(hasattr(field, 'label'))
            self.failUnless(hasattr(field, 'name'))
            self.failUnless(hasattr(field, 'render'))
            self.failUnless(hasattr(field, 'section'))
            for context in demogfields.contexts:
                self.failUnless(hasattr(field, 'show_' + context))
                self.failUnless(field.show(context) in (True, False))
        for field in demogfields.get_demog_fields(self.db, None):
            _field_api(field)
        for field in demogfields.get_demog_fields(self.db, 0):
            _field_api(field)

    def context_field_api(self):
        def _field_api(field):
            self.failUnless(hasattr(field, 'context'))
            self.failUnless(hasattr(field, 'disabled'))
            self.failUnless(hasattr(field, 'entity'))
            self.failUnless(hasattr(field, 'field'))
            self.failUnless(hasattr(field, 'hideable'))
            self.failUnless(hasattr(field, 'label'))
            self.failUnless(hasattr(field, 'name'))
            self.failUnless(hasattr(field, 'render'))
            self.failUnless(hasattr(field, 'section'))
        fields = demogfields.get_demog_fields(self.db, None)
        for context in demogfields.contexts:
            for field in fields.context_fields(context):
                _field_api(field)
                


class Suite(unittest.TestSuite):
    test_list = (
        'user',
        'admin',
        'field_api',
        'context_field_api',
    )
    def __init__(self):
        unittest.TestSuite.__init__(self, map(DemogFieldsTest, self.test_list))


def suite():
    return Suite()

if __name__ == '__main__':
    unittest.main(defaultTest='suite')

