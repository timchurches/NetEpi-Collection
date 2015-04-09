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

"""
Perform any necessary schema changes.
"""

import os, sys
import textwrap
from cocklebur import dbobj, form_ui

class UPMeta(type):

    def __init__(cls, name, bases, dict):
        if 'test' in dict:
            cls.upgrades.append(cls)


class Upgrades(object):

    """
    Upgrades maintains a registry of all subclasses (thanks to UPMeta), runs
    their .test() methods in reverse order, and then runs the appropriate
    .upgrade() methods.
    """

    __metaclass__ = UPMeta
    upgrades = []

    def __init__(self, db, target_dir):
        self.db = db
        self.target_dir = target_dir

    def msg(self, text):
        text = ' '.join([line.strip() for line in text.splitlines()])
        print textwrap.fill(text, initial_indent='  schema upgrade: ', 
                            subsequent_indent='    ')

    def abort(self, text):
        text = ' '.join([line.strip() for line in text.splitlines()])
        text = textwrap.wrap(text, initial_indent='Schema upgrade ABORTED: ', 
                             subsequent_indent='    ')
        tear = '!' * 80
        sys.exit('\n'.join([tear] + text + [tear]))

    def run(self):
        try:
            self.db.cursor().close()
        except dbobj.DatabaseError:
            return            # Probably new DB
        needed = []
        for upg_cls in self.upgrades[::-1]:
            upg = upg_cls(self.db, self.target_dir)
            if upg.test():
                break
            needed.append(upg)
        for upg in needed[::-1]:
            self.msg(upg.__doc__)
            try:
                upg.upgrade()
            except dbobj.DatabaseError, e:
                sys.exit(e)

    def has_relation(self, name):
        return self.db.db_has_relation(name)

    def has_col(self, tablecol):
        table, col = tablecol.split('.')
        if not self.has_relation(table):
            return False
        curs = self.db.cursor()
        try:
            try:
                dbobj.execute(curs, 'SELECT %s FROM %s LIMIT 0' % (col, table))
            except dbobj.DatabaseError:
                self.db.rollback()
                return False
            else:
                return True
        finally:
            curs.close()

    def update_constraint(self, ltable, ftable, updtype, deltype, *sql):
        # types: 
        #    a - no action (default)
        #    c - cascade
        #    n - null
        if self.has_relation(ltable) and self.has_relation(ftable):
            curs = self.db.cursor()
            try:
                dbobj.execute(curs, "SELECT conname"
                                "  FROM pg_constraint"
                                "  JOIN pg_class AS l ON (l.oid = conrelid)"
                                "  JOIN pg_class AS f ON (f.oid = confrelid)"
                                "  WHERE l.relname = %s"
                                "    AND f.relname = %s"
                                "    AND confupdtype = %s"
                                "    AND confdeltype = %s", 
                                (ltable, ftable, updtype, deltype))
                rows = curs.fetchall()
                if len(rows) == 1:
                    rel = rows[0][0]
                    # print 'schema upgrade: constraint %r on %r' % (rel, ltable)
                    dbobj.execute(curs, 'ALTER TABLE %s DROP CONSTRAINT "%s"' % 
                                            (ltable, rel))
                    for cmd in sql:
                        dbobj.execute(curs, cmd)
            finally:
                curs.close()

    def agg(self, cmd, *args):
        curs = self.db.cursor()
        try:
            dbobj.execute(curs, cmd, args)
            row = curs.fetchone()
            assert row is not None and len(row) == 1
            return row[0]
        finally:
            curs.close()

    def __call__(self, cmd):
        curs = self.db.cursor()
        try:
            dbobj.execute(curs, cmd)
        finally:
            curs.close()


class _UG(Upgrades):
    """
    add case_id on user_log [1367] (20050428-1)
    """

    def test(self):
        return self.has_col('user_log.case_id')

    def upgrade(c):
        c('ALTER TABLE user_log ADD COLUMN case_id INTEGER'
            ' REFERENCES cases(case_id) ON DELETE CASCADE')
        c('CREATE INDEX ul_case_id_idx ON user_log (case_id)')


