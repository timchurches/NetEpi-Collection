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

from itertools import izip
from cStringIO import StringIO
try:
    set
except NameError:
    from sets import Set as set

from cocklebur import xmlwriter, dbobj, datetime

from casemgr import globals, reports
from casemgr.reports.reportfilters import *

from tests import testcommon

class DummyField:
    name = 'dummy'
    label = 'Dummy test field'
    table = 'table'

    def optionexpr(self):
        return [
            (1, 'Tag'),
            ('AA', 'aa option'),
            ('BB', 'bb option'),
            ('CC', 'cc option'),
        ]

class DummyInput:
    column = 'dummy'
    label = 'Dummy test field'

    choices = [
            ('AA', 'aa option'),
            ('BB', 'bb option'),
            ('CC', 'cc option'),
        ]


class DummyParams:

    def demog_fields(self):
        class DF:
            def field_by_name(self, name):
                return DummyField()
        return DF()

    def form_info(self, name):
        class FI:
            name = 'testform'
            label = 'Dummy form'
            version = 2
            def load(self):
                class Form:
                    class Columns:
                        def find_input(self, name):
                            return DummyInput()
                    columns = Columns()
                return Form()
            def tablename(self):
                return 'formtable'
        return FI()

class ReportFilterTermsTest(testcommon.SchemaTestCase):

    # Not tested
    #   DOBDemogFieldOps - relative dates tricky
    #   NamesDemogFieldOps - brings in fuzzyperson logic

    def exercise(self, term, field_ops, want_markup,
                 want_desc, want_xml, want_query, 
                 allow_negate=True, want_datefmt=None):
        term.params = DummyParams()
        term.field_ops = field_ops(term)
        self.assertEqual(term.field, DummyField.name)
        self.assertEqual(term.label(), DummyField.label)
        self.assertEqual(term.get_markup(), want_markup)
        self.assertEqual(term.allow_negate(), allow_negate)
        if term.form:
            self.assertEqual(term.form, 'testform')
            self.assertEqual(term.form_label(), 'Dummy form')
        else:
            self.assertEqual(term.form_label(), 'Demographics')
        self.assertEqual(term.desc(), want_desc)
        self.assertEqual(term.date_format(), want_datefmt)
        # XML
        f = StringIO()
        xmlgen = xmlwriter.XMLwriter(f)
        term.to_xml(xmlgen)
        got_xml = f.getvalue().replace('<?xml version="1.0"?>\n', '')
        self.assertEqual(got_xml, want_xml)
        # Query
        query = dbobj.ExprBuilder(globals.db.get_table('cases'), 'AND')
        term.query(query)
        got_query = query.build_expr()[0]
        self.assertEqual(got_query, want_query)

    def test_pattern_demog_term(self):
        # Pattern term
        term = PatternTerm('dummy')
        term.value = 'XX*'
        self.exercise(term, PatternDemogFieldOps, 'pattern',
                      want_desc="matching pattern 'XX*'",
                      want_xml='<term field="dummy" op="pattern">\n <value>XX*'
                               '</value>\n</term>\n',
                      want_query='(table.dummy ILIKE %s)')
        # Now try it negated
        term.negate = True
        self.exercise(term, PatternDemogFieldOps, 'pattern',
                      want_desc="not matching pattern 'XX*'",
                      want_xml='<term field="dummy" op="pattern" negate="yes">'
                               '\n <value>XX*</value>\n</term>\n',
                      want_query='(NOT (table.dummy ILIKE %s))')
        # And with multiple patterns
        term.value = 'XX*, YY*'
        self.exercise(term, PatternDemogFieldOps, 'pattern',
                      want_desc="not matching pattern 'XX*, YY*'",
                      want_xml='<term field="dummy" op="pattern" negate="yes">'
                               '\n <value>XX*, YY*</value>\n</term>\n',
                      want_query='(NOT ((table.dummy ILIKE %s OR table.dummy '
                                 'ILIKE %s)))')

    def test_pattern_form_term(self):
        term = PatternTerm('dummy', form='testform')
        term.value = 'XX*'
        self.exercise(term, PatternFormFieldOps, 'pattern',
                      want_desc="matching pattern 'XX*'",
                      want_xml='<term form="testform" field="dummy" '
                               'op="pattern">\n <value>XX*</value>\n</term>\n',
                      want_query='(formtable.dummy ILIKE %s)')
        term.negate = True
        self.exercise(term, PatternFormFieldOps, 'pattern',
                      want_desc="not matching pattern 'XX*'",
                      want_xml='<term form="testform" field="dummy" '
                               'op="pattern" negate="yes">\n '
                               '<value>XX*</value>\n</term>\n',
                      want_query='(NOT (formtable.dummy ILIKE %s))')

    def test_range_demog_term(self):
        # Range term, lower limit
        term = RangeTerm('dummy')
        term.from_value = 'XX'
        self.exercise(term, RangeDemogFieldOps, 'range',
                      want_desc="from XX (inclusive)",
                      want_xml='<term field="dummy" op="range">\n '
                               '<from inclusive="yes">XX</from>\n</term>\n',
                      want_query='(table.dummy >= %s)')
        # Add an upper limit
        term.to_value = 'YY'
        self.exercise(term, RangeDemogFieldOps, 'range',
                      want_desc="from XX (inclusive) to YY",
                      want_xml='<term field="dummy" op="range">\n '
                               '<from inclusive="yes">XX</from>\n '
                               '<to>YY</to>\n</term>\n',
                      want_query='(table.dummy >= %s AND table.dummy < %s)')
        # Negation
        term.negate = True
        self.exercise(term, RangeDemogFieldOps, 'range',
                      want_desc="not from XX (inclusive) to YY",
                      want_xml='<term field="dummy" op="range" negate="yes">\n '
                               '<from inclusive="yes">XX</from>\n '
                               '<to>YY</to>\n</term>\n',
                      want_query='(NOT (table.dummy >= %s AND table.dummy < %s))')

    def test_date_range_form_term(self):
        # Range term, lower limit
        term = RangeTerm('dummy', form='testform')
        term.from_value = '2009-5-1'
        term.incl_from = False
        self.exercise(term, DateRangeFormFieldOps, 'range',
                      want_datefmt='%d/%m/%Y',
                      want_desc="from 2009-5-1",
                      want_xml='<term form="testform" field="dummy" op="range">'
                               '\n <from>2009-05-01</from>\n</term>\n',
                      want_query='(formtable.dummy > %s)')
        # Add an upper limit
        term.to_value = '2010-6-1'
        term.incl_to = True
        self.exercise(term, DateRangeFormFieldOps, 'range',
                      want_datefmt='%d/%m/%Y',
                      want_desc="from 2009-5-1 to 2010-6-1 (inclusive)",
                      want_xml='<term form="testform" field="dummy" '
                               'op="range">\n <from>2009-05-01</from>\n '
                               '<to inclusive="yes">2010-06-01</to>\n</term>\n',
                      want_query='(formtable.dummy > %s AND '
                                 'formtable.dummy <= %s)')

    def test_in_demog_term(self):
        term = InTerm('dummy')
        term.values = ['AA', 'BB']
        self.exercise(term, InDemogFieldOps, 'checkboxes',
                      want_desc="is in aa option, bb option",
                      want_xml='<term field="dummy" op="in">\n <value>AA'
                               '</value>\n <value>BB</value>\n</term>\n',
                      want_query='(table.dummy IN (%s,%s))')
        term.values = ['?', 'AA', 'BB']
        self.exercise(term, InDemogFieldOps, 'checkboxes',
                      want_desc="is in ?, aa option, bb option",
                      want_xml='<term field="dummy" op="in">\n <value>?'
                               '</value>\n <value>AA</value>\n <value>BB'
                               '</value>\n</term>\n',
                      want_query='((table.dummy IS NULL OR table.dummy '
                                 'IN (%s,%s)))')
        term.values = ['AA']
        term.negate = True
        self.exercise(term, InDemogFieldOps, 'checkboxes',
                      want_desc="is not aa option",
                      want_xml='<term field="dummy" op="in" negate="yes">\n '
                               '<value>AA</value>\n</term>\n',
                      want_query='(NOT (table.dummy IN (%s)))')

    def test_in_choices_form_term(self):
        term = InTerm('dummy', form='testform')
        term.values = ['AA', 'BB']
        self.exercise(term, ChoicesFormFieldOps, 'checkboxes',
                      want_desc="is in aa option, bb option",
                      want_xml='<term form="testform" field="dummy" op="in">\n <value>AA</value>\n <value>BB</value>\n</term>\n',
                      want_query='(formtable.dummy IN (%s,%s))')

    def test_in_checkbox_form_term(self):
        term = InTerm('dummy', form='testform')
        term.values = ['AA', 'BB']
        self.exercise(term, CheckboxFormFieldOps, 'checkboxes',
                      want_desc="is in aa option, bb option",
                      want_xml='<term form="testform" field="dummy" op="in">\n <value>AA</value>\n <value>BB</value>\n</term>\n',
                      want_query='((formtable.dummyaa OR formtable.dummybb))')

    def test_select_deleted_term(self):
        term = SelectTerm('dummy')
        term.value = 'exclude'
        self.exercise(term, DeletedDemogFieldOps, 'select',
                      allow_negate=False,
                      want_desc="is Excluded",
                      want_xml='<term field="dummy" op="select">\n '
                               '<value>exclude</value>\n</term>\n',
                      want_query='(NOT cases.deleted)')
        term.value = 'both'
        self.exercise(term, DeletedDemogFieldOps, 'select',
                      allow_negate=False,
                      want_desc="is Included",
                      want_xml='<term field="dummy" op="select">\n '
                               '<value>both</value>\n</term>\n',
                      want_query='True')
        term.value = 'only'
        self.exercise(term, DeletedDemogFieldOps, 'select',
                      allow_negate=False,
                      want_desc="is Only deleted",
                      want_xml='<term field="dummy" op="select">\n '
                               '<value>only</value>\n</term>\n',
                      want_query='(cases.deleted)')

    def test_select_tag_term(self):
        term = SelectTerm('dummy')
        self.exercise(term, TagsDemogFieldOps, 'select',
                      want_desc="is None",
                      want_xml='<term field="dummy" op="select" />\n',
                      want_query='True')
        term.value = '1'
        self.exercise(term, TagsDemogFieldOps, 'select',
                      want_desc="is Tag",
                      want_xml='<term field="dummy" op="select">\n <value>1'
                               '</value>\n</term>\n',
                      want_query='(cases.case_id IN (SELECT case_id FROM '
                                 'case_tags JOIN tags USING (tag_id) '
                                 'WHERE (tag ILIKE %s)))')

    def test_caseset_term(self):
        term = CasesetTerm([1,2,3,9], 'Four cases', field='dummy')
        self.exercise(term, CasesetDemogFieldOps, 'caseset',
                      want_desc="Case set: Four cases (4 cases)",
                      want_xml='<term field="dummy" op="caseset" caseset="Four '
                               'cases">\n <commalist>1,2,3,9</commalist>\n'
                               '</term>\n',
                      want_query='(case_id IN (%s,%s,%s,%s))')


