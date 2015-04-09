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
"""
Quick and somewhat dirty regression tests for data export code.

This could form the basis for more general unittests of the casemgr
machinery, because it populates a skeleton casemgr test database.

$Id: export.py 4432 2011-03-03 01:08:38Z andrewm $
$Source$
"""
import os
import unittest
import time
import csv
import cStringIO
import itertools

thisdir = os.path.dirname(__file__)
exportdatadir = os.path.join(thisdir, 'data', 'export')

from cocklebur import dbobj
#dbobj.execute_debug(1)

import testcommon

import casemgr
from casemgr import globals
from casemgr.dataexport import CaseExporter


def cellname(row, col):
    "Generate spreadsheet-style row and col addressing"
    label = ''
    while not label or col:
        col, mod = divmod(col, 26)
        label = chr(65 + mod) + label
    return label + str(row+1)

def csv_cmp(a, b):
    fa = csv.reader(open(a, 'rb'))
    fb = csv.reader(open(b, 'rb'))
    res = []
    for row, (rowa, rowb) in enumerate(map(None, fa, fb)):
        for col, (cola, colb) in enumerate(map(None, rowa, rowb)):
            if cola != colb:
                res.append('%s %s != %s' % (cellname(row, col), cola, colb))
    return '\n'.join(res)


class ExportTest(testcommon.AppTestCase):

    def _test(self, result_file, **kwargs):
        credentials = testcommon.DummyCredentials()
        syndrome = testcommon.DummySyndrome()
        exporter = CaseExporter(credentials, 2, **kwargs)
        self.assertEqual([form.label for form in exporter.forms], 
                         ['sars_exposure', 'hospital_admit'])
        self.assertEqual(len(exporter.export_cases), 3)
        ids = [ec.id for ec in exporter.export_cases.cases_in_order]
        self.assertEqual(ids, [1, 2, 5])
        cwd = os.getcwd()
        try:
            f = open('result.csv', 'wb')
            os.chdir(os.path.join(os.path.dirname(__file__), '..', 'casemgr'))
            exporter.csv_write(['sars_exposure'], f)
            os.chdir(cwd)
            f.flush()
            res = csv_cmp('result.csv', 
                          os.path.join(exportdatadir, result_file))
            self.failIf(res, '\n'+res)
        finally:
            os.chdir(cwd)
            os.unlink('result.csv')

    def test_classic(self):
        self._test('result.csv', format='classic')

    def test_doha(self):
        self._test('doharesult.csv', format='doha')

    def test_form(self):
        self._test('formresult.csv', format='form')


class Suite(unittest.TestSuite):
    test_list = (
        'test_classic',
        'test_doha',
        'test_form',
    )

    def __init__(self):
        unittest.TestSuite.__init__(self, map(ExportTest, self.test_list))


def suite():
    return Suite()

if __name__ == '__main__':
    unittest.main()

