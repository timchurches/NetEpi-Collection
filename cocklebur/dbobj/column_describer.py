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

from mx import DateTime

from cocklebur import datetime
from cocklebur.dbobj import misc, table_extras, dbapi
from cocklebur.dbobj.execute import execute


class ColumnType:

    primary_key = False
    unique = False
    default = None
    obscure = False
    auto_timestamp = False

    def __init__(self, table_desc, name, **kwargs):
        self.__dict__.update(kwargs)
        self.table_desc = table_desc
        self.name = name

    def to_user(self, value):
        """ Convert from internal representation to user representation """
        return value

    def from_user(self, value):
        """ Convert from user representation to internal representation """
        return value

    def to_sql(self, value):
        """ Convert from internal representation to sql representation """
        return value

    def from_sql(self, value):
        """ Convert from sql representation to internal representation """
        return value

    def dependancies(self):
        return []

    def create_sql(self, col_sql):
        col = [self.name, self.sql_type()]
        if self.unique:
            col.append('UNIQUE')
        if self.default:
            col.append('DEFAULT %s' % self.default)
        col_sql.append(' '.join(col))

    def initial_value(self):
        return None

    def reset_sequences(self, curs):
        pass


class StringColumn(ColumnType):

    size = None

    def to_sql(self, value):
        if value and self.size and len(value) > self.size:
            raise dbapi.ValidationError('%s: max field size is %s' %\
                                        (self.name, self.size))
        return value

    def from_user(self, value):
        if value is '':
            return None
        return value

    def sql_type(self):
        if self.size:
            return 'VARCHAR(%d)' % self.size
        else:
            return 'TEXT'


class PasswdColumn(StringColumn):
    # At this time, a password column is just a string column that knows to
    # obscure itself when being pretty-printed.
    obscure = True


class IntColumn(ColumnType):

    def from_user(self, value):
        if isinstance(value, basestring):
            if not value:
                return None
            try:
                return int(value)
            except (ValueError, TypeError):
                pass
        return value

    def to_sql(self, value):
        if value is not None:
            try:
                value = int(value)
            except ValueError:
                raise dbapi.ValidationError('%s: field must be an integer' %
                                            self.name)
        return value

    def sql_type(self):
        return 'INTEGER'


class SequenceExtra(table_extras.TableExtra):

    needs_grant = True

    def __init__(self, table_desc, column):
        self.table_desc = table_desc
        self.name = 'seq_%s_%s' % (column, self.table_desc.name)
        self.column = column

    def pre_create_sql(self):
        if not self.table_desc.db.db_has_relation(self.name):
            return 'CREATE SEQUENCE %s' % self.name

#   OWNED BY introduced in PG 8.2
#    def post_create_sql(self):
#        if not self.table_desc.db.db_has_relation(self.name):
#            return 'ALTER SEQUENCE %s OWNED BY %s.%s' %\
#                (self.name, self.table_desc.name, self.column)

    def post_drop_sql(self):
        if self.table_desc.db.db_has_relation(self.name):
            return 'DROP SEQUENCE %s' % self.name

    def owner(self, curs, owner):
        execute(curs, 'ALTER TABLE %s OWNER TO "%s"' % (self.name, owner))


class SerialColumn(IntColumn): 

    def __init__(self, table_desc, name, **kwargs):
        ColumnType.__init__(self, table_desc, name, **kwargs)
        self.seq = SequenceExtra(table_desc, self.name)
        table_desc.extra(self.seq)

    # Should really be bigint (64 bit)
    #def sql_type(self):
    #    return 'BIGINT'

    def create_sql(self, col_sql):
        self.default = "nextval('%s')" % self.seq.name
        ColumnType.create_sql(self, col_sql)

    def nextval_sql(self):
        return "SELECT nextval('%s')" % self.seq.name

    def reset_sequences(self, curs):
        execute(curs, "SELECT setval('%s',(SELECT max(%s) FROM %s))" %\
            (self.seq.name, self.name, self.table_desc.name))
        curs.fetchone()

class FloatColumn(ColumnType):

    def from_user(self, value):
        if isinstance(value, basestring):
            if not value:
                return None
            try:
                return float(value)
            except (ValueError, TypeError):
                pass
        return value

    def to_sql(self, value):
        if value is not None:
            try:
                value = float(value)
            except ValueError:
                raise dbapi.ValidationError('%s: field must be a decimal number' % self.name)
        return value

    def sql_type(self):
        return 'DOUBLE PRECISION'


