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
from cocklebur import dbobj

from casemgr import globals

from exclusiveop import exclusiveop

def rename_form(forms_row, old_name, new_name):
    globals.formlib.rename(old_name, new_name)
    forms_row.label = new_name
    forms_row.db_update()
    for table_desc in globals.formlib.form_tables(globals.db, old_name):
        new_table = table_desc.name.replace(old_name, new_name)
        globals.db.rename_table(table_desc.name, new_table)
    globals.db.save_describer()

rename_form = exclusiveop(rename_form)
