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
from cocklebur.dbobj import *

class Form(ResultRow):
    types = [
        ('case', 'Case'),
        ('followup', 'Contact Followup'),
    ]

def define_db(dsn):
    db = DatabaseDescriber(dsn)

    td = db.new_table('syndrome_types')
    td.column('syndrome_id', SerialColumn, primary_key = True)
    td.column('priority', IntColumn)
    td.column('name', StringColumn)
    td.column('description', StringColumn)
    td.column('additional_info', StringColumn)
    td.column('enabled', BooleanColumn, default = 'False')
    td.column('post_date', DatetimeColumn, default = 'CURRENT_TIMESTAMP')
    td.column('expiry_date', DatetimeColumn)
    td.order_by_cols('name')
    td.add_index('syndrome_types_name_key', ['lower(name)'], unique=True)

    td = db.new_table('syndrome_demog_fields')
    td.column('synddf_id', SerialColumn, primary_key = True)
    td.column('syndrome_id', ReferenceColumn, 
              references = 'syndrome_types', on_delete = 'cascade')
    td.column('name', StringColumn)
    td.column('label', StringColumn)
    td.column('show_case', BooleanColumn, default = 'True')
    td.column('show_form', BooleanColumn, default = 'True')
    td.column('show_search', BooleanColumn, default = 'True')
    td.column('show_person', BooleanColumn, default = 'True')
    td.column('show_result', BooleanColumn, default = 'True')
    td.add_index('sdf_syndrome_id', ['syndrome_id'])
    td.add_index('sdf_si_name_idx', ['syndrome_id', 'name'], unique=True)

    td = db.new_table('syndrome_case_status')
    td.column('syndcs_id', SerialColumn, primary_key = True)
    td.column('syndrome_id', ReferenceColumn, 
              references = 'syndrome_types', on_delete = 'cascade')
    td.column('name', StringColumn)
    td.column('label', StringColumn)
    td.add_index('scs_syndrome_id', ['syndrome_id'])

    td = db.new_table('syndrome_case_assignments')
    td.column('syndca_id', SerialColumn, primary_key = True)
    td.column('syndrome_id', ReferenceColumn, 
              references = 'syndrome_types', on_delete = 'cascade')
    td.column('name', StringColumn)
    td.column('label', StringColumn)
    td.add_index('sca_syndrome_id', ['syndrome_id'])

    td = db.new_table('form_defs')
    td.column('name', StringColumn)
    td.column('version', IntColumn)
    td.column('xmldef', StringColumn)
    td.add_index('fd_namever_idx', ['name', 'version'], unique=True)
    td.add_index('fd_name_idx', ['name'])

    td = db.new_table('forms', row_class = Form)
    td.column('label', StringColumn, size = 20, primary_key = True)
    td.column('form_type', StringColumn, size = 20)
    td.column('cur_version', IntColumn)
    td.column('name', StringColumn)
    td.column('allow_multiple', BooleanColumn, default = 'True')
    td.column('def_update_time', DatetimeColumn)
    td.order_by_cols('name')

    td = db.new_table('syndrome_forms')
    td.column('syndrome_forms_id', SerialColumn, primary_key = True)
    td.column('syndrome_id', ReferenceColumn, 
              references = 'syndrome_types', on_delete = 'cascade')
    td.column('form_label', ReferenceColumn, 
              references = 'forms', on_update = 'cascade')
    td.order_by_cols('syndrome_forms_id')
    td.add_index('sf_syndrome_id', ['syndrome_id'])

