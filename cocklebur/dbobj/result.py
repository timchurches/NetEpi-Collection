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

# Standard lib
import copy

# 3rd party
from mx import DateTime

# Module
from cocklebur.dbobj import dbapi
from cocklebur.dbobj.execute import execute


class _CmdBuilder:
    """
    Build SQL commands bit by bit, with additional help for parameters
    """
    def __init__(self):
        self.cmd = []
        self.args = []

    def append(self, cmd, *args):
        self.cmd.append(cmd)
        self.args.extend(args)

    def append_list_of_names(self, names):
        self.cmd.append('(' + ','.join(names) + ')')

    def append_list_of_values(self, values):
        self.cmd.append('(' + ','.join(['%s'] * len(values)) + ')')
        self.args.extend(values)

    def append_name_value_expr(self, join_str, names, values):
        self.cmd.append(join_str.join(['%s=%%s' % name for name in names]))
        self.args.extend(values)

    def execute(self, curs):
        execute(curs, ' '.join(self.cmd), self.args)

class ColumnValue(object):
    __slots__ = '_initial_value', '_value', '_saved_values'

    def __init__(self, initial_value=None):
        self._initial_value = self._value = initial_value

    def __getstate__(self):
        return self._initial_value, self._value

    def __setstate__(self, state):
        self._initial_value, self._value = state

    def set_value(self, value):
        self._value = value

    def value(self):
        return self._value

    def raw_value(self):
        return self._value

    def set_initial_value(self, value):
        self._initial_value = self._value = value

    def initial_value(self):
        return self._initial_value

    def has_changed(self):
        try:
            return self._initial_value != self._value
        except TypeError:
            return True

    def revert(self):
        self._value = self._initial_value

    def rollback(self):
        self._value, self._initial_value = self._saved_values

    def commit(self):
        del self._saved_values

    def save(self):
        self._saved_values = self._value, self._initial_value


