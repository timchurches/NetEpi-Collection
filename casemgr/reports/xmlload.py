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

import sys
from cocklebur import xmlparse, utils

from casemgr.reports import report, reportfilters
from casemgr.reports.common import *

class OrderingXMLParse(xmlparse.XMLParse):

    root_tag = 'ordering'

    class OrderBy(xmlparse.Node):
        permit_attrs = (
            'column', 'direction',
        )

    class Ordering(xmlparse.Node):
        __slots__ = 'params',
        subtags = (
            'orderby',
        )
        def start_element(self, parent):
            self.params = parent.params

        def end_child(self, child):
            self.params.add_order(**child.attrs)


class ColumnsXMLParse(xmlparse.XMLParse):

    root_tag = 'groups'

    class Column(xmlparse.Node):
        permit_attrs = (
            'name', 'label', 
        )

    class Group(xmlparse.ContainerNode):
        permit_attrs = (
            'type', 'form', 'label', 
        )
        subtags = (
            'column',
        )
        def end_element(self, parent):
            group = parent.params.add_group(**self.attrs)
            for child in self.children:
                group.add(**child.attrs)

    class Groups(xmlparse.Node):
        __slots__ = 'params',
        subtags = (
            'group',
        )
        def start_element(self, parent):
            self.params = parent.params



class FiltersXMLParse(xmlparse.XMLParse):

    root_tag = 'filter'

    class Value(xmlparse.Node):

        def end_element(self, parent):
            if parent.term.op == 'in':
                parent.term.values.append(self.get_text())
            else:
                parent.term.value = self.get_text()

    class Commalist(xmlparse.Node):

        def end_element(self, parent):
            parent.term.values = utils.commasplit(self.get_text())

    class From(xmlparse.Node):
        permit_attrs = (
            'inclusive:bool', 
        )
        def end_element(self, parent):
            parent.term.from_value = self.get_text()
            if 'inclusive' in self.attrs:
                parent.term.incl_from = self.attrs['inclusive']

    class To(xmlparse.Node):
        permit_attrs = (
            'inclusive:bool', 
        )
        def end_element(self, parent):
            parent.term.to_value = self.get_text()
            if 'inclusive' in self.attrs:
                parent.term.incl_to = self.attrs['inclusive']

    class Term(xmlparse.Node):
        __slots__ = 'term',
        permit_attrs = (
            'field', 'form', 'op', 'caseset', 'negate:bool', 'phonetic:bool',
        )
        subtags = (
            'value', 'commalist', 'from', 'to',
        )

        def start_element(self, parent):
            self.term = reportfilters.make_term(**self.attrs)
            parent.add_filter(self.term)


    class Filter(xmlparse.Node):
        __slots__ = 'filter',
        permit_attrs = (
            'op',
        )
        subtags = (
            'term', 'filter',
        )
        def start_element(self, parent):
            op = self.attrs.get('op', 'and')
            self.filter = reportfilters.make_term(op)
            parent.add_filter(self.filter)

        def add_filter(self, node):
            self.filter.add_filter(node)


class CrossTabXMLParse(xmlparse.XMLParse):

    root_tag = 'crosstab'

    class Axis(xmlparse.Node):
        permit_attrs = (
            'name', 'type', 'form', 'field', 
        )
        def end_element(self, parent):
            parent.params.set_axis(**self.attrs)

    class CrossTab(xmlparse.Node):
        __slots__ = 'params',
        permit_attrs = (
            'include_empty_rowsncols:bool', 'include_empty_pages:bool', 
        )
        subtags = (
            'axis',
        )
        def start_element(self, parent):
            self.params = parent.params

        def end_element(self, parent):
            parent.set('empty_rowsncols', 
                self.attrs.get('include_empty_rowsncols'))
            parent.set('empty_pages', 
                self.attrs.get('include_empty_pages'))


