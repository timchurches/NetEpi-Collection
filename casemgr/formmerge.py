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

class FormMergeError(globals.Error): pass
Error = FormMergeError
class FormHasChanged(FormMergeError): pass

class NullRow:
    def __getattr__(self, name):
        return None
nullrow = NullRow()

class MergeCol:
    def __init__(self, merge, input, index):
        self.merge = merge
        self.name = input.column
        self.label = input.label or input.column
        self.error = None
        value_a = input.get_value(merge.row_a)
        value_b = input.get_value(merge.row_b)
        self.conflict = (value_a and value_b and value_a != value_b)
        if not value_a and not value_b:
            self.source = 'd'
        elif value_b and not value_a:
            self.source = 'b'
        elif self.conflict and isinstance(value_a, str) and value_a == 'None':
            self.source = 'b'
        else:
            self.source = 'a'
        self.source_field = 'formmerge.fields[%d].source' % index
        self.set_butt = 'edit:%d' % index

    def get_input(self):
        return self.merge.get_input(self.name)

    def outtrans(self, ns):
        return self.get_input().outtrans(ns) or ''

    def format(self):
        return self.get_input().format()

    def toggle_edit(self):
        if self.source == 'e':
            self.source = self.last_source
        else:
            input = self.get_input()
            if not input.get_value(self.merge.form_data):
                if self.source == 'a':
                    input.nscopy(self.merge.row_a, self.merge.form_data)
                elif self.source == 'b':
                    input.nscopy(self.merge.row_b, self.merge.form_data)
            self.last_source = self.source
            self.source = 'e'

    def validate(self):
        if self.source == 'e':
            # Only validate a field if there is manual input.
            self.error = None
            input = self.get_input()
            try:
                input.validate(self.merge.form_data)
            except form_ui.ValidationError, e:
                self.error = str(e)
                return False
        return True

    def desc_edit(self):
        input = self.get_input()
        value_a = input.get_value(self.merge.row_a)
        value_b = input.get_value(self.merge.row_b)
        value_e = input.get_value(self.merge.form_data)
        if self.source == 'e':
            op = 'Edit'
            hilite = value_e != value_a or value_e != value_b
            ns = self.merge.form_data
        elif self.source == 'a' and value_a != value_b:
            op = 'A'
            hilite = True
            ns = self.merge.row_a
        elif self.source == 'b' and value_a != value_b:
            op = 'B'
            hilite = True
            ns = self.merge.row_b
        elif self.source == 'd' and (value_a or value_b):
            op = 'DELETE'
            hilite = True
            if value_a:
                ns = self.merge.row_a
            else:
                ns = self.merge.row_b
        else:
            return None
        return self.label, op, input.outtrans(ns), hilite

    def apply(self, row_a, row_b):
        input = self.get_input()
        value_a = input.get_value(row_a)
        value_b = input.get_value(row_b)
        initial_a = input.get_value(self.merge.row_a)
        initial_b = input.get_value(self.merge.row_b)
        if initial_a != value_a or initial_b != value_b:
            raise FormHasChanged
        elif self.source == 'a':
            src = self.merge.row_a
        elif self.source == 'b':
            src = self.merge.row_b
        elif self.source == 'd':
            src = nullrow
        elif self.source == 'e':
            src = self.merge.form_data
        input.nscopy(src, row_a)
        input.nscopy(src, row_b)
        value = input.get_value(src)
        return value_a != value, value_b != value