class _UG(Upgrades):
    """
    users.rights column added [1533] 20060208-1
    """

    def test(self):
        return self.has_col('users.rights')

    def upgrade(c):
        c('CREATE TABLE users_old (LIKE users)')
        c('INSERT INTO users_old SELECT * FROM users')
        c('ALTER TABLE users ADD COLUMN rights TEXT')
        c("UPDATE users SET rights='ADMIN' WHERE admin=true")
        c('ALTER TABLE users DROP COLUMN admin')


class _UG(Upgrades):
    """
    users.preferences column added [1545] 20060209-1
    """

    def test(self):
        return self.has_col('users.preferences')

    def upgrade(c):
        c('ALTER TABLE users ADD COLUMN preferences BYTEA')
        c("UPDATE groups SET rights='ACCESSALL' WHERE rights='DOH'")


class _UG(Upgrades):
    """
    XML forms [1581]
    """

    def test(self):
        return self.has_relation('form_defs')

    def upgrade(c):
        c('CREATE TABLE form_defs ('
          '    name TEXT,'
          '    version INTEGER,'
          '    xmldef TEXT'
          ') WITH OIDS')
        form_dir = os.path.join(self.target_dir, 'forms')
        if not os.path.exists(form_dir):
            return
        srclib = form_ui.FormLibPyFiles(form_dir)
        dstlib = form_ui.FormLibXMLDB(self.db, 'form_defs')
        if len(srclib) > 0 and len(dstlib) == 0:
            for entry in srclib:
                try:
                    form = entry.load()
                except form_ui.FormError, e:
                    raise 'ERROR loading %r: %s' % (entry, e)
                else:
                    dstlib.save(form, entry.name, entry.version)


class _UG(Upgrades):
    """
    def_update_time column added to forms [1631] 20060404-1
    """

    def test(self):
        return self.has_col('forms.def_update_time')

    def upgrade(c):
        c('ALTER TABLE forms ADD COLUMN def_update_time timestamp')


class _UG(Upgrades):
    """
    DOB_is_approx, interpreter_req added to persons [1671] 20060501-1
    """

    def test(self):
        return self.has_col('persons.DOB_is_approx')

    def upgrade(c):
        c('ALTER TABLE persons ADD COLUMN DOB_is_approx BOOLEAN')
        c('ALTER TABLE persons ALTER COLUMN DOB_is_approx SET DEFAULT FALSE')
        c('ALTER TABLE persons ADD COLUMN interpreter_req VARCHAR')


class _UG(Upgrades):
    """
    Configurable demographic fields [1666]
    """

    def test(self):
        return self.has_relation('syndrome_demog_fields')

    def upgrade(c):
        c('CREATE TABLE syndrome_demog_fields ('
          '    synddf_id SERIAL PRIMARY KEY,'
          '    syndrome_id INTEGER REFERENCES syndrome_types(syndrome_id)'
          '             ON DELETE cascade,'
          '    name TEXT,'
          '    label TEXT,'
          '    show_case BOOLEAN DEFAULT True,'
          '    show_form BOOLEAN DEFAULT True,'
          '    show_search BOOLEAN DEFAULT True,'
          '    show_person BOOLEAN DEFAULT True'
          ') WITH OIDS')


class _UG(Upgrades):
    """
    Per-syndrome case status [1676]
    """

    def test(self):
        return self.has_relation('syndrome_case_status')

    def upgrade(c):
        c('CREATE TABLE syndrome_case_status ('
          '    syndcs_id SERIAL PRIMARY KEY,'
          '    syndrome_id INTEGER REFERENCES syndrome_types(syndrome_id)'
          '             ON DELETE cascade,'
          '    name TEXT,'
          '    label TEXT'
          ') WITH OIDS')


class _UG(Upgrades):
    """
    person mobile, fax, e-mail and passport [1726] added 2006-05-10
    """

    def test(self):
        return self.has_col('persons.mobile_phone')

    def upgrade(c):
        c('ALTER TABLE persons ADD COLUMN mobile_phone VARCHAR')
        c('ALTER TABLE persons ADD COLUMN fax_phone VARCHAR')
        c('ALTER TABLE persons ADD COLUMN e_mail VARCHAR')
        c('ALTER TABLE persons ADD COLUMN passport_number VARCHAR')
        c('ALTER TABLE persons ADD COLUMN passport_country VARCHAR')