class EpiCurveXMLParse(xmlparse.XMLParse):
        
    root_tag = 'epicurve'

    class Suppress(xmlparse.Node):

        def end_element(self, parent):
            parent.params.ts_stack_suppress.append(self.get_text())

    class Dates(xmlparse.Node):
        required_attrs = (
            'field',
        )
        permit_attrs = (
            'form', 
        )
        def start_element(self, parent):
            form = self.attrs.get('form', '')
            parent.params.set_join(form)
            field = '%s:%s' % (form, self.attrs['field'])
            if parent.params.ts_bincol:
                parent.params.ts_bincol2 = field
            else:
                parent.params.ts_bincol = field

    class Stacking(xmlparse.Node):
        __slots__ = 'params',
        required_attrs = (
            'field',
        )
        permit_attrs = (
            'form', 'ratios:bool',
        )
        subtags = (
            'suppress',
        )
        def start_element(self, parent):
            self.params = parent.params
            form = self.attrs.get('form', '')
            self.params.set_join(form)
            self.params.ts_stacking = '%s:%s' % (form, self.attrs['field'])
            self.params.ts_stack_ratios = self.attrs.get('ratios', False)
            self.params.ts_stack_suppress = []

    class EpiCurve(xmlparse.Node):
        __slots__ = 'params',
        permit_attrs = (
            'join', 'format', 'nbins', 'missing_forms:bool', 
        )
        subtags = (
            'dates', 'stacking',
        )
        def start_element(self, parent):
            self.params = parent.params
            self.params.ts_bincol = self.params.ts_bincol2 = ''
            parent.set('ts_outfmt', self.attrs.get('format'))
            parent.set('ts_nbins', self.attrs.get('nbins'))


class ContactVisXMLParse(xmlparse.XMLParse):
        
    root_tag = 'contactvis'

    class ContactVis(xmlparse.Node):
        permit_attrs = (
            'format', 'labelwith', 'vismode', 
        )
        def end_element(self, parent):
            parent.set('outputtype', self.attrs.get('format'))
            parent.set('labelwith', self.attrs.get('labelwith'))
            parent.set('vismode', self.attrs.get('vismode'))


class ReportXMLParse(ColumnsXMLParse,
                     FiltersXMLParse,
                     OrderingXMLParse, 
                     CrossTabXMLParse,
                     EpiCurveXMLParse,
                     ContactVisXMLParse,
                     xmlparse.XMLParse):

    root_tag = 'report'

    class Header(xmlparse.SetAttrNode):
        attr = 'header'

    class Syndrome(xmlparse.SetAttrNode):
        attr = 'syndrome'

    class Preamble(xmlparse.SetAttrNode):
        attr = 'preamble'

    class Footer(xmlparse.SetAttrNode):
        attr = 'footer'

    class Export(xmlparse.Node):
        permit_attrs = (
            'strip_newlines:bool', 'column_labels', 'row_type', 
        )
        def end_element(self, parent):
            parent.set('export_strip_newlines', 
                                        str(self.attrs.get('strip_newlines')))
            parent.set('export_column_labels', self.attrs.get('column_labels'))
            parent.set('export_row_type', self.attrs.get('row_type'))

    class FormDep(xmlparse.Node):
        permit_attrs = (
            'name', 'version:int', 'label',
        )
        def end_element(self, parent):
            parent.params.saved_formdeps.append(self.attrs)

    class Report(xmlparse.Node):
        __slots__ = 'params',
        required_attrs = (
            'type', 'name',
        )
        subtags = (
            'ordering', 'header', 'syndrome', 'preamble', 'footer', 'export',
            'contactvis', 'crosstab', 'epicurve', 'groups', 'filter',
            'formdep',
        )
        def set(self, attr, value):
            if value is not None:
                setattr(self.params, attr, value)

        def add_filter(self, node):
            self.params.add_filter(node)

        def start_element(self, parent):
            # XXX syndrome_id
            ctor = report.get_report_ctor(self.attrs['type'])
            self.params = ctor(None)

        def end_element(self, parent):
            self.params.label = self.attrs['name']
            self.set('header', self.attrs.get('header'))
            self.set('preamble', self.attrs.get('preamble'))
            self.set('footer', self.attrs.get('footer'))


def xmlload(f):
    try:
        return ReportXMLParse().parse(f).params
    except xmlparse.ParseError, e:
        raise ReportParseError, e, sys.exc_info()[2]
