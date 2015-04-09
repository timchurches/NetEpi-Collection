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
try:
    set
except NameError:
    from sets import Set as set

from cocklebur import introspect, template
from casemgr import globals, demogfields, caseaccess, syndrome, messages
from casemgr.reports import reportfilters, reportcolumns, linereport, \
                            epicurve, contactvis, store, crosstab, export
from casemgr.reports.common import *

import config

class OrderParam:

    def __init__(self, column='', direction='asc'):
        self.col = column
        self.rev = direction


class OrderbyParamsMixin:

    show_orderby = True

    rev_options = [
        ('asc', 'Ascending'),
        ('desc', 'Descending'),
    ]

    def init(self):
        self.order_by = []

    def add_order(self, **kw):
        self.order_by.append(OrderParam(**kw))

    def del_order(self, index):
        del self.order_by[index]

    def query_order(self):
        f = self.demog_fields().field_by_name
        return ','.join(['%s %s' % (f(o.col).field_result, o.rev) 
                         for o in self.order_by
                         if o.col])

    def order_cols(self): 
        avail_cols = []
        for f in self.demog_fields('report'):
            if f.name != 'case_definition' and getattr(f, 'field_result', None):
                avail_cols.append((f.name, f.label))
        return avail_cols

    def _to_xml(self, xmlgen, curnode):
        if self.order_by:
            xmlgen.push('ordering')
            for ob in self.order_by:
                e = xmlgen.push('orderby')
                e.attr('column', ob.col)
                e.attr('direction', ob.rev)
                xmlgen.pop()
            xmlgen.pop()


class FormDependancyMixin:

    def init(self):
        self.saved_formdeps = []

    def _check(self, msgs):
        for saved_info in self.saved_formdeps:
            info = self.form_info(saved_info['name'])
            if info is None:
                msgs.msg('err', 'Form "%s" is no longer available - check '
                                'report parameters' % saved_info['label'])
            elif info.version != saved_info['version']:
                msgs.msg('warn', 'Form "%s" has been updated - check report '
                                 'parameters (report version %r, now '
                                 'version %r)' % (saved_info['label'], 
                                    saved_info['version'], info.version))

    def _to_xml(self, xmlgen, curnode):
        for form in self.forms_used():
            info = self.form_info(form)
            e = xmlgen.push('formdep')
            e.attr('name', info.name)
            e.attr('version', info.version)
            e.attr('label', info.label)
            xmlgen.pop()


class ReportParamsBase:

    report_type = None
    type_label = None
    header = None
    order_by = None

    show_filters = False
    show_orderby = False
    show_columns = False
    show_axes = False
    show_epicurve = False
    show_contactvis = False
    show_headfoot = False

    def __init__(self, syndrome_id):
        self.syndrome_id = syndrome_id
        introspect.callall(self, 'init')

    def expand(self, cred, name):
        assert name in ('header', 'preamble', 'footer')
        synd = syndrome.syndromes[self.syndrome_id]
        value = getattr(self, name)
        value = template.expand_template(value, 
                                         username=cred.user.username,
                                         fullname=cred.user.fullname,
                                         role=cred.unit.name,
                                         unit=cred.unit.name,
                                         syndrome=synd.name,
                                         syndrome_id=synd.syndrome_id,
                                         syndrome_name=synd.name,
                                         syndrome_desc=synd.description)
        return value

    def change_type(self, report_type, msgs=None):
        report_ctor = get_report_ctor(report_type)
        new = report_ctor(self.syndrome_id)
        new.__dict__.update(self.__dict__)
        new.defaults(msgs)
        return new

    def title(self, creds):
        if self.header:
            return self.expand(creds, 'header')
        if self.label:
            return self.label
        synd = syndrome.syndromes[self.syndrome_id]
        return '%s %s' % (synd.name, self.type_label)

    def demog_fields(self, context=None):
        fields = demogfields.get_demog_fields(globals.db, self.syndrome_id)
        if context is not None:
            fields = fields.context_fields(context)
        return fields

    def all_form_info(self):
        return syndrome.syndromes[self.syndrome_id].all_form_info()

    def form_info(self, form_name):
        return syndrome.syndromes[self.syndrome_id].form_info(form_name)

    def defaults(self, msgs=None):
        if msgs is None:
            msgs = messages.Messages()
        introspect.callall(self, '_defaults', msgs)
        return msgs

    def check(self, msgs=None):
        """
        After loading, base classes may need to warn the user about
        things such as form version skew.
        """
        if msgs is None:
            msgs = messages.Messages()
        introspect.callall(self, '_check', msgs)
        return msgs

    def cols_update(self):
        """
        Called prior to processing user request to update column options
        """
        introspect.callall(self, '_cols_update')

    def deleted_filter(self):
        return False

    def query(self, cred, no_order=False, form_based=False, 
                          include_deleted=False):
        kw = {}
        if self.order_by and not no_order:
            kw['order_by'] = self.query_order()
        if self.deleted_filter():
            include_deleted = None
        query = globals.db.query('cases', **kw)
        query.join('JOIN persons USING (person_id)')
        caseaccess.acl_query(query, cred, deleted=include_deleted)
        query.where('syndrome_id = %s', self.syndrome_id)
        if self.show_filters:
            self.filter_query(query, form_based=form_based)
        return query

    def count(self, cred):
        return self.query(cred, no_order=True).aggregate('count(case_id)')

    def get_case_ids(self, cred):
        return self.query(cred).fetchcols('case_id')

    def forms_used(self):
        used = set()
        introspect.callall(self, '_forms_used', used)
        return used

    def to_xml(self, xmlgen):
        curnode = xmlgen.push('report')
        curnode.attr('type', self.report_type)
        curnode.attr('name', self.label)
        xmlgen.pushtext('header', self.header)
        if self.syndrome_id is not None:
            synd = syndrome.syndromes[self.syndrome_id]
            xmlgen.pushtext('syndrome', synd.name)  # Informational
        introspect.callall(self, '_to_xml', xmlgen, curnode)
        xmlgen.pop()


