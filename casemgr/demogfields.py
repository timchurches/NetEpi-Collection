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

# Standard Modules
import time
# Application Modules
import config
from cocklebur import datetime, agelib, languages, countries, utils
from casemgr import person, casestatus, caseassignment, casetags, \
                    syndrome, addressstate

TTL = 10 * 60
DEMOG_TABLE = 'syndrome_demog_fields'

# NOTE If adding more contexts, add columns to syndrome_demog_fields table.
contexts = 'case', 'form', 'search', 'person', 'result'
_showattrs = ['show_' + c for c in contexts]

entity_table = {
    None: None,
    'case': 'cases', 
    'person': 'persons'
}
demog_classes = []

class DemogFieldMeta(type):
    def __init__(cls, name, bases, attrs):
        type.__init__(cls, name, bases, attrs)
        cls.table = entity_table[cls.entity]
        if 'name' in attrs:
            demog_classes.append(cls)

def _copyattrs(dst, src):
    if src.label:
        dst.label = src.label
    for varname in _showattrs:
        setattr(dst, varname, bool(getattr(src, varname, True)))

def _cmpattrs(dst, src):
    if src.label != dst.label:
        return False
    for varname in _showattrs:
        if bool(getattr(src, varname)) != bool(getattr(dst, varname)):
            return False
    return True

def _getpathattr(ns, path):
    try:
        return utils.nsgetattr(ns, path)
    except AttributeError:
        return None


class DemogSaved(object):

    def __init__(self, row):
        _copyattrs(self, row)


class DemogField(object):
    __metaclass__ = DemogFieldMeta
#    db_fields = 'label', 'show_case', 'show_form'
    hideable = True
    show_case = True
    show_form = True
    show_search = True
    show_person = True
    show_result = True
    optionexpr = None
    disabled = False
    disabled_form = True
    field = None
    render = None
    section = None
    syndrome_id = None
    context = None
    entity = None

    def __init__(self, syndrome_id, row=None, save_initial=False):
        self.syndrome_id = syndrome_id
        if row is not None:
            _copyattrs(self, row)
        if save_initial:
            self.initial = DemogSaved(self)

    def allow_field(self, context):
        return hasattr(self, 'field_' + context)

    def show(self, context):
        """ Should the field appear in the given /context/? """
        return (self.allow_field(context) 
                and getattr(self, 'show_' + context, True))

    def outtrans(self, ns):
        return _getpathattr(ns, self.field or self.name)

    def summary(self, ns):
        value = self.outtrans(ns)
        if value:
            return '%s: %s' % (self.label, value)

    def context_field(self, context, disabled=False):
        """ Make a context-specific copy of this field """
        context_field = self.__class__(self.syndrome_id)
        context_field.syndrome_id = self.syndrome_id
        context_field.context = context
        for attr in ('field', 'label', 'render', 'disabled', 'section'):
            value = getattr(self, attr + '_' + context, None)
            if value is None:
                value = getattr(self, attr)
            if attr == 'disabled' and disabled:
                value = disabled
            setattr(context_field, attr, value)
        return context_field

    ### Methods from this point on are only used when editing fields
    def has_changed(self):
        return not _cmpattrs(self, self.initial)

    def reset(self):
        del self.label
        for varname in _showattrs:
            try:
                delattr(self, varname)
            except AttributeError:
                pass
        _copyattrs(self, self.__class__)

    def set(self, state):
        for varname in _showattrs:
            setattr(self, varname, state)

    def update(self, row, common):
        all_defaults = True
        if not self.label or self.label == common.label:
            row.label = None
        else:
            row.label = self.label
            all_defaults = False
        for varname in _showattrs:
            commonvalue = getattr(common, varname)
            selfvalue = bool(getattr(self, varname, commonvalue))
            setattr(row, varname, selfvalue)
            if selfvalue != commonvalue:
                all_defaults = False
        if all_defaults:
            row.db_delete()
        else:
            row.db_update(refetch=False)


class SelDemogField(DemogField):
    render = 'select'

    def optionexpr(self):
        optionexpr = self._optionexpr()
        if self.context in ('search', 'person'):
            assert not optionexpr[0][0], 'optionexpr[0][0] is %r, not null\n%r' % (optionexpr[0][0], optionexpr)
            optionexpr = list(optionexpr)
            optionexpr[0:1] = [
                ('', 'Any'),
                ('!', optionexpr[0][1]),
            ]
        return optionexpr

    def outtrans(self, ns):
        value = _getpathattr(ns, self.field or self.name)
        if value:
            map = dict(self.optionexpr())
            return map.get(value, value)


