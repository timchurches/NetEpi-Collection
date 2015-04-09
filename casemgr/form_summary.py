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

# Standard libraries
from time import time

# Application modules
from cocklebur import form_ui, datetime
from casemgr import globals, cached
import config

# NOTE - due to a historical mistake the form abstractions transpose the common
# meanings of "name" and "label": the form "name" is a short description
# intended user consumption, and "label" is the system name from which table
# names and file names are derived. Sorry - AM

def instance_summary(form, instance_row):
    return '; '.join(form.collect_summary(instance_row))


class EditForm(object):
    """
    Represents an active edit of a case form (corresponds to a row in the
    summary and form instance tables).
    """
    def __init__(self, case_id, form, summary=None, 
                 data_src=None, force_multiple=False):
        self.case_id = case_id
        self.name = form.name
        self.label = form.label
        self.version = form.cur_version
        self.allow_multiple = form.allow_multiple
        self.data_src = data_src
        if force_multiple:
            self.allow_multiple = True
        if summary is None:
            self.summary_id = None
            self.deleted = False
            self.delete_reason = None
            self.delete_timestamp = None
        else:
            self.summary_id = summary.summary_id
            self.data_src = summary.data_src
            self.deleted = summary.deleted
            self.delete_reason = summary.delete_reason
            self.delete_timestamp = summary.delete_timestamp
        form = self.get_form_ui()
        self.instance_row = form_ui.load_form_data(globals.db, form, 
                                                   self.summary_id)

    def get_form_data(self):
        return self.instance_row

    def viewonly(self):
        return bool(self.deleted or self.data_src)

    def foreign_src(self):
        return bool(not self.deleted and self.data_src)

    def get_form_ui(self):
        try:
            return globals.formlib.load(self.label, self.version)
        except form_ui.FormError:
            import traceback
            traceback.print_exc()
            # This is a user app, so we hide the scary error
            raise form_ui.FormError('the %r form type is unavailable due to '
                                    'problems with it\'s structure' % 
                                        self.label)

    def validate(self):
        return self.get_form_ui().validate(self.instance_row)

    def db_desc(self):
        return self.instance_row.db_desc()

    def has_changed(self):
        return self.instance_row.db_has_changed()

    def take_ownership(self):
        assert self.data_src
        self.data_src = None

    def reload_instance(self, msg):
        """
        Our instance row cannot be saved (form upgrade or a conflicting
        update of a singleton form) - reload and merge our changes
        into the loaded row.
        """
        instance_row = form_ui.load_form_data(globals.db, self.get_form_ui(),
                                              self.summary_id)
        instance_row.db_merge(self.instance_row)
        self.instance_row = instance_row
        raise globals.ReviewForm(msg)

    def update(self):
        if config.form_rollforward:
            # Detect if the form definition has been upgraded while we were
            # editing. If so, update the dbobj to refer to the correct table,
            # and force the user to review the form before saving again.
            query = globals.db.query('forms', for_update=True)
            query.where('label = %s', self.label)
            deployed_version = query.aggregate('cur_version')
            if deployed_version != self.version:
                self.version = deployed_version
                self.reload_instance(
                    'The definition of this form was changed while you were '
                    'editing it. Please review all fields carefully before '
                    'saving it.') 
        summary_row = None
        if self.summary_id is None and not self.allow_multiple:
            # If form is a singleton, ensure nobody else created one while we
            # were editing - if they did, load their form, merge our fields
            # into it and then force the user to review the result before
            # saving again.
            globals.db.lock_table('case_form_summary', 'EXCLUSIVE')
            query = globals.db.query('case_form_summary', for_update=True)
            query.where('form_label = %s', self.label)
            query.where('case_id = %s', self.case_id)
            query.where('NOT deleted')
            summary_row = query.fetchone()
            if summary_row is not None:
                self.summary_id = summary_row.summary_id
                self.reload_instance(
                    'Another user has already created this form. Your data '
                    'has been merged into their form. Please review the '
                    'changes carefully, and then save.')
        else:
            query = globals.db.query('case_form_summary', for_update=True)
            query.where('summary_id = %s', self.summary_id)
            summary_row = query.fetchone()
        if summary_row is None:
            summary_row = globals.db.new_row('case_form_summary')
            self.summary_id = summary_row.db_nextval('summary_id')
            summary_row.form_label = self.label
            summary_row.summary_id = self.summary_id
            summary_row.case_id = self.case_id
            self.instance_row.summary_id = self.summary_id
        summary_row.form_version = self.version
        summary_row.data_src = self.data_src
        if self.instance_row.form_date:
            summary_row.form_date = self.instance_row.form_date
        form = self.get_form_ui()
        summary_row.summary = instance_summary(form, self.instance_row)
        summary_row.db_update()
        if not self.instance_row.form_date:
            self.instance_row.form_date = summary_row.form_date
        was_new = self.instance_row.is_new()
        self.instance_row.db_update()
        task_info = dict(form_name=self.label, 
                         summary_id=self.summary_id, 
                         is_new=was_new)
        return task_info

    def set_deleted(self, delete, reason=None):
        if delete:
            timestamp = datetime.now().mx()
        else:
            timestamp = None
            reason = None
        query = globals.db.query('case_form_summary')
        query.where('summary_id = %s', self.summary_id)
        query.update('deleted=%s, delete_reason=%s, delete_timestamp=%s',
                     delete, reason, timestamp)
        globals.db.commit()
        self.deleted = delete

    def task_info(self):
        return dict(form_name=self.label, 
                    summary_id=self.summary_id,
                    is_new=self.summary_id is None)

    def abort(self):
        task_info = self.task_info()
        self.instance_row.db_revert()
        return task_info


