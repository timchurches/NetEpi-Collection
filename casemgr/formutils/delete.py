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

from cocklebur import dbobj, form_ui

from casemgr import globals

from exclusiveop import exclusiveop

def delete_form(forms_row, name):
    try:
        globals.formlib.delete(name)
    except form_ui.NoFormError:
        pass
    for table_desc in globals.formlib.form_tables(globals.db, name):
        globals.db.drop_table(table_desc.name)
    # We haven't used an ON DELETE CASCADE here simply to make it harder for
    # the admin to have have a catastrophic accident SQL typo...
    curs = globals.db.cursor()
    try:
        dbobj.execute(curs, 'DELETE FROM case_form_summary '
                            'WHERE form_label = %s', (name,))
    finally:
        curs.close()
    forms_row.db_delete()
    globals.db.save_describer()

delete_form = exclusiveop(delete_form)