# Later
#    td = db.new_table('addresses', row_class = Address)
#    td.column('address_id', SerialColumn, primary_key = True)
#    td.column('street_address', StringColumn)
#    td.column('locality', StringColumn)
#    td.column('state', StringColumn)
#    td.column('postcode', StringColumn)

    td = db.new_table('persons')
    td.column('person_id', SerialColumn, primary_key = True)
    td.column('last_update', LastUpdateColumn)
    td.column('data_src', StringColumn)
    td.column('surname', StringColumn)
    td.column('given_names', StringColumn)
    td.column('DOB', DateColumn)
    td.column('DOB_prec', IntColumn, default=0)
    td.column('sex', StringColumn, size = 1)
    td.column('interpreter_req', StringColumn)
    td.column('home_phone', StringColumn)
    td.column('work_phone', StringColumn)
    td.column('mobile_phone', StringColumn)
    td.column('fax_phone', StringColumn)
    td.column('e_mail', StringColumn)
    td.column('street_address', StringColumn)
    td.column('locality', StringColumn)
    td.column('state', StringColumn)
    td.column('postcode', StringColumn)
    td.column('country', StringColumn)
    td.column('alt_street_address', StringColumn)
    td.column('alt_locality', StringColumn)
    td.column('alt_state', StringColumn)
    td.column('alt_postcode', StringColumn)
    td.column('alt_country', StringColumn)
    td.column('work_street_address', StringColumn)
    td.column('work_locality', StringColumn)
    td.column('work_state', StringColumn)
    td.column('work_postcode', StringColumn)
    td.column('work_country', StringColumn)
    td.column('occupation', StringColumn)
    td.column('passport_number', StringColumn)
    td.column('passport_country', StringColumn)
    td.column('passport_number_2', StringColumn)
    td.column('passport_country_2', StringColumn)
    td.column('indigenous_status', StringColumn)
    td.order_by_cols('surname', 'given_names')
    td.add_index('p_data_src_idx', ['data_src'])
    td.add_index('p_surname_idx', ['surname'])
    td.add_index('p_given_names_idx', ['given_names'])
    td.add_index('p_interpreter_req_idx', ['interpreter_req'])
    td.add_index('p_DOB_idx', ['DOB'])
    td.add_index('p_sex_idx', ['sex'])
    td.add_index('p_home_phone_idx', ['home_phone'])
    td.add_index('p_work_phone_idx', ['work_phone'])
    td.add_index('p_mobile_phone_idx', ['mobile_phone'])
    td.add_index('p_fax_phone_idx', ['fax_phone'])
    td.add_index('p_e_mail_idx', ['e_mail'])
    td.add_index('p_locality_idx', ['locality'])
    td.add_index('p_state_idx', ['state'])
    td.add_index('p_postcode_idx', ['postcode'])
    td.add_index('p_alt_locality_idx', ['alt_locality'])
    td.add_index('p_alt_state_idx', ['alt_state'])
    td.add_index('p_alt_postcode_idx', ['alt_postcode'])
    td.add_index('p_work_locality_idx', ['work_locality'])
    td.add_index('p_work_state_idx', ['work_state'])
    td.add_index('p_work_postcode_idx', ['work_postcode'])
    td.add_index('p_occupation_idx', ['occupation'])
    td.add_index('p_passport_number_idx', ['passport_number'])
    td.add_index('p_passport_country_idx', ['passport_country'])
    td.add_index('p_passport_number_2_idx', ['passport_number_2'])
    td.add_index('p_passport_country_2_idx', ['passport_country_2'])
    td.add_index('p_indigenous_status_idx', ['indigenous_status'])

    td = db.new_table('groups')
    td.column('group_id', SerialColumn, primary_key = True)
    td.column('group_name', StringColumn, size = 60, unique = True)
    td.column('rights', StringColumn)
    td.column('description', StringColumn)
    td.order_by_cols('group_name')

    td = db.new_table('unit_groups')
    td.column('unit_groups_id', SerialColumn, primary_key = True)
    td.column('unit_id', ReferenceColumn, 
              references = 'units', on_update='cascade', on_delete='cascade')
    td.column('group_id', ReferenceColumn, references = 'groups')
    td.add_index('ug_unit_idx', ['unit_id'])
    td.add_index('ug_group_idx', ['group_id'])

    td = db.new_table('units')
    td.column('unit_id', SerialColumn, primary_key = True)
    td.column('enabled', BooleanColumn, default = 'False')
    td.column('name', StringColumn, unique = True)
    td.column('rights', StringColumn)
    td.column('street_address', StringColumn)
    td.column('postal_address', StringColumn)
    td.column('contact_user_id', ReferenceColumn, 
              references = 'users', on_update='cascade', on_delete='set null')
    td.order_by_cols('name')

    td = db.new_table('group_syndromes')
    td.column('group_syndromes_id', SerialColumn, primary_key = True)
    td.column('syndrome_id', ReferenceColumn, 
              references = 'syndrome_types', on_delete = 'cascade')
    td.column('group_id', ReferenceColumn, references = 'groups')
    td.add_index('gs_unit_idx', ['syndrome_id'])
    td.add_index('gs_group_idx', ['group_id'])

    td = db.new_table('users')
    td.column('user_id', SerialColumn, primary_key = True)
    td.column('last_update', LastUpdateColumn)
    td.column('enabled', BooleanColumn, default='false')
    td.column('deleted', BooleanColumn, default='false')
    td.column('rights', StringColumn)
    td.column('username', StringColumn, size = 60, unique = True)
    td.column('fullname', StringColumn, size = 60)
    td.column('title', StringColumn)
    td.column('agency', StringColumn)
    td.column('expertise', StringColumn)
    td.column('password', PasswdColumn)
    td.column('creation_timestamp', DatetimeColumn, 
              default = 'CURRENT_TIMESTAMP')
    td.column('sponsoring_user_id', ReferenceColumn,
                references='users', on_delete='set null')
    td.column('enable_key', StringColumn)
    td.column('checked_timestamp', DatetimeColumn) 
    td.column('email', StringColumn)
    td.column('phone_home', StringColumn)
    td.column('phone_work', StringColumn)
    td.column('phone_mobile', StringColumn)
    td.column('phone_fax', StringColumn)
    td.column('bad_attempts', IntColumn, default = '0')
    td.column('bad_timestamp', DatetimeColumn)
    td.column('preferences', BinaryColumn)
    td.column('privacy', StringColumn)
    td.order_by_cols('username')
    td.add_index('u_username_idx', ['username'])
    td.add_index('u_email_idx', ['email'])
    td.add_index('u_enable_key_idx', ['enable_key'])

    td = db.new_table('user_log')
    td.column('user_log_id', SerialColumn, primary_key = True)
    td.column('user_id', ReferenceColumn, 
              references ='users', on_update='cascade', on_delete='cascade')
    td.column('event_timestamp', DatetimeColumn, 
              default = 'CURRENT_TIMESTAMP')
    td.column('event_type', StringColumn)
    td.column('remote_addr', StringColumn)
    td.column('forwarded_addr', StringColumn)
    td.column('case_id', ReferenceColumn, 
              references ='cases', on_update='cascade', on_delete='cascade')
    td.add_index('ul_user_id_idx', ['user_id'])
    td.add_index('ul_case_id_idx', ['case_id'])

    td = db.new_table('admin_log')
    td.column('admin_log_id', SerialColumn, primary_key = True)
    td.column('user_id', ReferenceColumn, 
              references ='users', on_update='cascade', on_delete='cascade')
    td.column('event_timestamp', DatetimeColumn, 
              default = 'CURRENT_TIMESTAMP')
    td.column('event_type', StringColumn)
    td.column('remote_addr', StringColumn)
    td.column('forwarded_addr', StringColumn)
    td.add_index('al_user_id_idx', ['user_id'])

    td = db.new_table('unit_users')
    td.column('unit_user_id', SerialColumn, primary_key = True)
    td.column('unit_id', ReferenceColumn, 
              references = 'units', on_update='cascade', on_delete='cascade')
    td.column('user_id', ReferenceColumn, 
              references = 'users', on_update='cascade', on_delete='cascade')
    td.add_index('uu_unit_idx', ['unit_id'])
    td.add_index('uu_user_idx', ['user_id'])

    td = db.new_table('tags')
    td.column('tag_id', SerialColumn, primary_key = True)
    td.column('tag', StringColumn)
    td.column('notes', StringColumn)
    td.add_index('t_tag_idx', ['tag'], unique=True)

    td = db.new_table('case_tags')
    td.column('case_tag_id', SerialColumn, primary_key = True)
    td.column('case_id', ReferenceColumn, 
              references ='cases(case_id)', 
              on_update='cascade', on_delete='cascade')
    td.column('tag_id', ReferenceColumn, 
              references ='tags(tag_id)', 
              on_update='cascade', on_delete='cascade')
    td.add_index('ct_case_id_idx', ['case_id'])
    td.add_index('ct_tag_idx', ['tag_id'])
    td.add_index('ct_case_tag_idx', ['case_id','tag_id'], unique=True)

    td = db.new_table('contact_types')
    td.column('contact_type_id', SerialColumn, primary_key = True)
    td.column('contact_type', StringColumn)
    td.add_index('ct_contact_type_idx', ['lower(contact_type)'], unique=True)

    td = db.new_table('case_contacts')
    td.column('case_id', ReferenceColumn, primary_key=True,
              references ='cases(case_id)', 
              on_update='cascade', on_delete='cascade')
    td.column('contact_id', ReferenceColumn, primary_key=True,
              references ='cases(case_id)', 
              on_update='cascade', on_delete='cascade')
    td.column('contact_type_id', ReferenceColumn, 
              references='contact_types', on_delete='SET NULL')
    td.column('contact_date', DatetimeColumn)
    td.add_index('cc_case_id_idx', ['case_id'])
    td.add_index('cc_contact_id_idx', ['contact_id'])
    td.add_index('cc_contact_type_id_idx', ['contact_type_id'])

    td = db.new_table('cases')
    td.column('case_id', SerialColumn, primary_key = True)
    td.column('last_update', LastUpdateColumn)
    td.column('deleted', BooleanColumn, default='False')
    td.column('delete_reason', StringColumn)
    td.column('delete_timestamp', DatetimeColumn)
    td.column('local_case_id', StringColumn)
    td.column('person_id', ReferenceColumn, references = 'persons')
    td.column('syndrome_id', ReferenceColumn, references = 'syndrome_types')
    td.column('case_status', StringColumn)
    td.column('case_assignment', StringColumn)
    td.column('notification_datetime', DatetimeColumn)
    td.column('onset_datetime', DatetimeColumn)
    td.column('notifier_name', StringColumn)
    td.column('notifier_contact', StringColumn)
    td.column('notes', StringColumn)
    td.order_by_cols('onset_datetime')
    td.add_index('c_person_idx', ['person_id'])
    td.add_index('c_deleted_idx', ['deleted'])
    td.add_index('c_case_status_idx', ['case_status'])
    td.add_index('c_case_assignment_idx', ['case_assignment'])
    td.add_index('c_syndrome_idx', ['syndrome_id'])
    td.add_index('c_local_idx', ['local_case_id'])

    td = db.new_table('case_acl')
    td.column('case_acl_id', SerialColumn, primary_key = True)
    td.column('unit_id', ReferenceColumn, references = 'units')
    td.column('case_id', ReferenceColumn, 
              references = 'cases', on_delete = 'cascade')
    td.add_index('cacl_unit_idx', ['unit_id'])
    td.add_index('cacl_case_idx', ['case_id'])

    td = db.new_table('case_form_summary')
    td.column('summary_id', SerialColumn, primary_key = True)
    td.column('case_id', ReferenceColumn, references = 'cases', 
              on_delete='cascade')
    td.column('form_label', ReferenceColumn, references = 'forms',
              on_update='cascade')
    td.column('form_version', IntColumn)
    td.column('form_date', DatetimeColumn, default = 'CURRENT_TIMESTAMP')
    td.column('data_src', StringColumn)
    td.column('deleted', BooleanColumn, default='False')
    td.column('delete_reason', StringColumn)
    td.column('delete_timestamp', DatetimeColumn)
    td.column('summary', StringColumn)
    td.order_by_cols('form_date')
    td.add_index('cfs_case_idx', ['case_id'])

    td = db.new_table('workqueues')
    td.column('queue_id', SerialColumn, primary_key = True)
    td.column('name', StringColumn)
    td.column('description', StringColumn)
    td.column('unit_id', ReferenceColumn, 
        references = 'units', on_delete = 'cascade', unique=True)
    td.column('user_id', ReferenceColumn, 
        references = 'users', on_delete = 'cascade', unique=True)
    td.add_index('wq_name_idx', ['name'], unique=True)

    td = db.new_table('workqueue_members')
    td.column('wqm_id', SerialColumn, primary_key = True)
    td.column('queue_id', ReferenceColumn, 
        references = 'workqueues', on_delete = 'cascade')
    td.column('unit_id', ReferenceColumn, 
        references = 'units', on_delete = 'cascade')
    td.column('user_id', ReferenceColumn, 
        references = 'users', on_delete = 'cascade')
    td.add_index('wqm_queue_idx', ['queue_id'])
    td.add_index('wqm_unit_idx', ['unit_id'])
    td.add_index('wqm_user_idx', ['user_id'])
    td.add_index('wqm_qunit_idx', ['queue_id', 'unit_id'], unique=True)
    td.add_index('wqm_quser_idx', ['queue_id', 'user_id'], unique=True)

    td = db.new_table('tasks')
    td.column('task_id', SerialColumn, primary_key = True)
    td.column('parent_task_id', ReferenceColumn, 
                references = 'tasks', on_delete = 'cascade')
    td.column('queue_id', ReferenceColumn, references = 'workqueues')
    td.column('action', IntColumn)
    td.column('active_date', DatetimeColumn, default = 'CURRENT_TIMESTAMP')
    td.column('due_date', DatetimeColumn)
    td.column('completed_by_id', ReferenceColumn, 
                references = 'users', on_delete = 'SET NULL')
    td.column('completed_date', DatetimeColumn)
    td.column('locked_by_id', ReferenceColumn, 
                references = 'users', on_delete = 'SET NULL')
    td.column('locked_date', DatetimeColumn)
    td.column('task_description', StringColumn)
    td.column('annotation', StringColumn)
    td.column('case_id', ReferenceColumn, 
                references = 'cases', on_delete = 'SET NULL')
    td.column('form_name', ReferenceColumn, 
                references='forms', on_delete='SET NULL', on_update='CASCADE')
    td.column('summary_id', ReferenceColumn, 
                references = 'case_form_summary', on_delete = 'SET NULL')
    td.column('assigner_id', ReferenceColumn, 
                references = 'users', on_delete = 'SET NULL')
    td.column('assignment_date', DatetimeColumn, 
                default = 'CURRENT_TIMESTAMP')
    td.column('originator_id', ReferenceColumn, 
                references = 'users', on_delete = 'SET NULL')
    td.column('creation_date', DatetimeColumn, default = 'CURRENT_TIMESTAMP')
    td.add_index('tasks_queue_idx', ['queue_id'])
    td.add_index('tasks_active_date_idx', ['active_date'])
    td.add_index('tasks_completed_date_idx', ['completed_date'])
    td.add_index('tasks_assigner_idx', ['assigner_id'])

    td = db.new_table('bulletins')
    td.column('bulletin_id', SerialColumn, primary_key = True)
    td.column('post_date', DatetimeColumn, default = 'CURRENT_TIMESTAMP')
    td.column('expiry_date', DatetimeColumn)
    td.column('title', StringColumn, size = 60)
    td.column('synopsis', StringColumn)
    td.column('detail', StringColumn)
    td.order_by_cols('post_date')
    td.add_index('b_post_idx', ['post_date'])
    td.add_index('b_expiry_idx', ['expiry_date'])

    td = db.new_table('group_bulletins')
    td.column('group_bulletins_id', SerialColumn, primary_key = True)
    td.column('bulletin_id', ReferenceColumn, 
              references = 'bulletins', on_delete = 'cascade')
    td.column('group_id', ReferenceColumn, 
              references = 'groups', on_delete = 'cascade')
    td.add_index('gb_bulletin_idx', ['bulletin_id'])
    td.add_index('gb_group_idx', ['group_id'])

    td = db.new_table('person_phonetics')
    td.column('person_id', ReferenceColumn, 
              references = 'persons', on_delete = 'cascade')
    td.column('phonetics', StringColumn)
    td.add_index('pp_person_id_idx', ['person_id'])
    td.add_index('pp_phonetics_idx', ['phonetics'])

    td = db.new_table('report_params')
    td.column('report_params_id', SerialColumn, primary_key = True)
    td.column('label', StringColumn)
    td.column('type', StringColumn)
    td.column('sharing', StringColumn)
    td.column('syndrome_id', ReferenceColumn, 
              references = 'syndrome_types', on_delete = 'cascade')
    td.column('unit_id', ReferenceColumn, 
        references = 'units', on_delete = 'cascade')
    td.column('user_id', ReferenceColumn, 
        references = 'users', on_delete = 'cascade')
    td.column('pickle', StringColumn)
    td.column('xmldef', StringColumn)
    td.add_index('rp_label_idx', ['label'])
    td.add_index('rp_type_idx', ['type'])
    td.add_index('rp_sharing_idx', ['sharing'])
    td.add_index('rp_unit_idx', ['unit_id'])
    td.add_index('rp_user_idx', ['user_id'])

    td = db.new_table('dupe_persons')
    td.column('low_person_id', ReferenceColumn, 
              references='persons', primary_key=True, on_delete='cascade')
    td.column('high_person_id', ReferenceColumn, 
              references='persons', primary_key=True, on_delete='cascade')
    td.column('status', StringColumn, size=1)
    td.column('confidence', FloatColumn)
    td.column('exclude_reason', StringColumn)
    td.column('timechecked', DatetimeColumn, default = 'CURRENT_TIMESTAMP')
    td.add_index('dp_timechecked_idx', ['timechecked'])

    td = db.new_table('address_states')
    td.column('address_states_id', SerialColumn, primary_key = True)
    td.column('code', StringColumn)
    td.column('label', StringColumn)

    td = db.new_table('import_defs')
    td.column('import_defs_id', SerialColumn, primary_key = True)
    td.column('name', StringColumn)
    td.column('syndrome_id', ReferenceColumn, 
              references = 'syndrome_types', on_delete = 'cascade')
    td.column('xmldef', StringColumn)
    td.add_index('id_name_idx', ['name'])

    td = db.new_table('nicknames')
    td.column('nick', StringColumn)
    td.column('alt', StringColumn)
    td.add_index('nick_idx', ['nick'])
    td.add_index('nick_alt_idx', ['nick', 'alt'])

    td = db.new_table('casesets')
    td.column('caseset_id', SerialColumn, primary_key = True)
    td.column('name', StringColumn)
    td.column('dynamic', BooleanColumn)
    td.column('unit_id', ReferenceColumn, 
        references = 'units', on_delete = 'cascade')
    td.column('user_id', ReferenceColumn, 
        references = 'users', on_delete = 'cascade')
    td.column('pickle', BinaryColumn)
    td.add_index('cs_label_idx', ['name'])

    return db

if __name__ == '__main__':
    import config
    dsn = sys.argv[1]
    define_db(dsn).make_database(config.web_user)
