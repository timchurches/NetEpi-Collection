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

from cocklebur import datetime

class DemogFilterBase(object):

    value = None
    column = None
    negate = False
    op = None

    def attr_to_xml(self, node):
        pass

    def value_to_xml(self, xmlgen):
        v = xmlgen.push('value')
        v.text(self.value)
        xmlgen.pop()

    def to_xml(self, xmlgen):
        e = xmlgen.push('term')
        e.attr('field', self.name)
        e.attr('op', self.op)
        if self.negate:
            e.attr('negate', 'yes')
        self.attr_to_xml(e)
        self.value_to_xml(xmlgen)
        xmlgen.pop()


class PatternDemogFilter(DemogFilterBase):

    op = 'pattern'


class RangeFilterMixin(object):

    op = 'range'
    from_value = ''
    to_value = ''
    incl_from = True
    incl_to = False
    iso_fmt = None

    def parse(self, v):
        return v

    def value_to_xml(self, xmlgen):
        if self.from_value:
            se = xmlgen.push('from')
            if self.incl_from:
                se.attr('inclusive', 'yes')
            value = self.from_value
            if self.iso_fmt:
                value = self.parse(value).strftime(self.iso_fmt)
            se.text(value)
            xmlgen.pop()
        if self.to_value:
            se = xmlgen.push('to')
            value = self.to_value
            if self.iso_fmt:
                value = self.parse(value).strftime(self.iso_fmt)
            se.text(value)
            if self.incl_to:
                se.attr('inclusive', 'yes')
            xmlgen.pop()


class DateRangeFilterMixin(RangeFilterMixin):

    iso_fmt = '%Y-%m-%d %H:%M:%S'

    def parse(self, v):
        try:
            return datetime.parse_discrete(v, past=True).mx()
        except datetime.Error, e:
            raise Error(str(e))


class RangeDemogFilter(RangeFilterMixin, DemogFilterBase):

    pass


class DateRangeDemogFilter(DateRangeFilterMixin, DemogFilterBase):

    pass


class DOBDemogFilter(DateRangeDemogFilter):

    pass


class InDemogFilter(DemogFilterBase):

    op = 'in'

    value = []

    def value_to_xml(self, xmlgen):
        for value in self.value:
            v = xmlgen.push('value')
            v.text(value)
            xmlgen.pop()


class CommalistDemogFilter(DemogFilterBase):
    
    op = 'pattern'


class PhoneticDemogFilter(PatternDemogFilter):

    phonetic = True

    def to_xml(self, xmlgen):
        if str(self.phonetic) == 'True':
            self.op = 'phonetic'
        else:
            self.op = 'pattern'
        PatternDemogFilter.to_xml(self, xmlgen)


class DeletedDemogFilter(DemogFilterBase):

    op = 'select'
    value = 'False'

    fixup_map = {
        'True': 'exclude',
        '': 'both',
        'False': 'only',
    }

    def to_xml(self, xmlgen):
        self.value = self.fixup_map.get(self.value, self.value)
        DemogFilterBase.to_xml(self, xmlgen)


class TagsDemogFilter(DemogFilterBase):

    op = 'in'

    def value_to_xml(self, xmlgen):
        if self.value:
            for value in self.value.split(','):
                value = value.strip()
                if value:
                    v = xmlgen.push('value')
                    v.text(value)
                    xmlgen.pop()


class FormFilterBase:

    negate = False

    def attr_to_xml(self, node):
        pass

    def value_to_xml(self, xmlgen):
        v = xmlgen.push('value')
        v.text(self.value)
        xmlgen.pop()

    def to_xml(self, xmlgen):
        e = xmlgen.push('term')
        e.attr('form', self.group)
        e.attr('field', self.name)
        e.attr('op', self.op)
        if self.negate:
            e.attr('negate', 'yes')
        self.attr_to_xml(e)
        self.value_to_xml(xmlgen)
        xmlgen.pop()


class PatternFormFilter(FormFilterBase):

    op = 'pattern'


class RangeFormFilter(RangeFilterMixin, FormFilterBase):

    pass


class DateRangeFormFilter(DateRangeFilterMixin, FormFilterBase):

    iso_fmt = '%Y-%m-%d'


class DateTimeRangeFormFilter(DateRangeFilterMixin, FormFilterBase):

    pass


class ChoicesFormFilter(FormFilterBase):

    op = 'in'
    value = []

    def value_to_xml(self, xmlgen):
        for value in self.value:
            v = xmlgen.push('value')
            v.text(value)
            xmlgen.pop()


class CheckboxFormFilter(ChoicesFormFilter):

    pass


class FilterParamsMixin:

    def _forms_used(self, used):
        for filter in self.filters:
            if isinstance(filter, FormFilterBase):
                used.add(filter.group)

    def _to_xml(self, xmlgen, curnode):
        if self.filters:
            e = xmlgen.push('filter')
            e.attr('op', 'AND')
            for filter in self.filters:
                filter.to_xml(xmlgen)
            xmlgen.pop()
