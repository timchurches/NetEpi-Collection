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

import sys, os
import cPickle
import base64
import traceback
from cStringIO import StringIO

def report_cvt(db):
    # Preload the report compatibility modules, and remap the module namespace
    # so the unpickling can find them.
    from casemgr.schema.report_1_6 import reportfilters, reportcrosstab,\
                                          reportcolumns, report
    sys.modules['casemgr.reportfilters'] = reportfilters
    sys.modules['casemgr.reportcrosstab'] = reportcrosstab
    sys.modules['casemgr.reportcolumns'] = reportcolumns
    sys.modules['casemgr.report'] = report
    try:
        form_info = {}
        query = db.query('forms')
        for n, l, v in query.fetchcols(('label', 'name', 'cur_version')):
            form_info[n.lower()] = (n, l, v)
        query = db.query('report_params')
        fail_count = 0
        for row in query.fetchall():
            if not row.pickle:
                continue
            try:
                f = StringIO()
                params = cPickle.loads(base64.decodestring(row.pickle))
                params.xmlsave(f, form_info)
                row.xmldef = f.getvalue()
                if row.label is None and row.user_id is not None:
                    row.sharing = 'last'
                elif row.user_id is not None:
                    row.sharing = 'private'
                elif row.unit_id is not None:
                    row.sharing = 'unit'
                else:
                    row.sharing = 'public'
                row.db_update()
            except Exception:
                fail_count += 1
                print >> sys.stderr, '*** Unable to convert report "%s"\n    (user %s, unit %s, sharing %s, type %s)' % (row.label, row.user_id, row.unit_id, row.sharing, row.type)
                traceback.print_exc()
        if fail_count:
            sys.exit('%s reports were not converted' % fail_count)
    finally:
        for n, m in sys.modules.items():
            if 'report_1_6' in getattr(m, '__file__', ''):
                del sys.modules[n]
