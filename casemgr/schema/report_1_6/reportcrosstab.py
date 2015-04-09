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

###############################################################################
# NOTE - these are dummy implementations of the report classes to allow pre-1.7
# report pickles to be loaded and converted to XML.
###############################################################################

class CrosstabAxisParams:

    def to_xml(self, xmlgen, name):
        e = xmlgen.push('axis')
        e.attr('name', name)
        if self.form_name:
            e.attr('type', 'form')
            e.attr('form', self.form_name)
        else:
            e.attr('type', 'demog')
        e.attr('field', self.field)
        xmlgen.pop()


class CrosstabParams:

    def _forms_used(self, used):
        for axis in (self.row, self.col):
            if axis.form_name:
                used.add(axis.form_name)

    def _to_xml(self, xmlgen, curnode):
        e = xmlgen.push('crosstab')
        self.row.to_xml(xmlgen, 'row')
        self.col.to_xml(xmlgen, 'column')
        xmlgen.pop()
