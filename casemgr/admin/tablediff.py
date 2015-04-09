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

# Standard Python libs
import re
import difflib
import itertools
try:
    set
except NameError:
    from sets import Set as set

class TableDiffError(Exception): pass

typeprecmap = {
    'int8': ('int', 8),
    'int4': ('int', 4),
    'int2': ('int', 2),
    'integer': ('int', 4),
    'float4': ('float', 4),
    'float8': ('float', 8),
    'double precision': ('float', 8),
}

varchar_re = re.compile(r'^varchar\s*(\(\d+\))?$')

def type_prec(sqltype):
    try:
        return typeprecmap[sqltype]
    except KeyError:
        match = varchar_re.match(sqltype)
        if match:
            prec = match.group(1)
            if prec:
                return 'varchar', int(prec[1:-1])
            else:
                return 'varchar', None
        else:
            return sqltype, None

implicitcast_map = {
    'float': set(('int','text','varchar')),
    'int': set(('float', 'text','varchar')),
    'date': set(('timestamp','text','varchar')),
    'timestamp': set(('date','text','varchar')),
    'time': set(('text','varchar')),
    'varchar': set(('text',)),
    'text': set(('varchar',)),
}
lossofprec_map = {
    'float': set(('int',)),
    'timestamp': set(('date',)),
}

def safe_conversion(from_type, to_type):
    def normalise(sqltype):
        return sqltype.lower().strip()
#        return tp.upper().split('REFERENCES')[0].strip()
    from_type = normalise(from_type)
    to_type = normalise(to_type)
    if from_type == to_type:
        return True, ''
    from_type, from_prec = type_prec(from_type)
    to_type, to_prec = type_prec(to_type)
    if from_type == to_type:
        if from_prec > to_prec:
            return False, 'overflow'
        return True, ''
    acceptable_types = implicitcast_map.get(from_type)
    if not acceptable_types or to_type not in acceptable_types:
        return False, 'incompatible types'
    precloss_types = lossofprec_map.get(from_type)
    if precloss_types and to_type in precloss_types:
        return True, 'loss of precision'
    return True, ''

class DC_Column:
    def __init__(self, op, col_a, col_b):
        self.op = op
        self.col_a = col_a
        self.col_b = col_b
        self.okay = True
        if self.col_a is not None:
            self.col_a_sql = self.col_a.sql_type()
        if self.col_b is not None:
            self.col_b_sql = self.col_b.sql_type()
        self.style = 'unknown'          # Shouldn't happen
        if op == 'add':
            self.style = 'add'
        elif op == 'drop':
            self.style = 'drop'
        elif self.col_a is not None and self.col_b is not None:
            if self.col_a_sql == self.col_b_sql:
                self.style = 'nochange'
            else:
                self.style = 'typechange'
                self.okay, msg = safe_conversion(self.col_a_sql, self.col_b_sql)
                if msg:
                    self.op = msg
                    if self.okay:
                        self.style = 'warning'
                    else:
                        self.style = 'incompatible'


class DC_Columns(list):
    def __init__(self, table_desc_a, table_desc_b):
        self.table_desc_a = table_desc_a
        self.table_desc_b = table_desc_b

    def get_dc_col(self, op, name_a, name_b):
        col_a = col_b = None
        if name_a:
            col_a = self.table_desc_a.get_column(name_a)
        if name_b:
            col_b = self.table_desc_b.get_column(name_b)
        return DC_Column(op, col_a, col_b)

    def col(self, op, name_a, name_b):
        self.append(self.get_dc_col(op, name_a, name_b))

    def rename(self, old, new):
        if not old or not new:
            raise TableDiffError('Select both a current and a new column')
        new_cols = []
        for dc_col in self:
            if dc_col.col_a is not None and dc_col.col_a.name == old:
                if dc_col.col_b is not None or dc_col.op != 'drop':
                    raise TableDiffError('Can only merge "add" with "drop"')
                if old == new:
                    new_cols.append(self.get_dc_col('', old, new))
                else:
                    new_cols.append(self.get_dc_col('rename', old, new))
            elif dc_col.col_b is not None and dc_col.col_b.name == new:
                if dc_col.col_a is not None or dc_col.op != 'add':
                    raise TableDiffError('Can only merge "add" with "drop"')
            else:
                new_cols.append(dc_col)
        self[:] = new_cols

    def recreate(self, old, new):
        if not old or not new:
            raise TableDiffError('Select both a current and a new column')
        new_cols = []
        for dc_col in self:
            if dc_col.col_a is not None and dc_col.col_a.name == old:
                if dc_col.col_b is None or dc_col.col_b.name != new:
                    raise TableDiffError('Can only split same row')
                new_cols.append(self.get_dc_col('drop', dc_col.col_a.name,None))
                new_cols.append(self.get_dc_col('add', None, dc_col.col_b.name))
            else:
                new_cols.append(dc_col)
        self[:] = new_cols

    def okay(self):
        for dc_col in self:
            if not dc_col.okay:
                return False
        return True

    def is_drop_all(self):
        drop = 0
        rollforward = 0
        for dc_col in self:
            if dc_col.col_a is not None:
                if dc_col.col_b is None:
                    drop += 1
                else:
                    rollforward += 1
        return bool(drop and not rollforward)

    def rollforward_map(self):
        rollforward = []
        for dc_col in self:
            if dc_col.col_a is not None and dc_col.col_b is not None:
                rollforward.append((dc_col.col_a.name, dc_col.col_b.name))
        return rollforward


def col_names(table_desc):
    if table_desc is None:
        return []
    names = [c.name for c in table_desc.columns
             if c.name not in ('summary_id', 'form_date')]
    names.sort()
    return names

def describe_changes(table_desc_a, table_desc_b):
    names_a = col_names(table_desc_a)
    names_b = col_names(table_desc_b)
    diffs = DC_Columns(table_desc_a, table_desc_b)
    s = difflib.SequenceMatcher(None, names_a, names_b)
    for op, i1, i2, j1, j2 in s.get_opcodes():
        if op == 'delete':
            for i in xrange(i1, i2):
                diffs.col('drop', names_a[i], None)
        elif op == 'insert':
            for j in xrange(j1, j2):
                diffs.col('add', None, names_b[j])
        elif op == 'equal':
            for i, j in itertools.izip(xrange(i1, i2), xrange(j1, j2)):
                diffs.col('', names_a[i], names_b[j])
        elif op == 'replace':
            for i in xrange(i1, i2):
                diffs.col('drop', names_a[i], None)
            for j in xrange(j1, j2):
                diffs.col('add', None, names_b[j])
    return diffs
