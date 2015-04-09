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

from cocklebur import dbobj, form_ui
from casemgr import globals

def formrollforward(db, name, target_vers, rollforward_map):
    """
    This function makes no attempt to update summary text, as this
    would require loading all the form instance data!

    We also can't cope with the source data being spread across
    multiple tables (as is the case when the configuration option
    form_rollforward has been set to false) - we'd need a rollforward
    map for each previous version of the form, and the chances of
    a successful roll-forward would be greatly diminished.
    """
    db.lock_table('case_form_summary', 'EXCLUSIVE')
    query = db.query('case_form_summary')
    query.where('form_label = %s', name)
    summ_id_by_version = {}
    for summary in query.fetchall():
        try:
            ids = summ_id_by_version[summary.form_version]
        except KeyError:
            ids = summ_id_by_version[summary.form_version] = []
        ids.append(summary.summary_id)
    if not summ_id_by_version:
        return                    # Nothing needing roll-forward
    if len(summ_id_by_version) > 1:
        raise dbobj.DatabaseError('Cannot roll-forward form data - system '
                                  'has been operated with form_rollforward '
                                  'set to False, and form data is spread over '
                                  'multiple tables.')
    from_vers = summ_id_by_version.keys()[0]
    src_cols, dst_cols = zip(*rollforward_map)
    sys_cols = ('summary_id', 'form_date')
    src_cols = ','.join(sys_cols + src_cols)
    dst_cols = ','.join(sys_cols + dst_cols)
    src_table = globals.formlib.tablename(name, from_vers)
    dst_table = globals.formlib.tablename(name, target_vers)
    curs = db.cursor()
    try:
        dbobj.execute(curs, 'UPDATE case_form_summary SET form_version=%s '
                            'WHERE form_label = %s', (target_vers, name))
        dbobj.execute(curs, 'INSERT INTO %s (%s) SELECT %s FROM %s' %\
                        (dst_table, dst_cols, src_cols, src_table))
    finally:
        curs.close()
