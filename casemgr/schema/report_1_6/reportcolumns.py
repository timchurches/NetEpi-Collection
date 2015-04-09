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

class ReportCol:

    def to_xml(self, xmlgen):
        e = xmlgen.push('column')
        e.attr('name', self.name)
        e.attr('label', self.label)
        xmlgen.pop()
    

class ReportColsBase(list):

    form_name = None


class DemogCols(ReportColsBase):

    def to_xml(self, xmlgen):
        e = xmlgen.push('group')
        e.attr('type', 'demog')
        e.attr('label', self.label)
        for c in self:
            c.to_xml(xmlgen)
        xmlgen.pop()


class FormCols(ReportColsBase):

    def to_xml(self, xmlgen):
        e = xmlgen.push('group')
        e.attr('type', 'form')
        e.attr('form', self.form_name)
        e.attr('label', self.label)
        for c in self:
            c.to_xml(xmlgen)
        xmlgen.pop()


class OutcolsParamsMixin:

    def _forms_used(self, used):
        for outgroup in self.outgroups:
            if outgroup.form_name:
                used.add(outgroup.form_name)

    def _to_xml(self, xmlgen, curnode):
        xmlgen.push('groups')
        for outgroup in self.outgroups:
            outgroup.to_xml(xmlgen)
        xmlgen.pop()
