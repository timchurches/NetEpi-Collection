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

from cocklebur import introspect, xmlwriter

import reportfilters, reportcolumns, reportcrosstab


class OrderParam:

    pass


class OrderbyParamsMixin:

    def _to_xml(self, xmlgen, curnode):
        if self.order_by:
            xmlgen.push('ordering')
            for ob in self.order_by:
                e = xmlgen.push('orderby')
                e.attr('column', ob.col)
                e.attr('direction', ob.rev)
                xmlgen.pop()
            xmlgen.pop()



class ReportParamsBase:

    report_type = None
    label = None

    def forms_used(self):
        used = set()
        introspect.callall(self, '_forms_used', used)
        return used

    def form_deps(self, xmlgen, form_info):
        for form in self.forms_used():
            name, label, version = form_info[form.lower()]
            e = xmlgen.push('formdep')
            e.attr('name', name)
            e.attr('version', version)
            e.attr('label', label)
            xmlgen.pop()

    def to_xml(self, xmlgen, form_info):
        curnode = xmlgen.push('report')
        curnode.attr('type', self.report_type)
        curnode.attr('name', self.label)
        xmlgen.pushtext('header', self.header)
        self.form_deps(xmlgen, form_info)
        introspect.callall(self, '_to_xml', xmlgen, curnode)
        xmlgen.pop()

    def xmlsave(self, f, form_info):
        xmlgen = xmlwriter.XMLwriter(f)
        self.to_xml(xmlgen, form_info)


class LineReportParams(
                reportfilters.FilterParamsMixin, 
                reportcolumns.OutcolsParamsMixin, 
                OrderbyParamsMixin,
                ReportParamsBase):

    report_type = 'line'

ReportParams = LineReportParams


class CrosstabReportParams(
                reportcrosstab.CrosstabParams,
                reportfilters.FilterParamsMixin,
                ReportParamsBase):

    report_type = 'crosstab'