class DemogStateBase(SelDemogField):

    def _optionexpr(self):
        return addressstate.optionexpr()


class DatetimeBase(DemogField):
    render = 'datetimeinput'

    def format(self):
        return datetime.mx_parse_datetime.format

    def outtrans(self, ns):
        value = DemogField.outtrans(self, ns)
        if value:
            return value.strftime(self.format())


class DemogCountryBase(SelDemogField):
    show_result = False

    def _optionexpr(self):
        return countries.country_optionexpr


class DemogInterpreterRequired(SelDemogField):
    name = 'interpreter_req'
    label = 'Interpreter'
    show_result = False
    field_case = field_form = 'case.person.interpreter_req'
    field_search = field_person = 'search.person.interpreter_req'
    field_result = 'interpreter_req'
    entity = 'person'

    def _optionexpr(self):
        return languages.language_optionexpr


class DemogIndigenous(SelDemogField):
    name = 'indigenous_status'
    label = 'Indigenous status'
    show_case = show_form = show_search = show_person = show_result = False
    field_case = field_form = 'case.person.indigenous_status'
    field_search = field_person = 'search.person.indigenous_status'
    field_result = 'indigenous_status'
    entity = 'person'

    def _optionexpr(self):
        return person.indigenous_values

    def outtrans(self, ns):
        value = DemogField.outtrans(self, ns)
        if value:
            return person.indigenous_map.get(value, '')

    def summary(self, ns):
        return self.outtrans(ns)


class DemogCaseDefinition(DemogField):
    name = 'case_definition'
    label = config.syndrome_label
    render = 'value'
    render_search = 'select_syndrome'
    show_person = False
    field_case = 'case.syndrome.name'
    field_form = 'case.syndrome.syndrome_id'
    field_search = 'search.search_syndrome_id'
    field_result = 'syndrome_id'
    section = 'id'
    entity = 'case'

    def outtrans(self, ns):
        value = DemogField.outtrans(self, ns)
        if value and value != 'Any':
            return syndrome.syndromes[value].name

    def summary(self, ns):
        return self.outtrans(ns)


class DemogCaseStatus(SelDemogField):
    name = 'case_status'
    label = 'Status'
    show_person = False
    field_case = field_form = 'case.case_row.case_status'
    field_search = 'search.case_status'
    field_result = 'case_status'
    section = 'id'
    entity = 'case'

    def _optionexpr(self):
        if self.syndrome_id is not None:
            args = [self.syndrome_id]
        else:
            args = []
        return casestatus.optionexpr(*args)

    def outtrans(self, ns):
        value = DemogField.outtrans(self, ns)
        if value:
            return casestatus.get_label(self.syndrome_id, value)


class DemogLocalId(DemogField):
    name = 'local_case_id'
    label = 'Local ID'
    render = 'textinput'
    field_case = field_form = 'case.case_row.local_case_id'
    field_search = field_person = 'search.local_case_id'
    field_result = 'local_case_id'
    section = 'id'
    entity = 'case'


class DemogCaseAssignment(SelDemogField):
    name = 'case_assignment'
    label = 'Case Assignment'
    show_person = False
    field_case = field_form = 'case.case_row.case_assignment'
    field_search = 'search.case_assignment'
    field_result = 'case_assignment'
    section = 'id'
    entity = 'case'

    def _optionexpr(self):
        if self.syndrome_id is not None:
            args = [self.syndrome_id]
        else:
            args = []
        return caseassignment.optionexpr(*args)

    def outtrans(self, ns):
        value = DemogField.outtrans(self, ns)
        if value:
            return caseassignment.get_label(self.syndrome_id, value)


class DemogSystemId(DemogField):
    name = 'case_id'
    label = 'System ID'
    render = 'value'
    #render_search = 'textinput'
    show_person = False
    field_case = field_form = 'case.case_row.case_id'
    #field_search = 'search.case_id'
    field_result = 'case_id'
    section = 'id'
    entity = 'case'


class DemogSurname(DemogField):
    name = 'surname'
    label = 'Surname'
    render = 'textinput'