class FilterAdderTest(testcommon.AppTestCase):

    want_groups = [
        ('demog', 'Demographics'),
        ('andsubexpr', 'AND Subexpression'),
        ('orsubexpr', 'OR Subexpression'),
        ('sars_exposure', 'Exposure History (SARS)'),
        ('hospital_admit', 'Hospital admission')
    ]

    want_avail = [
        ('demog', [
            ('', '- Choose filter -'),
            ('case_assignment', 'Case Assignment'),
            ('data_src', 'Data source'),
            ('DOB', 'Date of birth/Age'),
            ('deleted', 'Deleted'),
            ('delete_timestamp', 'Deletion date'),
            ('delete_reason', 'Deletion reason'),
            ('fax_phone', 'Fax'),
            ('given_names', 'Given names'),
            ('home_phone', 'Home phone'),
            ('interpreter_req', 'Interpreter'),
            ('local_case_id', 'Local ID'),
            ('locality', 'Locality/Suburb'),
            ('mobile_phone', 'Mobile phone'),
            ('notification_datetime', 'Notification Date'),
            ('onset_datetime', 'Onset Date'),
            ('passport_country', 'Passport country/Nationality'),
            ('passport_number', 'Passport number'),
            ('postcode', 'Postcode'),
            ('sex', 'Sex'),
            ('state', 'State'),
            ('case_status', 'Status'),
            ('street_address', 'Street address'),
            ('surname', 'Surname'),
            ('case_id', 'System ID'),
            ('tags', 'Tags'),
            ('work_phone', 'Work/School phone'),
        ]),
        ('sars_exposure', [
            ('', '- Choose filter -'),
            ('contact_duration', 'Contact duration (hours)'),
            ('close_contact', 'Contact with case'),
            ('contact_date_first', 'Date of first contact'),
            ('contact_favourite_food', 'Favourite foods'),
            ('contact_date_last', 'Most recent contact'),
        ]),
        ('hospital_admit', [
            ('', '- Choose filter -'),
            ('admission_aerosol', 'admission_aerosol'),
            ('admission_aerosol_detail', 'admission_aerosol_detail'),
            ('admission_co_morb', 'admission_co_morb'),
            ('admission_hospital', 'admission_hospital'),
            ('admission_icu', 'admission_icu'),
            ('admission_icu_stay', 'admission_icu_stay'),
            ('admission_isolation', 'admission_isolation'),
            ('admission_mech_vent', 'admission_mech_vent'),
            ('admission_stay', 'admission_stay'),
            ('admission_date', 'admitted'),
            ('admission_discharge_date', 'discharged'),
            ('admission_hospitalised', 'hospitalised'),
        ])]

    def test_adder(self):
        params = reports.new_report(2)
        self.assertEqual(params.filter.children, [])
        # Test adder cancel
        adder = params.filter_adder(params.filter)
        adder.abort()
        self.assertEqual(params.filter.children, [])
        # Test add demog field
        adder = params.filter_adder(params.filter)
        self.assertEqual(adder.groups(), self.want_groups)
        available = [(group.name, group.available_filters())
                     for group in adder if group.has_field]
        self.assertEqual(available, self.want_avail)
        adder.group = 'demog'
        self.failIf(adder.is_complete())
        self.failUnless(adder.has_field())
        self.assertEqual(adder.fields(), self.want_avail[0][1])
        adder.field = 'surname'
        self.failIf(adder.is_complete())
        self.assertEqual(adder.field_ops(), ['pattern', 'phonetic'])
        adder.op = 'pattern'
        self.failUnless(adder.is_complete())
        surname = adder.add()
        self.assertEqual(params.filter.children, [surname])
        # Test add "OR" expr
        adder = params.filter_adder(params.filter)
        adder.group = 'orsubexpr'
        self.failIf(adder.has_field())
        self.failUnless(adder.is_complete())
        orexpr = adder.add()
        self.assertEqual(params.filter.children, [surname, orexpr])
        # Test subexpr add
        adder = params.filter_adder(orexpr)
        adder.group = 'sars_exposure'
        self.failIf(adder.is_complete())
        self.failUnless(adder.has_field())
        self.assertEqual(adder.fields(), self.want_avail[1][1])
        adder.field = 'close_contact'
        self.failUnless(adder.is_complete())
        ccontact = adder.add()
        self.assertEqual(params.filter.children, [surname, orexpr])
        self.assertEqual(orexpr.children, [ccontact])
        # While we are here, test deletion (and implicit trimming)
        params.del_filter(ccontact)
        self.assertEqual(params.filter.children, [surname])

    want_query = (
        'SELECT cases.* FROM cases '
         'WHERE (cases.case_id IN '
           '(SELECT cases.case_id FROM cases '
             'JOIN persons USING (person_id) '
             'LEFT JOIN (SELECT case_id, form_hospital_admit_00001.* '
                    'FROM form_hospital_admit_00001 '
                    'JOIN case_form_summary USING (summary_id) '
                    'WHERE NOT deleted) '
                'AS form_hospital_admit_00001 USING (case_id) '
             'WHERE (syndrome_id = %s '
              'AND (cases.case_status IN (%s,%s) '
               'OR form_hospital_admit_00001.admission_hospitalised IN (%s)))))'
        )

    def test_query(self):
        params = reports.new_report(2)
        params.caseset_filter([1,2,3,9], 'Four cases')
        f_status = params.make_term(op='in', field='case_status', 
                                    values=['confirmed', 'suspected'])
        f_hosp = params.make_term(op='in', field='admission_hospitalised', 
                                  form='hospital_admit', values=['True'])
        f_or = params.make_term(op='or')
        params.add_filter(f_or)
        f_or.add_filter(f_status)
        f_or.add_filter(f_hosp)
        query = globals.db.query('cases')
        params.filter_query(query)
        got_query = query.build_expr()[0]
        self.assertEqual(got_query, self.want_query)


class FiltersWalkTest(testcommon.TestCase):
    
    def test_yield_nodes(self):
        class Node: pass
        root = Node()
        root.children = [Node(), Node()]
        root.children[0].children = [Node(), Node()]
        tokens = [(t, p) for t, p, n in reports.reportfilters.yield_nodes(root)]
        self.assertEqual(tokens,
            [('open', ''),
              ('open', '0'),
               ('clause', '0.0'),
               ('clause', '0.1'),
              ('close', '0'),
               ('clause', '1'),
              ('close', ''),
            ])
        root = Node()
        root.children = [Node(), Node()]
        root.children[1].children = [Node(), Node()]
        tokens = [(t, p) for t, p, n in reports.reportfilters.yield_nodes(root)]
        self.assertEqual(tokens, 
            [('open', ''),
              ('clause', '0'),
              ('open', '1'),
               ('clause', '1.0'),
               ('clause', '1.1'),
              ('close', '1'),
             ('close', '')
            ])
