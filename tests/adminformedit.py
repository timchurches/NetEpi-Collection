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
import sys
import unittest

from cocklebur.form_ui.xmlsave import xmlsave
from cocklebur.form_ui.xmlload import xmlload
from casemgr.admin import formedit

thisdir = os.path.dirname(__file__)
formdir = os.path.join(thisdir, 'data', 'adminformedit')

class Case(unittest.TestCase):
    def load(self, version):
        f = open(os.path.join(formdir, 'test%s.form' % version), 'r')
        try:
            return xmlload(f)
        finally:
            f.close()

    def save(self, form, version):
        f = open(os.path.join(formdir, 'test%s.form' % version), 'w')
        try:
            return xmlsave(f, form)
        finally:
            f.close()

    def runTest(self):
        # Load a form, turn it into a editable form and back into a form then
        # check we still have an equivilent form.
        form = self.load(0)
        fe = formedit.Root(form)
        self.assertEqual(form, fe.to_form())

        # Add a new section
        se = fe.new_section('E2')
        se.node.text = 'New section'
        self.assertEqual(self.load(1), fe.to_form())

        # Copy new section - should have no effect
        cut_buf = fe.copy('E2')
        self.assertEqual(self.load(1), fe.to_form())

        # Cut the new section and paste it back to the same place
        cut_buf = fe.cut('E2')
        #xmlsave(sys.stdout, cut_buf)
        fe.paste('E2', cut_buf)
        self.assertEqual(self.load(1), fe.to_form())

        # Cut and paste before the previous question
        cut_buf = fe.cut('E2')
        fe.paste('E1', cut_buf)
        self.assertEqual(self.load(2), fe.to_form())

        # Cut the section again and paste it inside the first section
        cut_buf = fe.cut('E1')
        fe.paste('E0_2', cut_buf)
        self.assertEqual(self.load(3), fe.to_form())

        # Cut the section and paste it at the start of the form
        cut_buf = fe.cut('E0_2')
        fe.paste('E0', cut_buf)
        self.assertEqual(self.load(4), fe.to_form())

        # Duplicate the second section
        cut_buf = fe.copy('E1')
        fe.paste('E3', cut_buf)
        self.assertEqual(self.load(5), fe.to_form())


def suite():
    return Case()

if __name__ == '__main__':
    unittest.main(defaultTest='suite')