#    hideable = False
    field_case = field_form = 'case.person.surname'
    field_search = field_person = 'search.person.surname'
    field_result = 'surname'
    section = 'name'
    entity = 'person'

    def summary(self, ns):
        return DemogField.outtrans(self, ns) or None


class DemogGivenNames(DemogField):
    name = 'given_names'
    label = 'Given names'
    render = 'textinput'
    field_case = field_form = 'case.person.given_names'
    field_search = field_person = 'search.person.given_names'
    field_result = 'given_names'
    section = 'name'
    entity = 'person'

    def summary(self, ns):
        return DemogField.outtrans(self, ns) or None


class DemogDOB(DatetimeBase):
    name = 'DOB'
    label = 'Date of birth/Age'
    render_case = 'case_dob'
    field_case = 'case.person.DOB_edit'
    field_form = 'case.person.DOB'
    render_search = render_person = 'datetimeinput'
    field_search = field_person = 'search.person.DOB_edit'
    field_result = 'DOB'
    entity = 'person'

    def age_if_dob(self, ns):
        return agelib.age_if_dob(_getpathattr(ns, self.field or self.name))

    def outtrans(self, ns):
        attr = self.field or self.name
        dob = _getpathattr(ns, attr)
        prec = _getpathattr(ns, attr + '_prec')
        return agelib.dobage_str(dob, prec)

    def summary(self, ns):
        return self.outtrans(ns)


class DemogSex(SelDemogField):
    name = 'sex'
    label = 'Sex'
    render = 'select'
    field_case = field_form = 'case.person.sex'
    field_search = field_person = 'search.person.sex'
    field_result = 'sex'
    entity = 'person'

    def optionexpr(self):
        return person.sexes

    def outtrans(self, ns):
        value = DemogField.outtrans(self, ns)
        if value and value != 'U':
            return person.expandsex(value)

    def summary(self, ns):
        return self.outtrans(ns)


class DemogHomePhone(DemogField):
    name = 'home_phone'
    label = 'Home phone'
    render = 'textinput'
    show_form = False
    show_result = False
    field_case = field_form = 'case.person.home_phone'
    field_search = field_person = 'search.person.home_phone'
    field_result = 'home_phone'
    section = 'phone'
    entity = 'person'


class DemogMobilePhone(DemogField):
    name = 'mobile_phone'
    label = 'Mobile phone'
    render = 'textinput'
    show_form = False
    show_result = False
    field_case = field_form = 'case.person.mobile_phone'
    field_search = field_person = 'search.person.mobile_phone'
    field_result = 'mobile_phone'
    section = 'phone'
    entity = 'person'


class DemogFaxPhone(DemogField):
    name = 'fax_phone'
    label = 'Fax'
    render = 'textinput'
    show_form = False
    show_result = False
    field_case = field_form = 'case.person.fax_phone'
    field_search = field_person = 'search.person.fax_phone'
    field_result = 'fax_phone'
    section = 'phone'
    entity = 'person'


class DemogEMail(DemogField):
    name = 'e_mail'
    label = 'e-mail'
    render = 'textinput'
    show_case = show_form = show_search = show_person = show_result = False
    field_case = field_form = 'case.person.e_mail'
    field_search = field_person = 'search.person.e_mail'
    field_result = 'e_mail'
    section = 'phone'
    entity = 'person'


class DemogStreetAddress(DemogField):
    name = 'street_address'
    label = 'Street address'
    render = 'textinput'
    show_form = False
    show_result = False
    field_case = field_form = 'case.person.street_address'
    field_search = field_person = 'search.person.street_address'
    field_result = 'street_address'
    section = 'address'
    entity = 'person'


class DemogLocality(DemogField):
    name = 'locality'
    label = 'Locality/Suburb'
    render = 'textinput'
    field_case = field_form = 'case.person.locality'
    field_search = field_person = 'search.person.locality'
    field_result = 'locality'
    section = 'address'
    entity = 'person'


class DemogState(DemogStateBase):
    name = 'state'
    label = 'State'
    render = 'select'
    show_form = False
    field_case = field_form = 'case.person.state'
    field_search = field_person = 'search.person.state'
    field_result = 'state'
    section = 'address'
    entity = 'person'


class DemogPostcode(DemogField):
    name = 'postcode'
    label = 'Postcode'
    render = 'textinput'
    show_result = False
    field_case = field_form = 'case.person.postcode'
    field_search = field_person = 'search.person.postcode'
    field_result = 'postcode'
    section = 'address'
    entity = 'person'