class _UG(Upgrades):
    """
    Unified cases & contacts, branch merge [1761] [1831] 2006-05-19
    """

    def test(self):
        return self.has_col('cases.master_id')

    def upgrade(c):
        c('CREATE TABLE contact_syndromes ('
          '    cs_id SERIAL PRIMARY KEY,'
          '    syndrome_id INTEGER REFERENCES syndrome_types(syndrome_id)'
          '             ON DELETE cascade,'
          '    contact_syndrome_id INTEGER REFERENCES syndrome_types(syndrome_id)'
          '             ON DELETE cascade'
          ') WITH OIDS')
        c('ALTER TABLE cases ADD COLUMN master_id INT')
        c('ALTER TABLE cases ADD FOREIGN KEY (master_id)'
                    ' REFERENCES cases(case_id)')
        c('ALTER TABLE cases ADD COLUMN master_syndrome_id int')
        c('ALTER TABLE cases ADD FOREIGN KEY (master_syndrome_id)'
                    ' REFERENCES syndrome_types(syndrome_id)')
        c('UPDATE cases SET master_id=case_id WHERE master_id IS null')
        c('UPDATE cases SET master_syndrome_id=syndrome_id')
        c('UPDATE cases SET master_id=case_contacts.case_id'
          ' WHERE cases.case_id=case_contacts.contact_id')
        c('UPDATE cases SET master_syndrome_id=tmp.syndrome_id'
          ' FROM cases AS tmp'
          ' WHERE cases.master_id=tmp.case_id')
        c('DROP TABLE case_contacts')
        c('ALTER TABLE case_acl RENAME case_id TO master_id')


class _UG(Upgrades):
    """
    add show_result to syndrome_demog_fields after [1863]
    """

    def test(self):
        return self.has_col('syndrome_demog_fields.show_result')

    def upgrade(c):
        c('ALTER TABLE syndrome_demog_fields ADD COLUMN show_result BOOLEAN')
        c('ALTER TABLE syndrome_demog_fields'
          ' ALTER COLUMN show_result SET DEFAULT TRUE')


class _UG(Upgrades):
    """
    logical delete cases after [1879] [1880]
    """

    def test(self):
        return self.has_col('cases.deleted')

    def upgrade(c):
        c('ALTER TABLE cases ADD COLUMN deleted BOOLEAN')
        c('ALTER TABLE cases ALTER COLUMN deleted SET DEFAULT FALSE')
        c("UPDATE cases SET deleted=TRUE WHERE case_status='excluded'")
        c('UPDATE cases SET deleted=FALSE WHERE deleted IS NULL')
        c('CREATE INDEX c_deleted_idx ON cases (deleted)')


class _UG(Upgrades):
    """
    workflow-lite [2042]
    """

    def test(self):
        return self.has_relation('tasks')

    def upgrade(c):
        c('CREATE TABLE workqueues ('
          '    queue_id SERIAL PRIMARY KEY,'
          '    name TEXT,'
          '    description TEXT,'
          '    unit_id INTEGER REFERENCES units(unit_id) ON DELETE cascade UNIQUE,'
          '    user_id INTEGER REFERENCES users(user_id) ON DELETE cascade UNIQUE'
          ') WITH OIDS')
        c('CREATE TABLE workqueue_members ('
          '    wqm_id SERIAL PRIMARY KEY,'
          '    queue_id INTEGER REFERENCES workqueues(queue_id) ON DELETE cascade,'
          '    unit_id INTEGER REFERENCES units(unit_id) ON DELETE cascade,'
          '    user_id INTEGER REFERENCES users(user_id) ON DELETE cascade'
          ') WITH OIDS')
        c('CREATE TABLE tasks ('
          '    task_id SERIAL PRIMARY KEY,'
          '    parent_task_id INTEGER REFERENCES tasks(task_id) ON DELETE cascade,'
          '    queue_id INTEGER REFERENCES workqueues(queue_id),'
          '    action INTEGER,'
          '    active_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,'
          '    due_date TIMESTAMP,'
          '    completed_by_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL,'
          '    completed_date TIMESTAMP,'
          '    locked_by_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL,'
          '    locked_date TIMESTAMP,'
          '    task_description TEXT,'
          '    annotation TEXT,'
          '    master_id INTEGER REFERENCES cases(case_id) ON DELETE SET NULL,'
          '    case_id INTEGER REFERENCES cases(case_id) ON DELETE SET NULL,'
          '    form_name VARCHAR(20) REFERENCES forms(label) ON DELETE SET NULL,'
          '    summary_id INTEGER REFERENCES case_form_summary(summary_id) ON DELETE SET NULL,'
          '    assigner_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL,'
          '    assignment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,'
          '    originator_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL,'
          '    creation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
          ') WITH OIDS')