class HeadFootParamsMixin:

    show_headfoot = True

    preamble = ''
    footer = ''

    def _defaults(self, msgs):
        if not self.preamble:
            synd = syndrome.syndromes[self.syndrome_id]
            self.preamble = synd.description

    def _to_xml(self, xmlgen, curnode):
        xmlgen.pushtext('preamble', self.preamble)
        xmlgen.pushtext('footer', self.footer)


report_types = {}

class LineReportParams(
                FormDependancyMixin,
                reportfilters.FilterParamsMixin, 
                reportcolumns.OutcolsParamsMixin, 
                OrderbyParamsMixin, 
                HeadFootParamsMixin,
                store.ParamSaveMixin,
                ReportParamsBase):

    report_type = 'line'
    type_label = 'Line Report'

    export_strip_newlines = 'yes'
    export_column_labels = 'fields'
    export_row_type = 'forms'

    def report(self, cred, msgs):
        self.check(msgs)
        if msgs.have_errors():
            return
        return linereport.ReportChunks(self, self.get_case_ids(cred))

    def export_rows(self, cred):
        if self.export_row_type == 'forms':
            exporter = export.ExportForms
        elif self.export_row_type == 'cases':
            exporter = export.ExportCases
        else:
            raise Error('Select an row export scheme')
        return exporter(self, self.get_case_ids(cred), 
                        field_labels=(self.export_column_labels == 'fields'),
                        strip_newlines=(self.export_strip_newlines == 'yes'))

    def _to_xml(self, xmlgen, curnode):
        e = xmlgen.push('export')
        e.boolattr('strip_newlines', self.export_strip_newlines)
        e.attr('column_labels', self.export_column_labels)
        e.attr('row_type', self.export_row_type)
        xmlgen.pop()

report_types[LineReportParams.report_type] = LineReportParams

ReportParams = LineReportParams                 # Legacy: old pickles


class EpicurveParams(
                FormDependancyMixin,
                reportfilters.FilterParamsMixin, 
                epicurve.EpiCurveParamsMixin,
                store.ParamSaveMixin,
                ReportParamsBase):

    report_type = 'epicurve'
    type_label = 'Epi Curve'

report_types[EpicurveParams.report_type] = EpicurveParams


class CrosstabReportParams(
                FormDependancyMixin,
                crosstab.CrosstabParams,
                reportfilters.FilterParamsMixin,
                store.ParamSaveMixin,
                ReportParamsBase):

    report_type = 'crosstab'
    type_label = 'Crosstab'


report_types[CrosstabReportParams.report_type] = CrosstabReportParams


class ContactVisReportParams(
                FormDependancyMixin,
                contactvis.ContactVisParamsMixin,
                reportfilters.FilterParamsMixin,
                store.ParamSaveMixin,
                ReportParamsBase):

    report_type = 'contactvis'
    type_label = '%s visualisation' % config.contact_label

report_types[ContactVisReportParams.report_type] = ContactVisReportParams


def report_type_optionexpr():
    options = [(rt.type_label, rt.report_type) for rt in report_types.values()]
    options.sort()
    return [(b, a) for a, b in options]


def get_report_ctor(report_type):
    try:
        return report_types[report_type]
    except KeyError:
        raise KeyError('Unknown report type %r' % report_type)

def new_report(syndrome_id, report_type='line'):
    report_ctor = get_report_ctor(report_type)
    new = report_ctor(syndrome_id)
    new.defaults()
    return new


def type_label(report_type):
    try:
        return report_types[report_type].type_label
    except KeyError:
        return '???'