class DemogCountry(DemogCountryBase):
    name = 'country'
    label = 'Country'
    field_case = field_form = 'case.person.country'
    field_search = field_person = 'search.person.country'
    show_case = show_form = show_search = show_person = show_result = False
    field_result = 'country'
    section = 'address'
    entity = 'person'


class AltDemogStreetAddress(DemogField):
    name = 'alt_street_address'
    label = 'Alternate Street address'
    render = 'textinput'
    show_case = show_form = show_search = show_person = show_result = False
    field_case = field_form = 'case.person.alt_street_address'
    field_search = field_person = 'search.person.alt_street_address'
    field_result = 'alt_street_address'
    section = 'alt_address'
    entity = 'person'


class AltDemogLocality(DemogField):
    name = 'alt_locality'
    label = 'Alternate Locality/Suburb'
    render = 'textinput'
    show_case = show_form = show_search = show_person = show_result = False
    field_case = field_form = 'case.person.alt_locality'
    field_search = field_person = 'search.person.alt_locality'
    field_result = 'alt_locality'
    section = 'alt_address'
    entity = 'person'


class AltDemogState(DemogStateBase):
    name = 'alt_state'
    label = 'Alternate State'
    render = 'select'
    show_case = show_form = show_search = show_person = show_result = False
    field_case = field_form = 'case.person.alt_state'
    field_search = field_person = 'search.person.alt_state'
    field_result = 'alt_state'
    section = 'alt_address'
    entity = 'person'


class AltDemogPostcode(DemogField):
    name = 'alt_postcode'
    label = 'Alternate Postcode'
    render = 'textinput'
    show_case = show_form = show_search = show_person = show_result = False
    field_case = field_form = 'case.person.alt_postcode'
    field_search = field_person = 'search.person.alt_postcode'
    field_result = 'alt_postcode'
    section = 'alt_address'
    entity = 'person'


class AltDemogCountry(DemogCountryBase):
    name = 'alt_country'
    label = 'Alternate Country'
    show_case = show_form = show_search = show_person = show_result = False
    field_case = field_form = 'case.person.alt_country'
    field_search = field_person = 'search.person.alt_country'
    field_result = 'alt_country'
    section = 'alt_address'
    entity = 'person'


class WorkDemogStreetAddress(DemogField):
    name = 'work_street_address'
    label = 'Work/School Street address'
    render = 'textinput'
    show_case = show_form = show_search = show_person = show_result = False
    field_case = field_form = 'case.person.work_street_address'
    field_search = field_person = 'search.person.work_street_address'
    field_result = 'work_street_address'
    section = 'occupation'
    entity = 'person'


class WorkDemogLocality(DemogField):
    name = 'work_locality'
    label = 'Work/School Locality/Suburb'
    render = 'textinput'
    show_case = show_form = show_search = show_person = show_result = False
    field_case = field_form = 'case.person.work_locality'
    field_search = field_person = 'search.person.work_locality'
    field_result = 'work_locality'
    section = 'occupation'
    entity = 'person'


class WorkDemogState(DemogStateBase):
    name = 'work_state'
    label = 'Work/School State'
    render = 'select'
    show_case = show_form = show_search = show_person = show_result = False
    field_case = field_form = 'case.person.work_state'
    field_search = field_person = 'search.person.work_state'
    field_result = 'work_state'
    section = 'occupation'
    entity = 'person'


class WorkDemogPostcode(DemogField):
    name = 'work_postcode'
    label = 'Work/School Postcode'
    render = 'textinput'
    show_case = show_form = show_search = show_person = show_result = False
    field_case = field_form = 'case.person.work_postcode'
    field_search = field_person = 'search.person.work_postcode'
    field_result = 'work_postcode'
    section = 'occupation'
    entity = 'person'


class WorkDemogCountry(DemogCountryBase):
    name = 'work_country'
    label = 'Work/School Country'
    field_case = field_form = 'case.person.work_country'
    field_search = field_person = 'search.person.work_country'
    show_case = show_form = show_search = show_person = show_result = False
    field_result = 'work_country'
    section = 'occupation'
    entity = 'person'


class WorkDemogPhone(DemogField):
    name = 'work_phone'
    label = 'Work/School phone'
    render = 'textinput'
    show_form = False
    show_result = False
    field_case = field_form = 'case.person.work_phone'
    field_search = field_person = 'search.person.work_phone'
    field_result = 'work_phone'
    section = 'occupation'
    entity = 'person'


