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
from cocklebur.dbobj import dbapi, execute, result, misc


def wild(term):
    if term:
        return term.replace('*', '%').replace('?', '_')


def is_wild(term):
    return term and ('*' in term or '%' in term or '?' in term or '_' in term)


class ExprBuilder:
    def __init__(self, table_desc, conjunction, negate=False):
        self.table_desc = table_desc
        self.conjunction = conjunction.upper()
        self.negate = negate
        self.where_exprs = []

    def where(self, expr, *args):
        self.where_exprs.append(('simple', expr, args))

    def where_in(self, incol, values):
        args = tuple(values)
        nargs = len(args)
        if not nargs:
            # An empty set matches no rows.
            expr = 'false'
        else:
            if isinstance(incol, basestring):
                # Simple "colname IN (value, value)" query
                valuefmt = '%s'
            else:
                # Multi-column IN query: "(colA, colB) IN ((valueA, valueB),...)
                ncols = len(incol)
                if not ncols:
                    raise dbapi.ProgrammingError('"IN" query with no columns?')
                elif ncols == 1:
                    incol = incol[0]
                    valuefmt = '%s'
                else:
                    incol = '(%s)' % ','.join(incol)
                    valuefmt = '(%s)' % ','.join(['%s'] * ncols)
                argsi = iter(args)
                args = []
                for value in argsi:
                    if len(value) != ncols:
                        raise dbapi.ProgrammingError(
        'Multi-column "IN" query parameter count not equal to column count')
                    args.extend(value)
            expr = '%s IN (%s)' % (incol, ','.join([valuefmt] * nargs))
        self.where_exprs.append(('simple', expr, args))

    def in_select(self, incol, table, op='IN', **kwargs):
        in_table_desc = self.table_desc.db.get_table(table)
        if 'columns' not in kwargs:
            kwargs['columns'] = [incol]
        in_query = Query(in_table_desc, **kwargs)
        self.where_exprs.append(('inselect', in_query, (incol, op)))
        return in_query

    def sub_expr(self, conjunction=None, negate=False):
        if not conjunction:
            if self.conjunction == 'AND':
                conjunction = 'OR'
            else:
                conjunction = 'AND'
        sub = ExprBuilder(self.table_desc, conjunction, negate)
        self.where_exprs.append(('subexpr', sub, None))
        return sub

    def __len__(self):
        n = 0
        for exprtype, expr, args in self.where_exprs:
            if exprtype == 'subexpr':
                n += len(expr)
            else:
                n += 1
        return n

    def build_expr(self):
        if self.where_exprs:
            expression, arguments = [], []
            for exprtype, expr, args in self.where_exprs:
                if exprtype == 'subexpr':
                    if len(expr) == 0:
                        continue
                    expr, args = expr.build_expr()
                elif exprtype == 'inselect':
                    incol, op = args
                    expr, args = expr.build_expr()
                    expr = '%s %s (%s)' % (incol, op, expr)
                expression.append(expr)
                arguments.extend(args)
            expression = '(%s)' % (' %s ' % self.conjunction).join(expression)
            if self.negate:
                expression = 'NOT ' + expression
            return expression, arguments
        else:
            # NOOP
            boolean = self.conjunction == 'AND'
            if self.negate:
                boolean = not boolean
            if boolean:
                return 'True', []
            else:
                return 'False', []

