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
import sys, os

modpath = os.path.normpath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, modpath)

all_tests = [
    'tests.parse_addr.suite',
    'tests.datetimetest.suite',
    'tests.age',
    'tests.person',
    'tests.wikiformatting',
    'tests.tuplestruct.suite',
    'tests.dbobj.suite',
    'tests.xmlparse.suite',
    'tests.form.suite',
    'tests.formsave.suite',
    'tests.formlib.suite',
    'tests.dataimp.xmlsaveload',
    'tests.dataimp.datasrc',
    'tests.dataimp.editor',
    'tests.dataimp.dataimp',
    'tests.searchacl.suite',
    'tests.export.suite',
    'tests.adminformedit.suite',
    'tests.demogfields.suite',
    'tests.reports.filters',
    'tests.reports.orderby',
    'tests.reports.columns',
    'tests.reports.savenload',
    'tests.reports.linereport',
    'tests.reports.export',
    'tests.reports.crosstab',
    'tests.persondupe.suite',
]

def suite():
    return unittest.defaultTestLoader.loadTestsFromNames(all_tests)

if __name__ == '__main__':
    try:
        i = sys.argv.index('-d')
    except ValueError:
        pass
    else:
        # Allow test database (dsn) to be specified
        import tests.testcommon
        tests.testcommon.set_dsn(sys.argv[i+1])
        del sys.argv[i:i+2]
    unittest.main(module=None, defaultTest='__main__.suite') 
