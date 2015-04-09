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

import os
import shutil
import unittest
from cStringIO import StringIO

from casemgr.dataimp import datasrc
from casemgr.dataimp.xmlload import xmlload

import config

data = '''\
surname,case_status
blogs,confirmed
smith,confirmed
jones,suspected
'''

named_rules = '''\
<?xml version="1.0"?>
<importrules name="test" mode="named" encoding="utf-8" fieldsep="," srclabel="import" conflicts="ignore">
</importrules>
'''

positional_rules = '''\
<?xml version="1.0"?>
<importrules name="test" mode="positional" encoding="utf-8" fieldsep="," srclabel="import" conflicts="ignore">
</importrules>
'''

class DataSrcTest(unittest.TestCase):

    scratchdir = os.path.join(os.path.dirname(__file__), 'scratch')

    def setUp(self):
        config.scratchdir = self.scratchdir
        os.mkdir(config.scratchdir)

    def tearDown(self):
        shutil.rmtree(self.scratchdir)

    def test_null_src(self):
        self.failIf(bool(datasrc.NullDataImpSrc))
        self.assertEqual(datasrc.NullDataImpSrc.preview.colvalues('x'), None)
        self.assertEqual(datasrc.NullDataImpSrc.preview.colpreview('x'), [])
        datasrc.NullDataImpSrc.release()
        self.failIf(datasrc.DataImpSrc('foo', StringIO()))

    def test_datasrc_named(self):
        rules = xmlload(StringIO(named_rules))
        f = StringIO(data)
        src = datasrc.DataImpSrc('foo', f)
        self.assertEqual(src.size, len(data))
        # Preview
        src.update_preview(rules)
        self.assertEqual(src.preview.n_cols, 2)
        self.assertEqual(src.preview.n_rows, 3)
        self.assertEqual(src.preview.col_names, ['surname', 'case_status'])
        self.assertEqual(len(src.preview.rows), 3)
        self.assertEqual(src.preview.rows, [
            ['blogs', 'confirmed'], 
            ['smith', 'confirmed'], 
            ['jones', 'suspected']])
        self.assertEqual(src.preview.colvalues('case_status'), 
                        ['confirmed', 'suspected'])
        self.assertEqual(src.preview.colpreview('surname'), 
                        ['blogs', 'smith', 'jones'])
        self.assertEqual(src.preview.colpreview('case_status'), 
                        ['confirmed', 'confirmed', 'suspected'])
        src.release()

    def test_datasrc_positional(self):
        rules = xmlload(StringIO(named_rules))
        rules.mode = 'positional'
        f = StringIO(data)
        src = datasrc.DataImpSrc('foo', f)
        self.assertEqual(src.size, len(data))
        # Preview
        src.update_preview(rules)
        self.assertEqual(src.preview.n_cols, 2)
        self.assertEqual(src.preview.n_rows, 4)
        self.assertEqual(src.preview.col_names, ['1', '2'])
        self.assertEqual(len(src.preview.rows), 4)
        self.assertEqual(src.preview.rows, [
            ['surname', 'case_status'], 
            ['blogs', 'confirmed'], 
            ['smith', 'confirmed'], 
            ['jones', 'suspected']])
        self.assertEqual(src.preview.colvalues('2'), 
                        ['case_status', 'confirmed', 'suspected'])
        self.assertEqual(src.preview.colpreview('1'), 
                        ['surname', 'blogs', 'smith', 'jones'])
        self.assertEqual(src.preview.colpreview('2'), 
                        ['case_status', 'confirmed', 'confirmed', 'suspected'])
        src.release()