class Query:
    def __init__(self, table_desc,
                 conjunction = 'AND', negate=False,
                 distinct = False, 
                 for_update = False, for_share = False,
                 order_by = None, group_by = None, 
                 limit = None, columns = None):
        self.table_desc = table_desc
        self.distinct = distinct
        self.for_update = for_update
        self.for_share = for_share
        self.order_by = order_by
        self.group_by = group_by
        self.limit = limit
        self.columns = columns
        self.joins = []
        self.where_expr = ExprBuilder(self.table_desc, conjunction, negate)
        self.sub_query = None
        self.set_query = None

    def db(self):
        return self.table_desc.db

    def where(self, expr, *args):
        self.where_expr.where(expr, *args)
        return self             # Allow Query(table).where(...).execute(db)

    def where_in(self, incol, values):
        self.where_expr.where_in(incol, values)
        return self             # Allow Query(table).where(...).execute(db)
        
    def in_select(self, incol, table, op='IN', **kwargs):
        return self.where_expr.in_select(incol, table, op, **kwargs)

    def by_primary_keys(self, keys):
        colnames = [col.name for col in self.table_desc.get_primary_cols()]
        self.where_in(colnames, keys)

    def sub_expr(self, conjunction=None, negate=False):
        return self.where_expr.sub_expr(conjunction, negate)

    def sub_select(self, **kwargs):
        self.sub_query = Query(self.table_desc, **kwargs)
        return self.sub_query

    def _set_query(self, table, op, **kwargs):
        if table is None:
            table_desc = self.table_desc
        else:
            table_desc = self.table_desc.db.get_table(table)
        if 'columns' not in kwargs:
            kwargs['columns'] = self.columns
        query = Query(table_desc, **kwargs)
        self.set_query = op, query
        return query

    def union_query(self, table=None, **kwargs):
        return self._set_query(table, 'UNION', **kwargs)

    def intersect_query(self, table=None, **kwargs):
        return self._set_query(table, 'INTERSECT', **kwargs)

    def except_query(self, table=None, **kwargs):
        return self._set_query(table, 'EXCEPT', **kwargs)

    def join(self, join_expr, *join_args):
        self.joins.append((join_expr, join_args))

    def build_expr(self, columns = None):
        table_name = self.table_desc.name
        if not columns:
            columns = self.columns
        query = ['SELECT']
        query_args = []
        if self.distinct:
            query.append('DISTINCT')
        if columns:
            query.append(', '.join(columns))
        else:
            query.append('%s.*' % table_name)
        if self.sub_query:
            sub_expr, sub_args = self.sub_query.build_expr()
            query.append('FROM (%s) AS %s' % (sub_expr, table_name))
            query_args.extend(sub_args)
        else:
            query.append('FROM %s' % table_name)
        for join_expr, join_args in self.joins:
            query.append(join_expr)
            query_args.extend(join_args)
        if self.where_expr:
            where_expr, where_args = self.where_expr.build_expr()
            query.append('WHERE %s' % where_expr)
            query_args.extend(where_args)
        if self.group_by:
            query.append('GROUP BY %s' % self.group_by)
        if self.order_by:
            if type(self.order_by) in (list, tuple):
                query.append('ORDER BY %s' % ', '.join(self.order_by))
            else:
                query.append('ORDER BY %s' % self.order_by)