def _getform(label, syndrome_id=None):
    query = globals.db.query('forms')
    query.where('label = %s', label)
    if syndrome_id is not None:
        subq = query.in_select('label', 'syndrome_forms', 
                               columns=('form_label',))
        subq.where('syndrome_id = %s', syndrome_id)
    form = query.fetchone()
    if form is None:
        raise form_ui.FormError('Nonexistent form: %r' % label)
    return form


def _getsummary(summary_id):
    query = globals.db.query('case_form_summary')
    query.where('summary_id = %s', summary_id)
    return query.fetchone()


def new_form(syndrome_id, case_id, label):
    # New form - are we allowed to create it?
    form = _getform(label, syndrome_id)
    if not form.allow_multiple:
        query = globals.db.query('case_form_summary')
        query.where('case_id = %s', case_id)
        query.where('form_label = %s', form.label)
        query.where('NOT deleted')
        if query.aggregate('count(summary_id)') > 0:
            raise form_ui.FormError('The %r form has already been'
                                    ' completed' % form.name)
    return EditForm(case_id, form)


def edit_form(summary_id):
    summary = _getsummary(summary_id)
    if summary is None:
        raise form_ui.FormError('Form not found')
    form = _getform(summary.form_label)
    return EditForm(summary.case_id, form, summary)


class FormDataImp:

    def __init__(self, syndrome_id, label, data_src):
        assert data_src
        self.form = _getform(label, syndrome_id)
        self.data_src = data_src

    def edit(self, case_id):
        # Import deliberately ignores allow_multiple (via force_multiple) at
        # this time as it is too difficult to handle the resulting RequireMerge
        # exceptions.
        query = globals.db.query('case_form_summary')
        query.where('case_id = %s', case_id)
        query.where('form_label = %s', self.form.label)
        query.where('data_src = %s', self.data_src)
        query.where('NOT deleted')
        summary = query.fetchone()
        if summary is None:
            edit_form = EditForm(case_id, self.form, None, 
                                 data_src=self.data_src, 
                                 force_multiple=True)
        else:
            edit_form = EditForm(summary.case_id, self.form, summary, 
                                 force_multiple=True)
        return edit_form, edit_form.get_form_data()


class FormSummary:
    """
    A summary of a single form
    """

    def __init__(self, summary_row):
        self.summary_id = summary_row.summary_id
        self.form_label = summary_row.form_label
        self.form_version = summary_row.form_version
        self.form_date = summary_row.form_date
        self.data_src = summary_row.data_src
        self.summary = summary_row.summary
        self.deleted = summary_row.deleted
        self.delete_reason = summary_row.delete_reason
        self.delete_timestamp = summary_row.delete_timestamp

    def update_summary(self, form, instance_row):
        self.summary = instance_summary(form, instance_row)


