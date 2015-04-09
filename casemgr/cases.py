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
import time
import re
from cocklebur import dbobj, datetime, pt
from casemgr import globals, person, form_summary, demogfields, \
                    syndrome, casestatus, caseaccess, casetags

import config

ValidationError = dbobj.ValidationError

def local_case_id_validate(local_case_id):
    if not local_case_id:
        return
#    if len(local_case_id) > 10:
#        raise dbobj.ValidationError('Local ID must be 10 characters or less')
    if not re.match('^[a-zA-Z0-9]+$', local_case_id):
        raise dbobj.ValidationError('Local ID must be alphanumeric')

class ACL(pt.SearchPT):
    def __init__(self, credentials, case_row):
        self.credentials = credentials
        ptable = globals.db.participation_table('case_acl','case_id','unit_id')
        ptable.preload_from_result([case_row])
        pt.SearchPT.__init__(self, ptable[case_row.case_id], 'name',
                             filter='enabled', info_page=True)

    def remove(self, index):
        if self.pt_set[int(index)].unit_id == self.credentials.unit.unit_id:
            self.search_error = 'Can\'t delete your unit\'s access'
            return
        pt.SearchPT.remove(self, index)


class Case(form_summary.FormsListMixin):

    def __init__(self, credentials, case_row, seed_person=None):
        if case_row is None:
            raise dbobj.DatabaseError('Access denied')
        self.acl = None
        self.case_row = case_row
        self.deleted = bool(self.case_row.deleted)
        self.delete_reason = self.case_row.delete_reason
        self.delete_timestamp = self.case_row.delete_timestamp
        self.syndrome = syndrome.syndromes[case_row.syndrome_id]
        self.credentials = credentials
        self.tags = casetags.CaseTags(self.case_row.case_id)
        self._contact_count = None
        form_summary.FormsListMixin.__init__(self, case_row.syndrome_id)
        if self.case_row.is_new():
            self.person = person.edit_new(seed_person)
        else:
            self.person = person.edit_id(self.case_row.person_id)
        self.forms.set_case(self.case_row.case_id)

    def load_acl(self):
        if self.case_row.case_id:
            self.acl = ACL(self.credentials, self.case_row)
    
    def unload_acl(self):
        self.acl = None

    def viewonly(self):
        return self.deleted or 'VIEWONLY' in self.credentials.rights

    def assert_not_viewonly(self):
        if self.viewonly():
            raise ValidationError('Case is view-only')

    def __str__(self):
        parts = []
        if self.person.surname:
            parts.append(self.person.surname)
        if self.person.given_names:
            if parts:
                parts.append(', ')
            parts.append(self.person.given_names)
        if self.case_row.local_case_id:
            if parts:
                parts.append(' ')
            parts.append('[%s]' % self.case_row.local_case_id)
        if self.case_row.case_id:
            if parts:
                parts.append(' ')
            parts.append('(ID %s)' % self.case_row.case_id)
        return ''.join(parts)

    def title(self):
        if self.is_new():
            title = 'Add'
        elif self.viewonly():
            title = 'View'
        else:
            title = 'Edit'
        title += ' Case'
        count = self.contact_count()
        if count == 1:
            title = '%s - 1 %s' % (title, config.contact_label.lower())
        else:
            title = '%s - %d %ss' % (title, count, config.contact_label.lower())
        return title

    def new(cls, credentials, syndrome_id, 
            from_search=None, use_person_id=None, 
            defer_case_id=False, **kwargs):
        """
        Alternate constructor, used when case is new
        """
        if defer_case_id:
            case_id = None
        else:
            case_id = globals.db.nextval('cases', 'case_id')
        case_seed = dict(case_id=case_id,
                         syndrome_id=syndrome_id,
                         notification_datetime=datetime.now())
        if from_search is not None:
            if use_person_id is None:
                kwargs['seed_person'] = from_search.person
            if from_search.case_status != '!':
                case_seed['case_status'] = from_search.case_status
            if from_search.case_assignment != '!':
                case_seed['case_assignment'] = from_search.case_assignment
            case_seed['local_case_id'] = from_search.local_case_id
            # case_seed['notes'] = from_search.notes
            # case_seed['notification_datetime'] = from_search.notification_datetime
            # case_seed['onset_datetime'] = from_search.onset_datetime
            case_seed['notifier_name'] = from_search.notifier_name
            # case_seed['notifier_contact'] = from_search.notifier_contact
        case_row = globals.db.new_row('cases', **case_seed)
        case = cls(credentials, case_row, **kwargs)
        if use_person_id is not None:
            case.use_person_id(use_person_id)
        if from_search and from_search.tags:
            # This doesn't give the normal "seed" semantics.
            case.tags.cur = from_search.tags
        return case
    new = classmethod(new)

    def get_demog_fields(self, context):
        disabled = self.viewonly() or bool(self.person.data_src)
        syndrome_id = self.case_row.syndrome_id
        fields = demogfields.get_demog_fields(globals.db, syndrome_id)
        return fields.context_fields(context, disabled=disabled)

    def use_person_id(self, person_id):
        self.person = person.edit_id(person_id)

    def is_new(self):
        return self.case_row.is_new()

    def field_label(self, field):
        # get_demog_fields() and field_by_name() internally cache lookups
        demog_fields = demogfields.get_demog_fields(globals.db, 
                                                    self.case_row.syndrome_id)
        return demog_fields.field_by_name(field).label

    def validate(self):
        _label = self.field_label
        try:
            self.person.normalise()
            self.person.validate()
        except person.Error, e:
            raise ValidationError('%s' % e)
        case_row = self.case_row
        if not case_row.local_case_id and not self.person.surname:
            raise ValidationError('Either %s or %s must be specified' %
                                  (_label('surname'), _label('local_case_id')))
        local_case_id_validate(case_row.local_case_id)
        try:
            case_row.onset_datetime = \
                datetime.mx_parse_datetime(case_row.onset_datetime)
        except datetime.Error, e:
            raise ValidationError('%s: %s' % (_label('onset_datetime'), e))
        try:
            case_row.notification_datetime = \
                datetime.mx_parse_datetime(case_row.notification_datetime)
        except datetime.Error, e:
            raise ValidationError('%s: %s' % 
                                  (_label('notification_datetime'), e))
        if datetime.is_later_than(self.case_row.onset_datetime,
                                  self.case_row.notification_datetime):
            raise ValidationError('%s must be after %s' %
                                  (_label('notification_datetime'), 
                                   _label('onset_datetime')))
        if datetime.is_later_than(self.person.DOB,
                                  self.case_row.onset_datetime):
            raise ValidationError('%s must be after %s' %
                                  (_label('onset_datetime'), _label('DOB')))
        if datetime.is_later_than(self.person.DOB, datetime.now()):
            raise ValidationError('\'%s\': %s must not be in the future' %
                    (self.person.DOB, _label('DOB')))
        if datetime.is_later_than(self.case_row.onset_datetime, datetime.now()):
            raise ValidationError('\'%s\': %s must not be in the future' %
                    (self.case_row.onset_datetime, _label('onset_datetime')))
        if datetime.is_later_than(self.case_row.notification_datetime,
                                  datetime.now()):
            raise ValidationError('\'%s\': %s must not be in the future' %
                    (self.case_row.notification_datetime, 
                     _label('notification_datetime')))

    def has_changed(self):
        return (
            self.tags.has_changed() or
            self.case_row.db_has_changed() or 
            self.person.has_changed()
        )

    def db_desc(self):
        desc = [
            self.person.db_desc(), 
            self.case_row.db_desc(), 
            self.tags.desc(),
        ]
        return ', '.join([d for d in desc if d])

    def cc_notify(self):
        """
        Syndrome case count has changed, send notification
        """
        globals.notify.notify('syndromecasecount', self.case_row.syndrome_id)

    def update(self):
        self.assert_not_viewonly()
        self.validate()
        is_new = self.is_new()
        self.person.db_update()
        self.case_row.person_id = self.person.person_id
        try:
            self.case_row.db_update()
        except dbobj.RecordDeleted:
            raise dbobj.RecordDeleted('Record has been deleted (or merged) by another user')
        self.tags.update(self.case_row.case_id)
        if is_new:
            case_acl = globals.db.new_row('case_acl')
            case_acl.case_id = self.case_row.case_id
            case_acl.unit_id = self.credentials.unit.unit_id
            case_acl.db_update()
            self.cc_notify()
        self.forms.set_case(self.case_row.case_id)

    def revert(self):
        self.person.db_revert()
        self.case_row.db_revert()

    def delete(self):
        # NOTE - not longer used - cases are logically deleted.
        #
        # This method is unusual in that it performs a db.commit(). This is so
        # the person delete can be rolled back without rolling back the case
        # delete. 
        query = globals.db.query('case_form_summary')
        query.where('case_id = %s', self.case_row.case_id)
        query.delete()
        self.case_row.db_delete()
        globals.db.commit()
        try:
            self.person.db_delete()
        except (dbobj.IntegrityError, dbobj.OperationalError):
            # Probably linked to other cases.
            globals.db.rollback()
        else:
            globals.db.commit()
        self.cc_notify()

    def user_log(self, event_type):
        try:
            self.credentials.user_log(globals.db, event_type,
                                      case_id=self.case_row.case_id)
        except dbobj.ConstraintError:
            raise dbobj.RecordDeleted('Record has been deleted (or merged) by another user')

    def contact_count(self):
        if self._contact_count is None:
            query = globals.db.query('cases')
            caseaccess.contact_query(query, self.case_row.case_id)
            query.where('not deleted')
            self._contact_count = query.aggregate('count(*)')
        return self._contact_count

    def invalidate_contact_count(self):
        self._contact_count = None

    def rows_and_cols(self, context):
        return self.get_demog_fields(context).rows_and_cols()

    def init_tabs(self, select=None):
        self.tabs = self.get_demog_fields('case').tabs(select)

    def set_deleted(self, delete, reason=None):
        if delete:
            timestamp = datetime.now().mx()
        else:
            timestamp = None
            reason = None
        query = globals.db.query('cases')
        query.where('case_id = %s', self.case_row.case_id)
        query.update('deleted=%s, delete_reason=%s, delete_timestamp=%s',
                     delete, reason, timestamp)
        globals.db.commit()
        self.deleted = delete
        self.delete_reason = reason
        self.delete_timestamp = timestamp


def edit_case(credentials, case_id):
    query = globals.db.query('cases')
    query.where('case_id = %s', case_id)
    caseaccess.acl_query(query, credentials, deleted=None)
    return Case(credentials, query.fetchone())

new_case = Case.new


def case_query(credentials, **kwargs):
    """
    Look up a (single) case via kwargs (local_case_id, etc)
    """
    query = globals.db.query('cases')
    for col, val in kwargs.iteritems():
        query.where('%s = %%s' % col, val)
    caseaccess.acl_query(query, credentials, deleted=None)
    row = query.fetchone()
    if row is None:
        return None
    return Case(credentials, query.fetchone())


def edit_form(credentials, summary_id):
    ef = form_summary.edit_form(summary_id)
    case = edit_case(credentials, ef.case_id)
    return case, ef

