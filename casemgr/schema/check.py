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

from cocklebur import form_ui
from casemgr.formutils import deploy

def check_form_dependancies(db, db_user):
    def set_from_query(query, *cols):
        s = set()
        for label, version in query.fetchcols(cols):
            if version is None:
                version = 0
            s.add((label, version))
        return s
    # Check that the tables have been created, as are called prior to schema
    # creation for new installs.
    for table in ('form_defs', 'case_form_summary', 'syndrome_forms', 'forms'):
        if not db.db_has_relation(table):
            return
    formlib = form_ui.FormLibXMLDB(db, 'form_defs')
    # collect forms defined
    defined = set()
    for entry in formlib:
        defined.add((entry.name, entry.version))
    # collect "in-use" forms (referenced by summary instances)
    query = db.query('case_form_summary', distinct=True)
    in_use = set_from_query(query, 'form_label', 'form_version')
    # collect "deployed" forms (cur_version not null or used by a syndrome)
    query = db.query('syndrome_forms', distinct=True)
    query.join('RIGHT JOIN forms ON (forms.label = syndrome_forms.form_label)')
    query.where('syndrome_id IS NOT NULL')
    deployed = set_from_query(query, 'label', 'cur_version')
    # collect "registered" forms
    registered = set(db.query('forms').fetchcols('label'))

    # Warn for in-use, but missing defs
    for missing in in_use - defined:
        print '    *** WARNING - definition for in-use form %r vers %s is missing!' % missing
    # Warn for deployed, but missing defs
    for missing in deployed - in_use - defined:
        print '    *** WARNING - definition for deployed form %r vers %s is missing!' % missing

    # Create missing form instance tables
    for name, version in (in_use | deployed) & defined:
        table = formlib.tablename(name, version)
        if not db.db_has_relation(table):
            print '    *** form %r vers %s instance table is missing - creating' % (name, version)
        elif db.has_table(table):
            # Has table and describer - nothing further to do
            continue
        try:
            form = formlib.load(name, version)
        except form_ui.FormError, e:
            print '    *** WARNING - unable to load %r, vers %s - FORM '\
                  'INSTANCE TABLE NOT CREATED!' % (name, version)
            print '        %s' % e
        deploy.make_form_table(db, form, table)
    # Create entries in "forms" table for defined forms
    highest_by_name = {}
    for name, version in defined:
        if name not in registered:
            if name not in highest_by_name or version > highest_by_name[name]:
                highest_by_name[name] = version
    for name, version in highest_by_name.items():
        print '    *** noting new form %r' % name
        form = formlib.load(name, version)
        formrow = db.new_row('forms')
        formrow.label = name
        formrow.name = form.text
        formrow.form_type = form.form_type
        formrow.allow_multiple = form.allow_multiple
        formrow.db_update()