class _UG(Upgrades):
    """
    0.95: fix form_name constrain [2069], indigenous_status to persons
    [2071], additional_info to syndrome_types [2083]
    """

    def test(self):
        return self.has_col('persons.indigenous_status')

    def upgrade(c):
        c.update_constraint('tasks', 'forms', 'a', 'n',
                          'ALTER TABLE tasks ADD'
                          '  FOREIGN KEY (form_name) REFERENCES forms(label)'
                          '  ON DELETE SET NULL ON UPDATE CASCADE')
        c('ALTER TABLE persons ADD COLUMN indigenous_status TEXT')
        c('CREATE INDEX p_indigenous_status_idx ON persons (indigenous_status)')
        c('syndrome_types', 'additional_info',
          'ALTER TABLE syndrome_types ADD COLUMN additional_info TEXT')


class _UG(Upgrades):
    """
    0.96: master_id to user_log [2238], alt addr to persons [2293],
    fix case_form_summary constraint [2301]
    """

    def test(self):
        return self.has_col('user_log.master_id')

    def upgrade(c):
        c('ALTER TABLE user_log ADD COLUMN master_id INT REFERENCES cases')
        c('UPDATE user_log SET master_id = case_id')
        c('ALTER TABLE persons ADD COLUMN alt_street_address TEXT')
        c('ALTER TABLE persons ADD COLUMN alt_locality TEXT')
        c('ALTER TABLE persons ADD COLUMN alt_state TEXT')
        c('ALTER TABLE persons ADD COLUMN alt_postcode TEXT')
        c.update_constraint('case_form_summary', 'cases', 'a', 'a',
                          'ALTER TABLE case_form_summary ADD'
                          '  FOREIGN KEY (case_id) REFERENCES cases(case_id)'
                          '  ON DELETE CASCADE')


class _UG(Upgrades):
    """
    Report-lite [2395]
    """

    def test(self):
        return self.has_relation('report_params')

    def upgrade(c):
        c('CREATE TABLE report_params ('
          ' report_params_id SERIAL PRIMARY KEY,'
          ' label TEXT,'
          ' syndrome_id INTEGER REFERENCES syndrome_types(syndrome_id)'
          '     ON DELETE cascade,'
          ' unit_id INTEGER REFERENCES units(unit_id) ON DELETE cascade,'
          ' user_id INTEGER REFERENCES users(user_id) ON DELETE cascade,'
          ' pickle TEXT'
          ') WITH OIDS')
        c('CREATE INDEX rp_label_idx ON report_params (label)')


class _UG(Upgrades):
    """
    duplicate person scan exclusions [2499]
    """

    def test(self):
        return self.has_relation('nondupe_persons')

    def upgrade(c):
        c('CREATE TABLE nondupe_persons ('
          ' low_person_id INTEGER REFERENCES persons(person_id)'
          '     ON DELETE cascade,'
          ' high_person_id INTEGER REFERENCES persons(person_id)'
          '     ON DELETE cascade,'
          ' exclude_reason TEXT'
          ') WITH OIDS')
        c('CREATE UNIQUE INDEX ndp_uniq'
          '     ON nondupe_persons (low_person_id,high_person_id)')


class _UG(Upgrades):
    """
    localisation of address states [2769]
    """

    def test(self):
        return self.has_relation('address_states')

    def upgrade(c):
        c('CREATE TABLE address_states ('
          '     address_states_id SERIAL PRIMARY KEY, '
          '     syndrome_id INTEGER REFERENCES syndrome_types(syndrome_id) '
          '         ON DELETE cascade,'
          '     code TEXT,'
          '     label TEXT'
          ') WITH OIDS')


class _UG(Upgrades):
    """
    1.0.4: logical user delete [2908]
    """

    def test(self):
        return self.has_col('users.deleted')

    def upgrade(c):
        c('ALTER TABLE users ADD COLUMN deleted BOOLEAN')
        c('UPDATE users SET deleted=false')
        c('ALTER TABLE users ALTER deleted SET DEFAULT false')


