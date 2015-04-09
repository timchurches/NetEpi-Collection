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
import re
try:
    set
except NameError:
    from sets import Set as set
from cocklebur.dbobj.execute import execute
from cocklebur.dbobj import misc
from cocklebur.dbobj import result
from cocklebur.dbobj import column_describer
from cocklebur.dbobj import table_extras

class IndexDescriber(table_extras.TableExtra):
    def __init__(self, table_desc, name, table, col_names, 
                 unique = False, using = None):
        self.table_desc = table_desc
        self.name = name
        self.table = table
        self.col_names = col_names
        self.unique = unique
        self.using = using

    def create_sql(self):
        if not self.table_desc.db.db_has_relation(self.name):
            sql = ['CREATE']
            if self.unique:
                sql.append('UNIQUE')
            sql.extend(('INDEX', self.name, 'ON', self.table))
            if self.using:
                sql.append(self.using.upper())
            sql.append('(%s)' % ','.join(self.col_names))
            return ' '.join(sql)

    def drop_sql(self):
        return 'DROP INDEX %s' % self.name


class TableDescriber:
    def __init__(self, db, name, row_class = None):
#        assert db.__class__.__name__ == 'DatabaseDescriber'
        misc.valid_identifier(name, 'table identifier', strict=False)
        self.db, self.name = db, name
        self.row_class = row_class or result.ResultRow
        self.columns = []
        self.extras = table_extras.TableExtras()  # Sequences, indecies, etc
        self.columns_by_name = {}
        self.primary_keys = []
        self.order_by = None
        self.order_reversed = False
        self.owned_by = None

    valid_name_re = re.compile('^[a-z_]\w*$', re.IGNORECASE)

    def column(self, name, type, **kwargs):
        misc.valid_identifier(name, 'column identifier', strict=False)
        name = name.lower()
        col_desc = type(self, name, **kwargs)
        if col_desc.primary_key:
            self.primary_keys.append(col_desc)
        col_desc.table_desc = self
        self.columns.append(col_desc)
        self.columns_by_name[name] = col_desc

    def order_by_cols(self, *names):
        self.order_by = names
        self.order_reversed = False

    def reverse_order_by_cols(self, *names):
        self.order_by = names
        self.order_reversed = True

    def extra(self, extra):
        self.extras.append(extra)

    def get_column(self, name):
        return self.columns_by_name[name.lower()]

    def get_columns(self):
        return self.columns

    def get_primary_cols(self):
        return self.primary_keys

    def get_row(self, seed_values=None):
        return self.row_class(self, seed_values=seed_values)

    def add_index(self, name, col_names, **kwargs):
#        name = '%s_%s' % (self.name, name)
        misc.valid_identifier(name, 'index identifier', strict=False)
        self.extra(IndexDescriber(self, name, self.name, col_names, **kwargs))

    def grant(self, curs, user):
        objs = [self.name] + [e.name for e in self.extras if e.needs_grant]
        execute(curs, 
                'GRANT SELECT, UPDATE, INSERT, DELETE, REFERENCES'
                ' ON %s TO "%s"' % (', '.join(objs), user))

    def revoke(self, curs, user):
        objs = [self.name] + [e.name for e in self.extras if e.needs_grant]
        execute(curs, 
                'REVOKE SELECT, UPDATE, INSERT, DELETE, REFERENCES '
                ' ON %s FROM "%s"' % (', '.join(objs), user))

    def owner(self, curs, owner):
        execute(curs, 'ALTER TABLE %s OWNER TO "%s"' % (self.name, owner))
        for extra in self.extras:
            extra.owner(curs, owner)
        self.owned_by = owner

    def create(self, grant=None, owner=None):
        cmds = []
        for extra in self.extras:
            sql = extra.pre_create_sql()
            if sql is not None:
                cmds.append(sql)
        if not self.db.db_has_relation(self.name):
            col_sql = []
            for col in self.columns:
                col.create_sql(col_sql)
            if self.primary_keys:
                pkey_cols = [coldesc.name for coldesc in self.primary_keys]
                col_sql.append('PRIMARY KEY (%s)' % ', '.join(pkey_cols))
            table_sql = [
                'CREATE TABLE %s (' % self.name,
                ',\n'.join(['    %s' % c for c in col_sql]),
                ') WITH OIDS',
                '',
            ]
            cmds.append('\n'.join(table_sql))
        for extra in self.extras:
            sql = extra.post_create_sql()
            if sql is not None:
                cmds.append(sql)
        curs = self.db.cursor()
        try:
            for cmd in cmds:
                execute(curs, cmd)
            if cmds and grant:
                self.grant(curs, grant)
            if cmds and owner:
                self.owner(curs, owner)
        finally:
            curs.close()

    def rename(self, new_name):
        misc.valid_identifier(new_name, 'table identifier', strict=False)
        curs = self.db.cursor()
        try:
            execute(curs, 'ALTER TABLE %s RENAME TO %s' % (self.name, new_name))
            self.name = new_name
        finally:
            curs.close()

    def drop(self):
        if self.db.db_has_relation(self.name):
            curs = self.db.cursor()
            try:
                for extra in self.extras:
                    sql = extra.pre_drop_sql()
                    if sql is not None:
                        execute(curs, sql)
                execute(curs, 'DROP TABLE %s' % self.name)
                # PG drops objects related to the table
                for extra in self.extras:
                    sql = extra.post_drop_sql()
                    if sql is not None:
                        execute(curs, sql)
            finally:
                curs.close()

    def dependancies(self):
        dependancies = set()
        for col_desc in self.columns:
            dependancies.update(col_desc.dependancies())
        dependancies.discard(self.name.lower())
        return dependancies

    def nextval(self, colname):
        col_desc = self.get_column(colname)
        curs = self.db.cursor()
        try:
            execute(curs, col_desc.nextval_sql())
            return curs.fetchone()[0]
        finally:
            curs.close()

    def reset_sequences(self, curs):
        for col_desc in self.columns:
            col_desc.reset_sequences(curs)