class ResultRow:
    def __init__(self, table_desc, seed_values=None):
        self._table_desc = table_desc
        self._new = True
        self._columns = {}
        for col_desc in self._table_desc.get_columns():
            col_value = ColumnValue(col_desc.initial_value())
            self._columns[col_desc.name] = col_value
        if seed_values:
            for attr, value in seed_values.iteritems():
                col_desc, col_value = self._colpair(attr)
                col_value.set_initial_value(col_desc.from_user(value))

    def reset_initial(self, name, value):
        col_desc = self._table_desc.get_column(name)
        self._columns[name].set_initial_value(col_desc.from_user(value))


    def __getstate__(self):
        return self._table_desc.db, self._table_desc.name, \
               self._new, self._columns

    def __setstate__(self, state):
        db, name, self._new, self._columns = state
        self._table_desc = db.get_table(name)

    def table_desc(self):
        return self._table_desc

    def db(self):
        return self._table_desc.db

    def _colpair(self, col_name):
        col_desc = self._table_desc.get_column(col_name)
        return col_desc, self._columns[col_desc.name]

    def from_fetch(self, fetch_desc, fetch_row):
        for desc, value in zip(fetch_desc, fetch_row):
            try:
                col_desc, col_value = self._colpair(desc[0])
            except KeyError:
                pass
            else:
                col_value.set_initial_value(col_desc.from_sql(value))
        self._new = False

    def __getattr__(self, name):
        try:
            col_desc, col_value = self._colpair(name)
        except KeyError:
            raise AttributeError('table "%s" has no column "%s"' % \
                                 (self._table_desc.name, name))
        return col_desc.to_user(col_value.value())

    def __setattr__(self, name, value):
        if not name.startswith('_'):
            try:
                col_desc, col_value = self._colpair(name)
            except KeyError:
                pass
            else:
                col_value.set_value(col_desc.from_user(value))
                return
        self.__dict__[name] = value

    def __repr__(self):
        cols = ['%s=%s' % (d.name, repr(self._columns[d.name].value()))
                for d in self._table_desc.get_columns()]
        return '<%s.%s: %s>' % \
            (self._table_desc.db.dsn.database, self._table_desc.name, 
             ', '.join(cols))

    def db_desc(self, changesonly=True):
        def short(s):
            s = str(s)
            if len(s) > 20:
                return '%s...%s' % (s[:10], s[-8:])
            return s
        desc = []
        count = 0
        for col_desc in self._table_desc.get_columns():
            col_value = self._columns[col_desc.name]
            value = col_value.raw_value()
            has_changed = ((self._new and value is not None) 
                           or col_value.has_changed())
            if has_changed:
                count += 1
            if not changesonly or has_changed or col_desc.primary_key:
                new = short(col_desc.to_user(value))
                if col_desc.obscure:
                    desc.append('%s:***' % (col_desc.name))
                elif col_value.initial_value() is None or not has_changed:
                    desc.append('%s:%s' % (col_desc.name, new))
                else:
                    old = short(col_desc.to_user(col_value.initial_value()))
                    desc.append('%s:%s->%s' % (col_desc.name, old, new))
        if not count and (changesonly or self._new):
            return None
        return '%s[%s]' % (self._table_desc.name, ', '.join(desc))

    def is_new(self):
        return self._new

    def db_has_changed(self):
        """
        Has the application changed any column values since the db fetch
        """
        if 0:
            import sys
            for col_desc in self._table_desc.get_columns():
                col_value = self._columns[col_desc.name]
                if col_value.has_changed():
                    print >> sys.stderr, 'changed %s: %r -> %r' %\
                        (col_desc.name, col_value._initial_value, 
                         col_value._value)
        for col_value in self._columns.values():
            if col_value.has_changed():
                return True
        return False

    def db_clone(self):
        # NOTE - does not clone seed values!
        clone = ResultRow(self._table_desc)
        for col_desc in self._table_desc.get_columns():
            if col_desc not in self._table_desc.primary_keys:
                value = self._columns[col_desc.name].value()
                clone._columns[col_desc.name].set_value(value)
        return clone

    def db_revert(self):
        for col_value in self._columns.values():
            col_value.revert()

    def db_rollback(self):
        self._new = self._saved_new
        for col_value in self._columns.values():
            col_value.rollback()

    def db_commit(self):
        del self._saved_new
        for col_value in self._columns.values():
            col_value.commit()

    def db_refetch(self, for_update=False):
        if not self._new:
            table = self._table_desc.name
            curs = self.db().cursor()
            try:
                pkey_names, pkey_values = self._get_pkey(initial = False)
                if not pkey_names:
                    raise dbapi.ProgrammingError('No primary key defined for "%s"' % table)
                cmd = _CmdBuilder()
                cmd.append('SELECT * FROM %s WHERE' % table)
                cmd.append_name_value_expr(' AND ', pkey_names, pkey_values)
                if for_update:
                    cmd.append('FOR UPDATE')
                cmd.execute(curs)
                result = curs.fetchmany(2)
                assert len(result) == 1
                self.from_fetch(curs.description, result[0])
            finally:
                curs.close()

    def _get_pkey(self, initial = True):
        pkey_names, pkey_values = [], []
        for col_desc in self._table_desc.primary_keys:
            pkey_names.append(col_desc.name)
            if initial:
                value = self._columns[col_desc.name].initial_value()
            else:
                value = self._columns[col_desc.name].value()
            pkey_values.append(col_desc.to_sql(value))
        return pkey_names, pkey_values

    def get_keys(self):
        return tuple(self._get_pkey()[1])

    def get_ref(self, col_name):
        col_desc, col_value = self._colpair(col_name)
        ref_col_desc = col_desc.target_column()
        ref_table_desc = ref_col_desc.table_desc
        row = ref_table_desc.get_row()
        curs = self.db().cursor()
        try:
            value = col_value.raw_value()
            if value is not None:
                execute(curs, 'SELECT * FROM %s WHERE %s = %%s' % \
                        (ref_table_desc.name, ref_col_desc.name),
                        (col_desc.to_sql(value),))
                result = curs.fetchone()
                if result:
                    row.from_fetch(curs.description, result)
        finally:
            curs.close()
        return row

    def db_merge(self, src_row):
        """
        Merge values from /src_row/ into /self/

        It is not necessary for /src_row/ to refer to the same table - the
        merging is done by column name and mismatches are ignored. Values 
        are only copied if they have been changed in /src_row/.
        """
        assert isinstance(src_row, ResultRow)
        for col_desc in self._table_desc.get_columns():
            src_col_value = src_row._columns.get(col_desc.name)
            if src_col_value is not None and src_col_value.has_changed():
                col_value = self._columns[col_desc.name]
                col_value.set_value(src_col_value.value())

    def db_update(self, refetch=True):
        changed_cols, new_values = [], []
        no_change = True
        for col_desc in self._table_desc.get_columns():
            col_value = self._columns[col_desc.name]
            value = col_value.raw_value()
            changed = ((self._new and value is not None) 
                       or col_value.has_changed())
            if changed:
                no_change = False
            elif col_desc.auto_timestamp:
                # Not "changed", but auto-updating with other updates
                value = DateTime.now()
                changed = True
            if changed:
                changed_cols.append(col_desc.name)
                new_values.append(col_desc.to_sql(value))
        if no_change:
            return
        table = self._table_desc.name
        curs = self.db().cursor()
        try:
            if self._new:
                cmd = _CmdBuilder()
                cmd.append('INSERT INTO %s' % table)
                cmd.append_list_of_names(changed_cols)
                cmd.append('VALUES')
                cmd.append_list_of_values(new_values)
                cmd.execute(curs)
                if not refetch:
                    return
                execute(curs, 'SELECT * FROM %s WHERE oid=%%s' % table, 
                        (curs.oidValue,))
            else:
                pkey_names, pkey_values = self._get_pkey()
                if not pkey_names:
                    raise dbapi.ProgrammingError('No primary key defined for "%s"' % table)
                cmd = _CmdBuilder()
                cmd.append('UPDATE %s SET' % table)
                cmd.append_name_value_expr(', ', changed_cols, new_values)
                cmd.append('WHERE')
                cmd.append_name_value_expr(' and ', pkey_names, pkey_values)
                cmd.execute(curs)
                if curs.rowcount != 1:
                    raise dbapi.RecordDeleted('Record has been deleted')
                pkey_names, pkey_values = self._get_pkey(initial = False)
                if not refetch:
                    return
                cmd = _CmdBuilder()
                cmd.append('SELECT * FROM %s WHERE' % table)
                cmd.append_name_value_expr(' and ', pkey_names, pkey_values)
                cmd.execute(curs)
            for col_value in self._columns.values():
                col_value.save()
            self._saved_new = self._new
            self.db().add_pending(self)
            result = curs.fetchmany(2)
            assert len(result) == 1
            self.from_fetch(curs.description, result[0])
        finally:
            curs.close()

    def db_delete(self):
        if self._new:
            return
        curs = self.db().cursor()
        try:
            pkey_names, pkey_values = self._get_pkey()
            cmd = _CmdBuilder()
            cmd.append('DELETE FROM %s WHERE' % self._table_desc.name)
            cmd.append_name_value_expr(' and ', pkey_names, pkey_values)
            cmd.execute(curs)
            self.db().del_pending(self)
        finally:
            curs.close()

    def db_nextval(self, colname):
        return self._table_desc.nextval(colname)