class _UG(Upgrades):
    """
    1.0.5: explicit syndrome ordering [3012]
    """

    def test(self):
        return self.has_col('syndrome_types.priority')

    def upgrade(c):
        c('ALTER TABLE syndrome_types ADD COLUMN priority INTEGER')
        c('UPDATE syndrome_types SET priority=3')


class _UG(Upgrades):
    """
    data import (import_defs table) [3120]
    """

    def test(self):
        return self.has_relation('import_defs')

    def upgrade(c):
        c('CREATE TABLE import_defs ('
          ' import_defs_id SERIAL PRIMARY KEY,'
          ' name TEXT,'
          ' syndrome_id INTEGER REFERENCES syndrome_types(syndrome_id) '
          '     ON DELETE cascade,'
          ' xmldef TEXT'
          ') WITH OIDS')
        c('CREATE INDEX id_name_idx ON import_defs (name)')


class _UG(Upgrades):
    """
    1.1.0: Additional person fields (work address, second passport,
    occupation, etc) [3126] [3130] [3142] [3143] [3149] [3281]
    """

    def test(self):
        return self.has_col('persons.work_street_address')

    def upgrade(c):
        # work address [3126]
        c('ALTER TABLE persons ADD COLUMN work_street_address TEXT')
        c('ALTER TABLE persons ADD COLUMN work_locality TEXT')
        c('ALTER TABLE persons ADD COLUMN work_state TEXT')
        c('ALTER TABLE persons ADD COLUMN work_postcode TEXT')
        # second passport, occupation [3130]
        c('ALTER TABLE persons ADD COLUMN passport_number_2 TEXT')
        c('ALTER TABLE persons ADD COLUMN passport_country_2 TEXT')
        c('ALTER TABLE persons ADD COLUMN occupation TEXT')
        # address country [3142]
        c('ALTER TABLE persons ADD COLUMN country TEXT')
        c('ALTER TABLE persons ADD COLUMN alt_country TEXT')
        c('ALTER TABLE persons ADD COLUMN work_country TEXT')
        # case notes [3143]
        c('ALTER TABLE cases ADD COLUMN notes TEXT')
        # notifier name and contact details [3149]
        c('ALTER TABLE cases ADD COLUMN notifier_name TEXT')
        c('ALTER TABLE cases ADD COLUMN notifier_contact TEXT')
        # data_src [3281]
        c('ALTER TABLE persons ADD COLUMN data_src TEXT')


class _UG(Upgrades):
    """
    nickname remapping table [3180]
    """

    def test(self):
        return self.has_relation('nicknames')

    def upgrade(c):
        c('CREATE TABLE nicknames ('
          '  nick TEXT,'
          '  alt TEXT'
          ') WITH OIDS')
        c('CREATE INDEX nick_idx ON nicknames (nick)')
        c('CREATE INDEX nick_alt_idx ON nicknames (nick,alt)')


class _UG(Upgrades):
    """
    dupe_persons replaced nondupe_persons after 1.2 [3238]
    """

    def test(self):
        return self.has_relation('dupe_persons')

    def upgrade(c):
        c('''
            CREATE TABLE dupe_persons (
                low_person_id INTEGER REFERENCES persons(person_id) 
                    ON DELETE cascade,
                high_person_id INTEGER REFERENCES persons(person_id) 
                    ON DELETE cascade,
                status VARCHAR(1),
                confidence DOUBLE PRECISION,
                exclude_reason TEXT,
                timechecked TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (low_person_id, high_person_id)
            ) WITH OIDS''')
        c('INSERT INTO dupe_persons (low_person_id, high_person_id, '
          '                          status, exclude_reason)'
          ' SELECT low_person_id, high_person_id, \'E\', exclude_reason'
          '  FROM nondupe_persons')
        c('DROP TABLE nondupe_persons')