class DemogOccupation(DemogField):
    name = 'occupation'
    label = 'Occupation'
    render = 'textinput'
    show_case = show_form = show_search = show_person = show_result = False
    field_case = field_form = 'case.person.occupation'
    field_search = field_person = 'search.person.occupation'
    field_result = 'occupation'
    section = 'occupation'
    entity = 'person'


class DemogPassportNumber(DemogField):
    name = 'passport_number'
    label = 'Passport number'
    render = 'textinput'
    show_result = False
    field_case = field_form = 'case.person.passport_number'
    field_search = field_person = 'search.person.passport_number'
    field_result = 'passport_number'
    section = 'passport'
    entity = 'person'


class DemogPassportCountry(DemogCountryBase):
    name = 'passport_country'
    label = 'Passport country/Nationality'
    field_case = field_form = 'case.person.passport_country'
    field_search = field_person = 'search.person.passport_country'
    field_result = 'passport_country'
    section = 'passport'
    entity = 'person'


class DemogPassportNumber2(DemogField):
    name = 'passport_number_2'
    label = 'Second passport number'
    render = 'textinput'
    show_case = show_form = show_search = show_person = show_result = False
    field_case = field_form = 'case.person.passport_number_2'
    field_search = field_person = 'search.person.passport_number_2'
    field_result = 'passport_number_2'
    section = 'passport'
    entity = 'person'


class DemogPassportCountry2(DemogCountryBase):
    name = 'passport_country_2'
    label = 'Second passport country/Nationality'
    show_case = show_form = show_search = show_person = show_result = False
    field_case = field_form = 'case.person.passport_country_2'
    field_search = field_person = 'search.person.passport_country_2'
    field_result = 'passport_country_2'
    section = 'passport'
    entity = 'person'


class DemogNotes(DemogField):
    name = 'notes'
    label = 'Other Information'
    render = 'textarea'
    show_case = show_form = show_search = show_person = show_result = False
    field_case = field_form = 'case.case_row.notes'
#    field_search = field_person = None
    field_result = 'notes'
    section = 'notes'
    entity = 'case'


class DemogNotificationDate(DatetimeBase):
    name = 'notification_datetime'
    label = 'Notification Date'
    show_person = False
    show_result = False
    field_case = field_form = 'case.case_row.notification_datetime'
    field_result = 'notification_datetime'
    section = 'notification'
    entity = 'case'


class DemogOnsetDate(DatetimeBase):
    name = 'onset_datetime'
    label = 'Onset Date'
    render = 'datetimeinput'
    show_search = show_person = False
    field_case = field_form = 'case.case_row.onset_datetime'
    field_result = 'onset_datetime'
    section = 'notification'
    entity = 'case'


class DemogNotifierName(DemogField):
    name = 'notifier_name'
    label = 'Notifier name'
    render = 'textinput'
    show_case = show_form = show_search = show_person = show_result = False
    field_case = field_form = 'case.case_row.notifier_name'
    field_search = field_person = 'search.notifier_name'
    field_result = 'notifier_name'
    section = 'notification'
    entity = 'case'


class DemogNotifierContact(DemogField):
    name = 'notifier_contact'
    label = 'Notifier contact details'
    render = 'textarea'
    show_case = show_form = show_search = show_person = show_result = False
    field_case = field_form = 'case.case_row.notifier_contact'
#    field_search = field_person = 'search..notifier_contact'
    field_result = 'notifier_contact'
    section = 'notification'
    entity = 'case'


class DemogTags(DemogField):
    name = 'tags'
    label = 'Tags'
    render = 'tags'
    show_case = show_search = show_result = True
    section = None
    entity = 'case'
    field_search = field_person = 'search.tags'
    field_case = 'case.tags.cur'
    field_result = 'tags'

    def optionexpr(self):
        return [(ti.tag, ti.tag) for ti in casetags.tags()]


class DemogDeleted(DemogField):
    name = 'deleted'
    label = 'Deleted'
    render = render_person = 'short_radio'
    show_person = False
    field_search = field_person = 'search.deleted'
    field_result = 'deleted'
    entity = 'case'

    def optionexpr(self):
        return [
            ('n', 'No'),
            ('y', 'Yes'),
            ('', 'Both'),
        ]

    def outtrans(self, ns):
        value = DemogField.outtrans(self, ns)
        if self.context in ('search', 'person'):
            if value == 'y':
                return 'DELETED only'
            elif value == '':
                return 'Include DELETED'
        elif value:
            return 'DELETED'

    def summary(self, ns):
        return self.outtrans(ns)


