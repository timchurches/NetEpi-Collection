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
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from cocklebur import xmlwriter

from casemgr import globals, cached, syndrome
from casemgr.reports.common import *

import config


class ParamSaveMixin:

    label = loaded_label = None
    sharing = loaded_sharing = 'private'
    loaded_from_id = None

    sharing_options = [
        ('private', 'None'),
        ('unit', config.unit_label),
        ('public', 'Public'),
        ('quick', 'Quick'),
    ]

    def init(self):
        self.loaded_from_id = None

    def xmlsave(self, f):
        xmlgen = xmlwriter.XMLwriter(f)
        self.to_xml(xmlgen)

    def _save(self, cred, row=None, sharing='private'):
        if row is None:
            row = globals.db.new_row('report_params')
        row.label = self.label
        row.syndrome_id = self.syndrome_id
        row.type = self.report_type
        row.sharing = sharing
        row.user_id = row.unit_id = None
        if sharing in ('private', 'last'):
            row.user_id = cred.user.user_id
        elif sharing == 'unit':
            row.unit_id = cred.unit.unit_id
        f = StringIO()
        self.xmlsave(f)
        row.xmldef = f.getvalue()
        row.db_update()
        self.loaded_from_id = row.report_params_id
        self.loaded_label = row.label
        if sharing == 'quick':
            globals.notify.notify('report_quick', row.report_params_id)

    def save(self, cred):
        row = None
        if self.loaded_from_id is not None and self.label == self.loaded_label:
            query = globals.db.query('report_params')
            query.where('report_params_id = %s', self.loaded_from_id)
            row = query.fetchone()
        sharing = self.sharing
        if sharing == 'last':
            sharing = 'private'
        self._save(cred, row, sharing)

    def autosave(self, cred):
        # This should only save if the parameters have changed, but the current
        # logic is not suited to detecting this.
        query = globals.db.query('report_params')
        query.where('syndrome_id = %s', self.syndrome_id)
        query.where('sharing = %s', 'last')
        query.where('user_id = %s', cred.user.user_id)
        rows = query.fetchall()
        if rows:
            row = rows[0]
        else:
            row = None
        self._save(cred, row, 'last')


def delete(report_params_id):
    query = globals.db.query('report_params')
    query.where('report_params_id = %s', report_params_id)
    query.delete()
    globals.notify.notify('report_params', report_params_id)


legacy = (
    ('report', 'reports.report'),
    ('reportfilters', 'reports.reportfilters'),
    ('reportcolumns', 'reports.reportcolumns'),
    ('reportcrosstab', 'reports.crosstab'),
)

def _parse_file(f):
    # Avoid import cycle
    from casemgr.reports import xmlload
    return xmlload.xmlload(f)


def parse_file(syndrome_id, f):
    params = _parse_file(f)
    params.syndrome_id = syndrome_id
    params.defaults()
    return params


def _decode(row):
    # Avoid import cycle
    from casemgr.reports import xmlload
    try:
        params = _parse_file(StringIO(row.xmldef))
    except ReportParseError, e:
        raise ReportLoadError, 'load %r: %s' % (row.label, e), sys.exc_info()[2]
    params.syndrome_id = row.syndrome_id
    params.label = params.loaded_label = row.label
    params.sharing = params.loaded_sharing = row.sharing
    params.loaded_from_id = row.report_params_id
    params.defaults()
    return params


def load(report_params_id, cred):
    query = globals.db.query('report_params')
    query.where('report_params_id = %s', report_params_id)
    row = query.fetchone()
    if row is None:
        raise Error('Report not found')
    return _decode(row)


def load_last(syndrome_id, report_type, cred):
    """
    Load the last report parameters the user was working on, or a
    new parameter set if none were found.

    NOTE - currently unusued (functionality subsumed into report menu)
    """
    query = globals.db.query('report_params')
    query.where('label is null')
    query.where('syndrome_id = %s', syndrome_id)
    query.where('sharing = %s', 'last')
    query.where('user_id = %s', cred.user.user_id)
    query.where('type = %s', report_type)
    row = query.fetchone()
    if row is not None:
        try:
            return _decode(row)
        except Error:
            pass
    return new_report(syndrome_id, report_type)


class ReportMenuItem(object):

    __slots__ = ('report_params_id', 'label', 'sharing', 'type', 
                 'unit_id', 'user_id', 'sharing')

    def __init__(self, attrs):
        for col, value in zip(self.__slots__, attrs):
            setattr(self, col, value)


class ReportMenu(list):

    def __init__(self, cred, syndrome_id, report_type=None):
        self.syndrome_name = syndrome.syndromes[syndrome_id].name
        self.by_sharing = dict([(mode, []) for mode in sharing_tags])
        query = globals.db.query('report_params', order_by='label')
        query.where('syndrome_id = %s', syndrome_id)
        if report_type:
            query.where('type = %s', report_type)
        sub = query.sub_expr('OR')
        sub.where("sharing IN ('quick', 'public')")
        sub.where("(sharing = 'unit' AND unit_id = %s)", cred.unit.unit_id)
        sub.where("(sharing IN ('private', 'last') AND user_id = %s)", 
                    cred.user.user_id)
        for row in query.fetchcols(ReportMenuItem.__slots__):
            ur = ReportMenuItem(row)
            self.append(ur)
            if ur.sharing == 'last':
                if ur.label:
                    ur.label = 'Most recent: ' + ur.label
                else:
                    ur.label = 'Most recent'
                self.by_sharing['private'].insert(0, ur)
                continue
            self.by_sharing[ur.sharing].append(ur)


class ReportCache(object):

    __slots__ = 'report_params_id', 'syndrome_id', 'label', 'unit_id', 'type'

    def __init__(self, attrs):
        for col, value in zip(self.__slots__, attrs):
            setattr(self, col, value)


class ReportsCache(cached.NotifyCache):

    notification_target = 'report_quick'

    def load(self):
        self.by_synd_by_unit = {}
        self.reports = []
        query = globals.db.query('report_params', order_by='label')
        # This machinery supports including per-unit reports on the main page,
        # although this is currently disabled.
        query.where('sharing = %s', 'quick')
        for row in query.fetchcols(ReportCache.__slots__):
            self.reports.append(ReportCache(row))

    def get_synd_unit(self, syndrome_id, unit_id):
        self.refresh()
        key = syndrome_id, unit_id
        try:
            return self.by_synd_by_unit[key]
        except KeyError:
            by_synd_by_unit = [report
                               for report in self.reports
                               if (report.syndrome_id == syndrome_id)
                                   and (report.unit_id is None 
                                     or report.unit_id == unit_id)]
            self.by_synd_by_unit[key] = by_synd_by_unit
            return by_synd_by_unit

reports_cache = ReportsCache()