class _UG(Upgrades):
    """
    1.3.0: unit/group retasked into roles and contexts [3530] 
    [3535] [3548], formimport [3637]
    """

    def test(self):
        return self.has_col('users.title')

    def upgrade(c):
        c('ALTER TABLE users RENAME role TO title')
        c('ALTER TABLE units ADD COLUMN rights VARCHAR')
        c('ALTER TABLE groups ALTER rights TYPE VARCHAR')
        c('ALTER TABLE users ADD COLUMN privacy VARCHAR')
        c('ALTER TABLE users ADD COLUMN checked_timestamp TIMESTAMP')
        c('ALTER TABLE users ADD COLUMN agency VARCHAR')
        c('ALTER TABLE users ADD COLUMN expertise VARCHAR')
        c('ALTER TABLE case_form_summary ADD COLUMN data_src VARCHAR')


class _UG(Upgrades):
    """
    1.4.0: report types [3772] [3649]
    """

    def test(self):
        return self.has_col('report_params.type')

    def upgrade(c):
        c('ALTER TABLE report_params ADD COLUMN type TEXT')
        c("UPDATE report_params SET type='line'")
        c('ALTER TABLE units DROP password')


class _UG(Upgrades):
    """
    1.4.6: last_update on users, persons, cases [3943], [3944]
    """

    def test(self):
        return self.has_col('users.last_update')

    def upgrade(c):
        c('ALTER TABLE users ADD COLUMN last_update TIMESTAMP')
        c('ALTER TABLE persons ADD COLUMN last_update TIMESTAMP')
        c('ALTER TABLE cases ADD COLUMN last_update TIMESTAMP')
        c('ALTER TABLE cases ADD COLUMN delete_reason TEXT')
        c('ALTER TABLE cases ADD COLUMN delete_timestamp TIMESTAMP')


class _UG(Upgrades):
    """
    1.5.0: logical form delete 
    """
    def test(self):
        return self.has_col('case_form_summary.deleted')

    def upgrade(c):
        c('ALTER TABLE case_form_summary ADD COLUMN deleted BOOLEAN')
        c('UPDATE case_form_summary SET deleted=false')
        c('ALTER TABLE case_form_summary ALTER deleted SET DEFAULT false')
        c('ALTER TABLE case_form_summary ADD COLUMN delete_reason TEXT')
        c('ALTER TABLE case_form_summary ADD COLUMN delete_timestamp TIMESTAMP')


class _UG(Upgrades):
    """
    1.5.0: master/contact case relationship replaced with bidirectional
    association.

    *** WARNING *** 
    case/contact relationship is now many-to-many, and contact syndromes
    (case definitions) have been deprecated in favour of using a single
    syndrome (case definition) for both cases and contacts, with "contact
    only" status indicated via case status.
    """

    def test(self):
        return self.has_relation('case_contacts')

    def upgrade(c):
        c('CREATE TABLE contact_types ('
          '  contact_type_id SERIAL PRIMARY KEY,'
          '  contact_type VARCHAR'
          ') WITH OIDS')
        c('CREATE TABLE case_contacts ('
          '  case_id INT REFERENCES cases(case_id)'
          '         ON UPDATE cascade ON DELETE cascade,'
          '  contact_id INT REFERENCES cases(case_id)'
          '         ON UPDATE cascade ON DELETE cascade,'
          '  contact_type_id INT REFERENCES contact_types(contact_type_id)'
          '         ON DELETE SET NULL,'
          '  contact_date TIMESTAMP,'
          '  PRIMARY KEY (case_id, contact_id)'
          ') WITH OIDS')
        # Duplicate case ACL to contacts
        c('INSERT INTO case_acl (master_id, unit_id)'
          '    SELECT case_id, unit_id FROM case_acl'
          '        JOIN cases USING (master_id)'
          '        WHERE master_id != case_id')
        c('ALTER TABLE case_acl RENAME master_id TO case_id')
        # Copy master_id<>case_id relationship 
        c('INSERT INTO case_contacts (case_id, contact_id)'
          '    SELECT master_id, case_id FROM cases'
          '        WHERE master_id != case_id')
        c('INSERT INTO case_contacts (contact_id, case_id)'
          '    SELECT master_id, case_id FROM cases'
          '        WHERE master_id != case_id')
        # Remap contact task actions
        c('UPDATE tasks SET action=action-4 WHERE action IN (5,6,7,8)')
        # Remove redundant columns
        c('ALTER TABLE cases DROP master_id')
        c('ALTER TABLE cases DROP master_syndrome_id')
        c('ALTER TABLE tasks DROP master_id')
        c('ALTER TABLE user_log DROP master_id')
        # Remove redundant tables
        c('DROP TABLE contact_syndromes')