class DemogDeleteReason(DemogField):
    name = 'delete_reason'
    label = 'Deletion reason'
    render = 'textinput'
    show_case = show_form = show_search = show_person = show_result = False
    field_result = 'delete_reason'
    entity = 'case'


class DemogDeleteTimestamp(DatetimeBase):
    name = 'delete_timestamp'
    label = 'Deletion date'
    render = 'datetimeinput'
    show_case = show_form = show_search = show_person = show_result = False
    field_result = 'delete_timestamp'
    entity = 'case'


class DemogDataSrc(DemogField):
    name = 'data_src'
    label = 'Data source'
    render = 'textinput'
    #field_case = field_form = 'case.person.data_src'
    field_search = field_person = 'search.person.data_src'
    #field_result = 'data_src'
    show_case = show_form = show_search = show_person = show_result = False
    entity = 'person'


def rows_and_cols(fields, row_width=2):
    rows = []
    row = []
    section = None
    for field in fields:
        if len(row) >= row_width or (field.section != section and row):
            rows.append(row)
            row = []
        section = field.section
        row.append(field)
    if row:
        rows.append(row)
    return rows


class DemogFieldsBase(list):
    group_defs = [
        (None, None),
        ('Address', 'address'),
        ('Alt Address', 'alt_address'),
        ('Work/School', 'occupation'),
        ('Passport', 'passport'),
        ('Notification', 'notification'),
        ('Notes', 'notes'),
    ]        
    groups = None
    group_by_name = None

    def __init__(self):
        self.fields_by_name = {}

    def add_field(self, field):
        self.append(field)
        self.fields_by_name[field.name] = field

    def field_by_name(self, name):
        return self.fields_by_name[name]

    def rows_and_cols(self, row_width=2):
        return rows_and_cols(self, row_width)

    def summary(self, ns):
        summary = []
        for field in self:
            field_summary = field.summary(ns)
            if field_summary:
                summary.append(field_summary)
        return ', '.join(summary)

    def grouped(self):
        if self.groups is None:
            self.groups = []
            self.group_by_name = {}
            if len(self) > config.tabbed_demogfields_threshold:
                groups = []
                group_by_section = {}
                for group_def in self.group_defs:
                    group = GroupDemogFields(*group_def)
                    for section in group.sections:
                        group_by_section[section] = group
                    groups.append(group)
                anon_group = groups[0]
                for field in self:
                    group = group_by_section.get(field.section, anon_group)
                    group.add_field(field)
                for group in groups:
                    if group:
                        self.groups.append(group)
                        self.group_by_name[group.name] = group
            if len(self.groups) < 3:
                group = GroupDemogFields(None, None)
                for field in self:
                    group.add_field(field)
                self.groups = [group]
                self.group_by_name = {None: group}
        return self.groups

    def group(self, name):
        if self.group_by_name is None:
            self.grouped()
        try:
            return self.group_by_name[name]
        except KeyError:
            # This generally shouldn't happen, but admin changes to demogfields
            # and other obscure stuff can result in an invalid group request,
            # so don't throw an ugly error.
            return GroupDemogFields('', '')

    def tabs(self, initial=None):
        from casemgr.tabs import Tabs
        tabs = Tabs(initial)
        for group in self.grouped():
            if group.label:
                tabs.add(group.name, group.label)
        tabs.done()
        return tabs


class GroupDemogFields(DemogFieldsBase):
    def __init__(self, label, *sections):
        DemogFieldsBase.__init__(self)
        self.name = sections[0]
        self.label = label
        self.sections = sections


class ContextDemogFields(DemogFieldsBase):
    def __init__(self, demog_fields, context, *opts):
        DemogFieldsBase.__init__(self)
        for demog_field in demog_fields:
            if demog_field.show(context):
                self.add_field(demog_field.context_field(context, *opts))


class ReportContextDemogFields(DemogFieldsBase):
    """
    The "report" context includes all "case" context fields, plus fields that
    are hard-coded in the UI.
    """
    forced = (
        'deleted', 'delete_reason', 'delete_timestamp', 'data_src',
    )
    def __init__(self, demog_fields):
        DemogFieldsBase.__init__(self)
        for demog_field in demog_fields:
            if (demog_field.name in self.forced or demog_field.show('case')):
                self.add_field(demog_field)