class BooleanColumn(ColumnType):

    def from_user(self, value):
        if value:
            return True
        return None

    def to_sql(self, value):
        if value:
            return dbapi.TRUE
        return dbapi.FALSE

    def from_sql(self, value):
        if value:
            return True
        return None

    def to_user(self, value):
        # We do this to work with HTML's <input type="checkbox"> - sorry
        if value:
            return 'True'
        else:
            return ''

    def sql_type(self):
        return 'BOOLEAN'

    def initial_value(self):
        if self.default and self.default[0].lower() == 't':
            return True
        return None


class _DateTimeColumn(ColumnType):

    pass

class DateColumn(_DateTimeColumn):

    def sql_type(self):
        return 'DATE'

    def from_user(self, value):
        try:
            return datetime.mx_parse_date(value)
        except datetime.Error:
            return value

    def to_sql(self, value):
        if value is None:
            return None
        elif isinstance(value, str):
            try:
                return datetime.mx_parse_date(value).mx()
            except datetime.Error, e:
                raise dbapi.ValidationError('%s: %s' % (self.name, e))
        elif isinstance(value, DateTime.DateTimeType):
            return value
        elif isinstance(value, datetime.mx_parse_date):
            return value.mx()
        else:
            raise TypeError('%s: bad column type: %s' % (self.name, type(value)))

    def from_sql(self, value):
        if value is not None:
            return datetime.mx_parse_date(value)


class TimeColumn(_DateTimeColumn):

    def sql_type(self):
        return 'TIME'

    def from_user(self, value):
        try:
            return datetime.mx_parse_time(value)
        except datetime.Error:
            return value

    def to_sql(self, value):
        if value is None:
            return None
        elif isinstance(value, str):
            try:
                return datetime.mx_parse_time(value).mx()
            except datetime.Error, e:
                raise dbapi.ValidationError('%s: %s' % (self.name, e))
        elif isinstance(value, DateTime.DateTimeDeltaType):
            return value
        elif isinstance(value, datetime.mx_parse_time):
            return value.mx()
        else:
            raise TypeError('%s: bad column type: %s' % (self.name, type(value)))

    def from_sql(self, value):
        if value is not None:
            return datetime.mx_parse_time(value)


class DatetimeColumn(_DateTimeColumn):

    def sql_type(self):
        return 'TIMESTAMP'

    def from_user(self, value):
        try:
            return datetime.mx_parse_datetime(value)
        except datetime.Error:
            return value

    def to_sql(self, value):
        if value is None:
            return None
        elif isinstance(value, str):
            try:
                return datetime.mx_parse_datetime(value).mx()
            except datetime.Error, e:
                raise dbapi.ValidationError('%s: %s' % (self.name, e))
        elif isinstance(value, DateTime.DateTimeType):
            return value
        elif isinstance(value, datetime.mx_parse_datetime):
            return value.mx()
        else:
            raise TypeError('%s: bad column type: %s' % (self.name, type(value)))

    def from_sql(self, value):
        if value is not None:
            return datetime.mx_parse_datetime(value)


class LastUpdateColumn(DatetimeColumn):
    """
    A timestamp column that auto-updates for the time of the last update

    Note - special-cased in result.ResultRow
    """
    auto_timestamp = True


class ReferenceColumn(ColumnType):

    on_delete = None
    on_update = None

    def __init__(self, table_desc, name, **kwargs):
        ColumnType.__init__(self, table_desc, name, **kwargs)
        self.ref_col_desc = None
        self.ref_column = None
        self.ref_table, columns = misc.parse_tablecols(self.references)
        if columns:
            if len(columns) > 1:
                raise ValueError('%s: ReferenceColumn cannot specify more than'
                                 ' one target column: %s' % 
                                 (self.name, ', '.join(columns)))
            self.ref_column = columns[0]

    def target_column(self):
        if self.ref_col_desc is None:
            ref_table_desc = self.table_desc.db.get_table(self.ref_table)
            if not self.ref_column:
                assert len(ref_table_desc.primary_keys) == 1
                self.ref_col_desc = ref_table_desc.primary_keys[0]
            else:
                self.ref_col_desc = ref_table_desc.get_column(self.ref_column)
        return self.ref_col_desc

    def dependancies(self):
        return [self.ref_table.lower()]

    def sql_type(self):
        ref_col_desc = self.target_column()
        sql = ['%s REFERENCES %s(%s)' % 
               (ref_col_desc.sql_type(), self.ref_table, ref_col_desc.name)]
        if self.on_delete:
            sql.append('ON DELETE %s' % self.on_delete)
        if self.on_update:
            sql.append('ON UPDATE %s' % self.on_update)
        return ' '.join(sql)

    def to_sql(self, value):
        ref_col_desc = self.target_column()
        return ref_col_desc.to_sql(value)


class BinaryColumn(ColumnType):

    size = None

    def to_sql(self, value):
        return dbapi.Binary(value)

    def sql_type(self):
        return 'BYTEA'