class ResultSet(list):
    """
    Behaves like a list of ResultRow instances, inserts and deletes are
    reflected in the database table.
    """
    # We'd like to demand-load the rows, but there's not much point
    # because Postgres cursors don't return the count of rows matched,
    # making the application unlike to abort early (although demand
    # loading might allow the application to give early feedback to
    # the user). 
    def __init__(self, _table_desc):
        self._table_desc = _table_desc
        self.save_state()
        self._rows_deleted = []

    def save_state(self):
        self._rows_orig = self[:]

    def __getstate__(self):
        return self._table_desc.db, self._table_desc.name, \
               self._rows_orig, self._rows_deleted

    def __setstate__(self, state):
        db, name, self._rows_orig, self._rows_deleted = state
        self._table_desc = db.get_table(name)

    def table_desc(self):
        return self._table_desc

    def db(self):
        return self._table_desc.db

    def from_cursor(self, curs, limit=None):
        fetch_desc = curs.description
        while 1:
            fetch_result = curs.fetchmany(100)
            if not fetch_result:
                break
            for fr in fetch_result:
                if limit is not None and len(self) >= limit:
                    raise dbapi.TooManyRecords('Too many records (limit is %d)' % limit)
                row = self._table_desc.get_row()
                row.from_fetch(fetch_desc, fr)
                self.append(row)
        self.save_state()

    def __delitem__(self, n):
        self.pop(n)

    def pop(self, n):
        row = list.pop(self, n)
        if not row.is_new():
            self._rows_deleted.append(row)
        return row

    def remove(self, value):
        list.remove(self, value)
        self._rows_deleted.append(value)

    def new_row(self, **seed_values):
        return self._table_desc.get_row(seed_values=seed_values)

    def db_revert(self):
        self[:] = self._rows_orig
        for row in self:
            row.db_revert()
        self._rows_deleted = []

    def db_update(self):
        for row in self._rows_deleted:
            try:
                row.db_delete()
            except dbapi.IntegrityError:
                self.append(row)
                self._rows_deleted.remove(row)
                raise
        self._rows_deleted = []
        for row in self:
            row.db_update()
        self.save_state()

    def db_has_changed(self):
        if self._rows_deleted:
            return True
        for row in self:
            if row.db_has_changed():
                return True
        return False