class ReorderedDemogFields(DemogFieldsBase):
    def __init__(self, demog_fields, order):
        DemogFieldsBase.__init__(self)
        field_map = {}
        for field in demog_fields:
            field_map[field.name] = field
        for name in order:
            field = field_map.pop(name, None)
            if field:
                self.add_field(field)
        for field in demog_fields:
            if field.name in field_map:
                self.add_field(field)


class DemogFields(DemogFieldsBase):
    def __init__(self, db, syndrome_id, save_initial=False):
        DemogFieldsBase.__init__(self)
        self.syndrome_id = syndrome_id
        self.context_cache = {}
        common_rows_by_name, rows_by_name = self.rows_dict(db)
        for demog_field_cls in demog_classes:
            row = rows_by_name.get(demog_field_cls.name)
            common_row = common_rows_by_name.get(demog_field_cls.name)
            field = demog_field_cls(syndrome_id, row or common_row, 
                                    save_initial)
            self.add_field(field)

    def rows_dict(self, db, for_update=False):
        rows_by_name = {}
        common_rows_by_name = {}
        query = db.query(DEMOG_TABLE, for_update=for_update)
        if self.syndrome_id is None:
            query.where('syndrome_id is null')
        else:
            query.where('(syndrome_id is null OR syndrome_id = %s)', 
                        self.syndrome_id)
        for row in query.fetchall():
            if row.syndrome_id == self.syndrome_id:
                rows_by_name[row.name] = row
            elif row.syndrome_id is None:
                common_rows_by_name[row.name] = row
        return common_rows_by_name, rows_by_name

    def context_fields(self, context, disabled=False):
        cache_key = context, disabled
        try:
            context_fields = self.context_cache[cache_key]
        except KeyError:
            if context == 'report':
                context_fields = ReportContextDemogFields(self)
            else:
                context_fields = ContextDemogFields(self, context, disabled)
            self.context_cache[cache_key] = context_fields
        return context_fields

    def reordered_context_fields(self, order, context, *opts):
        fields = self.context_fields(context, *opts)
        if not order:
            return fields
        def basename(name):
            return name.split('.')[-1]
        # This is abusing the context_cache to cache reordered fields
        order = tuple(map(basename, order))
        key = (context, False) + order
        try:
            context_fields = self.context_cache[key]
        except KeyError:
            context_fields = ReorderedDemogFields(fields, order)
            self.context_cache[key] = context_fields
        return context_fields

    ### Methods from this point on are only used when editing fields
    def has_changed(self):
        for demog_field in self:
            if demog_field.has_changed():
                return True
        return False

    def update(self, db):
        common_rows_by_name, rows_by_name = self.rows_dict(db, for_update=True)
        for demog_field in self:
            try:
                row = rows_by_name[demog_field.name]
            except KeyError:
                row = db.new_row(DEMOG_TABLE)
                row.syndrome_id = self.syndrome_id
                row.name = demog_field.name
            cls = demog_field.__class__
            common_row = common_rows_by_name.get(demog_field.name)
            demog_field.update(row, cls(None, common_row))


class DemogFieldCache(object):
    subscribed = False

    def __init__(self):
        self.fields_by_syndrome = {}

    def notification(self, *args):
        for id in args:
            if id == 'None':
                self.flush()
            else:
                try:
                    del self.fields_by_syndrome[int(id)]
                except KeyError:
                    pass

    def flush(self):
        self.fields_by_syndrome.clear()

    def get_demog_fields(self, db, syndrome_id):
        if not self.subscribed:
            from globals import notify
            self.subscribed = True
            if not notify.subscribe('demogfields', self.notification):
                # Notification not available - use time based refresh.
                pass
        now = time.time()
        try:
            demog_fields = self.fields_by_syndrome[syndrome_id]
        except KeyError:
            demog_fields = None
        else:
            if demog_fields.fetch_time + TTL < now:
                demog_fields = None
        if demog_fields is None:
            demog_fields = DemogFields(db, syndrome_id)
            demog_fields.fetch_time = now
            self.fields_by_syndrome[syndrome_id] = demog_fields
        return demog_fields


demog_field_cache = DemogFieldCache()
get_demog_fields = demog_field_cache.get_demog_fields
flush = demog_field_cache.flush