class _UG(Upgrades):
    """
    1.5.0: casesets
    """

    def test(self):
        return self.has_relation('casesets')

    def upgrade(c):
        c('CREATE TABLE casesets ('
          '  caseset_id SERIAL PRIMARY KEY,'
          '  name VARCHAR,'
          '  dynamic BOOLEAN,'
          '  unit_id INTEGER REFERENCES units(unit_id) ON DELETE cascade,'
          '  user_id INTEGER REFERENCES users(user_id) ON DELETE cascade,'
          '  pickle BYTEA'
          ') WITH OIDS')


class _UG(Upgrades):
    """
    1.5.0: case tags (exposures)
    """
    def test(self):
        return self.has_relation('tags')

    def upgrade(c):
        c('CREATE TABLE tags ('
          '  tag_id SERIAL PRIMARY KEY,'
          '  tag VARCHAR,'
          '  notes VARCHAR'
          ') WITH OIDS')
        c('CREATE TABLE case_tags ('
          '  case_tag_id SERIAL PRIMARY KEY,'
          '  case_id INT REFERENCES cases(case_id)'
          '         ON UPDATE cascade ON DELETE cascade,'
          '  tag_id INT REFERENCES tags(tag_id)'
          '         ON UPDATE cascade ON DELETE cascade'
          ') WITH OIDS')
        c('ALTER TABLE users ALTER password TYPE VARCHAR')


class _UG(Upgrades):
    """
    1.5.0: new user sponsorship
    """
    def test(self):
        return self.has_col('users.sponsoring_user_id')

    def upgrade(c):
        c('ALTER TABLE users ADD COLUMN sponsoring_user_id INTEGER'
          ' REFERENCES users(user_id) ON DELETE SET NULL')
        c('ALTER TABLE users ADD COLUMN enable_key VARCHAR')

class _UG(Upgrades):
    """
    1.5.0: remove per-syndrome address state
    """
    def test(self):
        return not self.has_col('address_states.syndrome_id')

    def upgrade(c):
        if c.agg('SELECT count(*) FROM address_states'
                 ' WHERE syndrome_id IS NOT NULL'):
            c.abort('per-syndrome address states have been used.')
        c('ALTER TABLE address_states DROP COLUMN syndrome_id')

class _UG(Upgrades):
    """
    1.5.0: add case assignment
    """
    def test(self):
        return self.has_relation('syndrome_case_assignments')

    def upgrade(c):
        c('ALTER TABLE cases ADD COLUMN case_assignment TEXT')
        c('CREATE TABLE syndrome_case_assignments ('
          '    syndca_id SERIAL PRIMARY KEY,'
          '    syndrome_id INT REFERENCES syndrome_types ON DELETE CASCADE,'
          '    name TEXT,'
          '    label TEXT'
          ') WITH OIDS')

class _UG(Upgrades):
    """
    1.7.0: report sharing & XML parameters
    """

    def test(self):
        return self.has_col('report_params.sharing')

    def upgrade(c):
        from report_1_6.convert import report_cvt
        c('ALTER TABLE report_params ADD COLUMN sharing TEXT')
        c('ALTER TABLE report_params ADD COLUMN xmldef TEXT')
        c('CREATE INDEX rp_type_idx ON report_params (type)')
        c('CREATE INDEX rp_sharing_idx ON report_params (sharing)')
        c('CREATE INDEX rp_unit_idx ON report_params (unit_id)')
        c('CREATE INDEX rp_user_idx ON report_params (user_id)')
        report_cvt(c.db)
        c('ALTER TABLE report_params DROP COLUMN pickle')

class _UG(Upgrades):
    """
    1.7.0: enhanced DOB storage (DOB + precision)
    """

    def test(self):
        return self.has_col('persons.DOB_prec')

    def upgrade(c):
        c('ALTER TABLE persons ADD COLUMN DOB_prec INTEGER')
        c('ALTER TABLE persons ALTER COLUMN DOB_prec SET DEFAULT 0')
        c('UPDATE persons SET DOB_prec = '
            'CASE WHEN dob_is_approx THEN 366 ELSE 0 END')
        c('ALTER TABLE persons DROP COLUMN DOB_is_approx')