#            elif self.table_desc.order_by:
#                query.append('ORDER BY ' + ', '.join(self.table_desc.order_by))
#                if self.table_desc.order_reversed:
#                    query.append('DESC')
        if self.for_update:
            query.append('FOR UPDATE')
        elif self.for_share:
            query.append('FOR SHARE')
        if self.limit is not None:
            query.append('LIMIT %s' % self.limit)
        if self.set_query:
            set_op, set_query = self.set_query
            query.append(set_op)
            set_expr, set_args = set_query.build_expr()
            query.append(set_expr)
            query_args.extend(set_args)
        return ' '.join(query), query_args

    def execute(self, curs, columns = None):
        query_expr, query_args = self.build_expr(columns)
        execute.execute(curs, query_expr, query_args)

    def fetchkeys(self):
        table_name = self.table_desc.name
        pkey_cols = ['%s.%s' % (table_name, col.name) 
                     for col in self.table_desc.get_primary_cols()]
        return self.fetchcols(pkey_cols)

    def fetchcols(self, columns):
        """
        Execute the query, returning tuples of the requested columns.
        """
        curs = self.table_desc.db.cursor()
        try:
            if type(columns) in (str, unicode):
                self.execute(curs, [columns])
                return [r[0] for r in curs.fetchall()]
            else:
                self.execute(curs, columns)
                return [tuple(r) for r in curs.fetchall()]
        finally:
            curs.close()

    def fetchall(self, limit=None):
        """
        Execute the query, returning a ResultSet containing ResultRows
        for all the matching rows.
        """
        curs = self.table_desc.db.cursor()
        try:
            self.execute(curs)
            rs = result.ResultSet(self.table_desc)
            rs.from_cursor(curs, limit)
        finally:
            curs.close()
        return rs

    def yieldall(self, fetchcount=100):
        """
        Execute the query, yielding up ResultRow objects.

        Note that we can't mix generator functions and try/finally, so
        this could potentially leak cursors if the caller aborts early,
        and something prevents the generator being GCed.
        """
        curs = self.table_desc.db.cursor()
        self.execute(curs)
        while True:
            rows = curs.fetchmany(fetchcount)
            if not rows:
                break
            for fetch_row in rows:
                row = self.table_desc.get_row()
                row.from_fetch(curs.description, fetch_row)
                yield row
        curs.close()

    def fetchdict(self):
        """
        Execute the query, returning a list of dicts representing the
        resulting rows. 
        
        Some dbapi adapters do this for you - we duplicate the
        functionality here for portability.
        """
        curs = self.table_desc.db.cursor()
        try:
            self.execute(curs)
            cols = misc.cursor_cols(curs)
            return [dict(zip(cols, row)) for row in curs.fetchall()]
        finally:
            curs.close()

    def fetchone(self):
        """
        Execute the query, returning a single ResultRow if a single row
        results, None if no rows match, or raising IntegrityError if
        more than one row results.
        """
        curs = self.table_desc.db.cursor()
        try:
            self.execute(curs)
            fetch_rows = curs.fetchmany(2)
            if len(fetch_rows) == 0:
                return None
            elif len(fetch_rows) > 1:
                raise dbapi.IntegrityError('fetchone returned more than one row')
            row = self.table_desc.get_row()
            row.from_fetch(curs.description, fetch_rows[0])
        finally:
            curs.close()
        return row

    def fetchall_by_keys(self, keys):
        if not keys:
            return []
        # Restore results to the order specific by the user - PG gets this
        # right, but do others?
        keys = [tuple(row_keys) for row_keys in keys]
        self.by_primary_keys(keys)
        rows_by_key = {}
        for row in self.fetchall():
            rows_by_key[row.get_keys()] = row
        return [rows_by_key[row_keys] 
                for row_keys in keys
                if row_keys in rows_by_key]

    def delete(self):
        query = ['DELETE FROM %s' % self.table_desc.name]
        query_args = ()
        if self.where_expr:
            where_expr, query_args = self.where_expr.build_expr()
            query.append('WHERE %s' % where_expr)
        curs = self.table_desc.db.cursor()
        try:
            execute.execute(curs, ' '.join(query), query_args)
        finally:
            curs.close()

    def aggregate(self, *op):
        query_expr, query_args = self.build_expr(op)
        curs = self.table_desc.db.cursor()
        try:
            execute.execute(curs, query_expr, query_args)
            result = curs.fetchone()
            if len(result) != len(op):
                raise dbapi.ProgrammingError('aggregate function returned '
                                             '%d results, expected %d' % 
                                                (len(result), len(op)))
            if len(result) == 1:
                return result[0]
            else:
                return result
        finally:
            curs.close()

    def update(self, set, *args):
        query = ['UPDATE %s SET %s' % (self.table_desc.name, set)]
        args = list(args)
        if self.where_expr:
            where_expr, query_args = self.where_expr.build_expr()
            query.append('WHERE %s' % where_expr)
            args.extend(query_args)
        curs = self.table_desc.db.cursor()
        try:
            execute.execute(curs, ' '.join(query), args)
        finally:
            curs.close()