class FormSummaries:
    """
    Represents the collection of summaries of a given syndrome form
    """
    def __init__(self, form_row, case_id):
        self.label = form_row.label
        self.version = form_row.cur_version
        self.name = form_row.name
        self.allow_multiple = form_row.allow_multiple
        self.allow_new = True
        self.case_id = case_id
        self.summaries = []
        self.summaries_by_id = {}
        self.summaries_by_src = {}

    def add_summary_from_row(self, summary_row):
        summary = FormSummary(summary_row)
        self.summaries.append(summary)
        self.summaries_by_id[summary.summary_id] = summary
        if not self.allow_multiple and not summary.deleted:
            self.allow_new = False
        if summary.data_src:
            self.summaries_by_src[summary.data_src] = summary

    def load_summaries(self):
        by_version = {}
        for s in self.summaries:
            by_version.setdefault(s.form_version, []).append(s.summary_id)
        for version, ids in by_version.items():
            try:
                form_def = globals.formlib.load(self.label, version)
            except form_ui.FormError:
                continue        # Nothing else we can do for now
            query = globals.db.query(form_def.table)
            query.where_in('summary_id', ids)
            for instance_row in query.fetchall():
                try:
                    summary = self.summaries_by_id[instance_row.summary_id]
                except KeyError:
                    pass
                else:
                    summary.update_summary(form_def, instance_row)

    def allow_new_form(self):
        """
        Can the current form have new instances?

        This test is cheap and potentially inaccurate - it is called
        repeatedly while rendering the UI. A more comprehensive
        test is done when the user actually attempts to create a
        new form instance, and again when a form is saved.
        """
        return self.allow_new


# We'd rather use a generator function or a real iterator, but, at the time,
# the Albatross <al-for> tag only supported indexable types.
class FormEnumerator:

    def __init__(self, forms):
        self.forminfo = [(s.form_label, s.form_version, s.summary_id)
                         for form in forms for s in form.summaries]

    def __getitem__(self, i):
        label, version, summary_id = self.forminfo[i]
        form = globals.formlib.load(label, version)
        instance_row = form_ui.load_form_data(globals.db, form, summary_id)
        return form, instance_row

            
class FormsList(cached.Cached, list):
    """
    Represents the collection of forms applicable to a loaded case or contact.
    """
    time_to_live = 30

    def __init__(self, syndrome_id, summary_order_by='form_date'):
        self.syndrome_id = syndrome_id
        self.summary_order_by = summary_order_by
        self.by_name = None
        self.case_id = None

    def set_case(self, case_id):
        if self.case_id != case_id:
            self.case_id = case_id
            self.cache_invalidate()

    def getform(self, label):
        if self.by_name is None:
            self.load()
        return self.by_name[label]

    def load(self):
        #import traceback
        #traceback.print_stack()
        del self[:]
        self.by_name = {}
        query = globals.db.query('forms', order_by='syndrome_forms_id')
        query.join('JOIN syndrome_forms'
                    ' ON syndrome_forms.form_label = forms.label')
        query.where('syndrome_forms.syndrome_id = %s', self.syndrome_id)
        for row in query.fetchall():
            fs = FormSummaries(row, self.case_id) 
            self.append(fs)
            self.by_name[fs.label] = fs
        query = globals.db.query('case_form_summary', 
                                    order_by=('deleted', self.summary_order_by))
        query.where('case_id = %s', self.case_id)
        for row in query.fetchall():
            try:
                form_summaries = self.by_name[row.form_label]
            except KeyError:
                pass
            else:
                form_summaries.add_summary_from_row(row)
        if not config.cache_form_summaries:
            for form_summaries in self:
                form_summaries.load_summaries()


class FormsListMixin(object):

    def __init__(self, syndrome_id):
        self.forms = FormsList(syndrome_id)

    def getform(self, form_label):
        return self.forms.getform(form_label)

    def enumerate_forms(self):
        return FormEnumerator(self.forms)

    def can_merge_forms(self):
        self.forms.refresh()
        for form in self.forms:
            if len(form.summaries) > 1:
                return True
        return False

    def form_data_src(self):
        return self.edit_form.form_data_src()

    def edit_form(self, summary_id):
        self.forms.cache_invalidate()
        return edit_form(summary_id)

    def new_form(self, label):
        self.forms.cache_invalidate()
        return new_form(self.case_row.syndrome_id, self.case_row.case_id, label)