class FormMerge:
    def __init__(self, case_id, key_a, key_b):
        self.case_id = case_id
        self.key_a = key_a
        self.key_b = key_b
        self._load()
        form = self.get_form_ui()
        self.form_data = form_ui.load_form_data(globals.db, form, None)

    def _load(self):
        self.summary_a, self.summary_b = self._fetch_summary()
        self.form_label = self.summary_a.form_label
        self.form_version = self.summary_a.form_version
        self.form_description = self._fetch_description()
        self.row_a, self.row_b = self._fetch_rows()
        self._init_fields()

    def _fetch_summary(self, for_update=False):
        summary_a = summary_b = None
        query = globals.db.query('case_form_summary', for_update=for_update)
        query.where('case_id = %s', self.case_id)
        query.where_in('summary_id', (self.key_a, self.key_b))
        for summary in query.fetchall():
            if summary.summary_id == self.key_a:
                summary_a = summary
            elif summary.summary_id == self.key_b:
                summary_b = summary
        if summary_a is None or summary_b is None:
            raise Error('Could not fetch form summary')
        if summary_a.form_label != summary_b.form_label:
            raise Error('Forms must be of the same type')
        if summary_a.form_version != summary_b.form_version:
            raise Error('Form definition version does not match!')
        return summary_a, summary_b

    def _fetch_description(self):
        query = globals.db.query('forms')
        query.where('label = %s', self.form_label)
        row = query.fetchone()
        return row.name

    def _fetch_rows(self, for_update=False):
        form = self.get_form_ui()
        row_a = row_b = None
        query = globals.db.query(form.table, for_update=for_update)
        query.where_in('summary_id', (self.key_a, self.key_b))
        for row in query.fetchall():
            if row.summary_id == self.key_a:
                row_a = row
            elif row.summary_id == self.key_b:
                row_b = row
        if row_a is None or row_b is None:
            raise Error('Could not fetch form data')
        return row_a, row_b

    def _add_field(self, input):
        self.fields.append(MergeCol(self, input, len(self.fields)))

    def _init_fields(self):
        self.fields = []
        form = self.get_form_ui()
        self.form_date_input = None
        try:
            self.get_input('form_date')
        except KeyError:
            self.form_date_input = form_ui.DatetimeInput('form_date',
                                                        label='Form date')
            self._add_field(self.form_date_input)
        for input in form.get_inputs():
            self._add_field(input)

    def get_form_ui(self):
        return globals.formlib.load(self.form_label, self.form_version)

    def get_input(self, name):
        if name == 'form_date' and self.form_date_input is not None:
            return self.form_date_input
        return self.get_form_ui().columns.find_input(name)

    def toggle_edit(self, index):
        self.fields[index].toggle_edit()

    def validate(self):
        okay = True
        for field in self.fields:
            if not field.validate():
                okay = False
        return okay

    def desc_edit(self):
        edits = []
        for mc in self.fields:
            desc = mc.desc_edit()
            if desc:
                edits.append(desc)
        return edits

    def merge(self, credentials):
        form = self.get_form_ui()
        summary_a, summary_b = self._fetch_summary(for_update=True)
        row_a, row_b = self._fetch_rows(for_update=True)
        a_delta_count = b_delta_count = 0
        for mc in self.fields:
            try:
                a_changed, b_changed = mc.apply(row_a, row_b)
            except FormHasChanged:
                row_a.db_revert()
                row_b.db_revert()
                self.row_a = row_a
                self.row_b = row_b
                self._init_fields()
                raise
            if a_changed:
                a_delta_count += 1
            if b_changed:
                b_delta_count += 1
        # Now decide which direction to merge
        if b_delta_count > a_delta_count:
            update_row, delete_row = row_a, row_b
            update_summary, delete_summary = summary_a, summary_b
        else:
            update_row, delete_row = row_b, row_a
            update_summary, delete_summary = summary_b, summary_a
        assert update_row.summary_id == update_summary.summary_id
        assert delete_row.summary_id == delete_summary.summary_id
        # Describe and log the update
        update_desc = update_row.db_desc()
        delete_desc = delete_row.db_desc()
        if not update_desc:
            update_desc = 'no edits required'
        if not delete_desc:
            delete_desc = 'no edits required'
        desc = 'Merge %s form, System ID %s, UPDATED %s, DELETED %s' %\
                    (self.form_label, self.case_id, update_desc, delete_desc)
        credentials.user_log(globals.db, desc, case_id=self.case_id)
        update_summary.form_date = update_row.form_date
        update_summary.summary = '; '.join(form.collect_summary(update_row))
        update_row.db_update(refetch=False)
        delete_row.db_delete()
        update_summary.db_update(refetch=False)
        delete_summary.db_delete()
#        globals.db.rollback()   # While debugging
