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
import unittest
from cocklebur.dbobj import query_builder

class DummyColDesc:
    def __init__(self, name):
        self.name = name

class DummyCurs:
    def __init__(self, table_desc):
        self.table_desc = table_desc
        self.table_desc.execute_cmd = None
        self.table_desc.execute_args = None

    def execute(self, cmd, args):
        self.table_desc.execute_cmd = cmd
        self.table_desc.execute_args = tuple(args)

    def fetchone(self):
        return self.table_desc.fetch_result

    def fetchall(self):
        return self.table_desc.fetch_result

    def close(self):
        pass

class DummyDB:
    def __init__(self, table_desc):
        self.table_desc = table_desc

    def cursor(self):
        return DummyCurs(self.table_desc)

    def get_table(self, name):
        return self.table_desc

class DummyTableDesc:
    name = 'test_table'
    
    def __init__(self, fetch_result=None):
        self.fetch_result = fetch_result
        self.db = DummyDB(self)

    def get_primary_cols(self):
        return DummyColDesc('pkey_a'), DummyColDesc('pkey_b')

class Case(unittest.TestCase):
    def _test(self, query, expect, expect_args = [], **kwargs):
        got, got_args = query.build_expr(**kwargs)
        self.assertEqual((expect, expect_args), (got, got_args),
                         '\nExpected: %s (args %s)\nGot     : %s (args %s)' %\
                                (expect, expect_args, got, got_args))

    def _test_exec(self, table_desc, meth, args, kwargs, exec_cmd, 
                   exec_args=[], expect_result=None):

        result = meth(*args, **kwargs)
        self.assertEqual((table_desc.execute_cmd, table_desc.execute_args), 
                         (exec_cmd, exec_args),
                         '\nExecute expected: %s (args %s)'
                         '\nGot     : %s (args %s)' %
                         (exec_cmd, exec_args, 
                          table_desc.execute_cmd, table_desc.execute_args))
        self.assertEqual(result, expect_result,
                         'Returned: %r, expected %r' % 
                         (result, expect_result))
        

    def test_expr_build(self):
        expr_builder = query_builder.ExprBuilder(None, 'AND')
        expr_builder.where('a = %s', 1)
        expr_builder.where('(b = %s OR c = %s)', 2, 3)
        self._test(expr_builder, '(a = %s AND (b = %s OR c = %s))', [1, 2, 3])

    def test_simple(self):
        query = query_builder.Query(DummyTableDesc())
        self._test(query, 'SELECT test_table.* FROM test_table')

    def test_where(self):
        query = query_builder.Query(DummyTableDesc())
        query.where('a = %s', 1)
        self._test(query, 'SELECT test_table.*'
                          ' FROM test_table'
                          ' WHERE (a = %s)', [1])

    def test_where_and(self):
        query = query_builder.Query(DummyTableDesc())
        query.where('a = %s', 1)
        query.where('b = %s', 2)
        self._test(query, 'SELECT test_table.*'
                          ' FROM test_table'
                          ' WHERE (a = %s AND b = %s)', [1, 2])

        query = query_builder.Query(DummyTableDesc(), conjunction = 'OR')
        sub_expr = query.sub_expr()
        sub_expr.where('a = %s', 1)
        sub_expr.where('b = %s', 2)
        self._test(query, 'SELECT test_table.*'
                          ' FROM test_table'
                          ' WHERE ((a = %s AND b = %s))', [1, 2])

    def test_where_or(self):
        query = query_builder.Query(DummyTableDesc(), conjunction = 'OR')
        query.where('a = %s', 1)
        query.where('b = %s', 2)
        self._test(query, 'SELECT test_table.*'
                          ' FROM test_table'
                          ' WHERE (a = %s OR b = %s)', [1, 2])

        query = query_builder.Query(DummyTableDesc())
        sub_expr = query.sub_expr()
        sub_expr.where('a = %s', 1)
        sub_expr.where('b = %s', 2)
        self._test(query, 'SELECT test_table.*'
                          ' FROM test_table'
                          ' WHERE ((a = %s OR b = %s))', [1, 2])

    def test_where_andor(self):
        query = query_builder.Query(DummyTableDesc())
        query.where('a = %s', 1)
        sub_expr = query.sub_expr()
        sub_expr.where('b = %s', 2)
        query.where('d = %s', 4)
        sub_expr.where('c = %s', 3)
        self._test(query, 'SELECT test_table.*'
                          ' FROM test_table'
                          ' WHERE (a = %s AND (b = %s OR c = %s) AND d = %s)', 
                   [1, 2, 3, 4])

        query = query_builder.Query(DummyTableDesc())
        query.where('a = %s', 1)
        sub_expr = query.sub_expr()
        query.where('d = %s', 4)
        self._test(query, 'SELECT test_table.*'
                          ' FROM test_table'
                          ' WHERE (a = %s AND d = %s)', 
                   [1, 4])


    def test_where_not(self):
        query = query_builder.Query(DummyTableDesc(), negate=True)
        query.where('a = %s', 1)
        query.where('b = %s', 2)
        self._test(query, 'SELECT test_table.*'
                          ' FROM test_table'
                          ' WHERE NOT (a = %s AND b = %s)', 
                   [1, 2])

        query = query_builder.Query(DummyTableDesc())
        query.where('a = %s', 1)
        notq = query.sub_expr(negate=True, conjunction='AND')
        notq.where('b = %s', 2)
        notq.where('c = %s', 3)
        self._test(query, 'SELECT test_table.*'
                          ' FROM test_table'
                          ' WHERE (a = %s AND NOT (b = %s AND c = %s))', 
                   [1, 2, 3])

    def test_where_in(self):
        query = query_builder.Query(DummyTableDesc())
        query.where_in('a', [])
        self._test(query, 'SELECT test_table.*'
                          ' FROM test_table'
                          ' WHERE (false)', 
                   [])

        query = query_builder.Query(DummyTableDesc())
        query.where_in('a', [1])
        self._test(query, 'SELECT test_table.*'
                          ' FROM test_table'
                          ' WHERE (a IN (%s))', 
                   [1])

        query = query_builder.Query(DummyTableDesc())
        query.where_in('a', [1, 2])
        self._test(query, 'SELECT test_table.*'
                          ' FROM test_table'
                          ' WHERE (a IN (%s,%s))', 
                   [1,2])

    def test_join(self):
        query = query_builder.Query(DummyTableDesc())
        query.where('a = %s', 1)
        query.join('JOIN foo USING (a)')
        query.join('LEFT JOIN bah USING (b)')
        self._test(query, 'SELECT test_table.*'
                          ' FROM test_table'
                          ' JOIN foo USING (a)'
                          ' LEFT JOIN bah USING (b)'
                          ' WHERE (a = %s)', [1])

    def test_distinct(self):
        query = query_builder.Query(DummyTableDesc(), distinct = True)
        self._test(query, 'SELECT DISTINCT test_table.* FROM test_table')

    def test_order_by(self):
        query = query_builder.Query(DummyTableDesc(), order_by = 'a')
        self._test(query, 'SELECT test_table.* FROM test_table ORDER BY a')
        query = query_builder.Query(DummyTableDesc(), order_by = ('a', 'b'))
        self._test(query, 'SELECT test_table.* FROM test_table ORDER BY a, b')

    def test_for_update(self):
        query = query_builder.Query(DummyTableDesc(), for_update = True)
        self._test(query, 'SELECT test_table.* FROM test_table FOR UPDATE')

    def test_limit(self):
        query = query_builder.Query(DummyTableDesc(), limit = 100)
        self._test(query, 'SELECT test_table.* FROM test_table LIMIT 100')

    def test_keys_only(self):
        query = query_builder.Query(DummyTableDesc())
        self._test(query, 'SELECT test_table.pkey_a, test_table.pkey_b'
                          ' FROM test_table',
                   [], columns = ['test_table.pkey_a', 'test_table.pkey_b'])

    def test_sub_select(self):
        query = query_builder.Query(DummyTableDesc())
        subquery = query.sub_select()
        self._test(query, 'SELECT test_table.*'
                          ' FROM (SELECT test_table.* FROM test_table)'
                          ' AS test_table')

    def test_sub_select_where(self):
        query = query_builder.Query(DummyTableDesc())
        subquery = query.sub_select()
        subquery.where('b = %s', 2)
        query.where('a = %s', 1)
        self._test(query, 'SELECT test_table.*'
                          ' FROM (SELECT test_table.*'
                                  ' FROM test_table'
                                  ' WHERE (b = %s))'
                          ' AS test_table'
                          ' WHERE (a = %s)', [2, 1])

    def test_in_select(self):
        query = query_builder.Query(DummyTableDesc())
        inquery = query.in_select('d', 'test_table')
        inquery.where('a = %s', 1)
        self._test(query, 'SELECT test_table.*'
                          ' FROM test_table'
                          ' WHERE ('
                           'd IN'
                           ' (SELECT d'
                             ' FROM test_table'
                             ' WHERE (a = %s)))', [1])

        query = query_builder.Query(DummyTableDesc())
        query.where('a = %s', 1)
        inquery = query.in_select('d', 'test_table', op='NOT IN', columns=['e'])
        inquery.where('b = %s', 2)
        query.where('c = %s', 3)
        self._test(query, 'SELECT test_table.*'
                          ' FROM test_table'
                          ' WHERE ('
                           'a = %s'
                           ' AND d NOT IN'
                           ' (SELECT e'
                             ' FROM test_table'
                             ' WHERE (b = %s))'
                           ' AND c = %s)', [1, 2, 3])

    def test_set_op(self):

        query = query_builder.Query(DummyTableDesc())
        query.where('a = %s', 1)
        union_query = query.union_query()
        union_query.where('b = %s', 2)
        self._test(query, 'SELECT test_table.*'
                          ' FROM test_table'
                          ' WHERE (a = %s)'
                         ' UNION'
                          ' SELECT test_table.*'
                          ' FROM test_table'
                          ' WHERE (b = %s)', [1, 2])

        query = query_builder.Query(DummyTableDesc())
        query.where('a = %s', 1)
        intersect_query = query.intersect_query()
        intersect_query.where('b = %s', 2)
        self._test(query, 'SELECT test_table.*'
                          ' FROM test_table'
                          ' WHERE (a = %s)'
                         ' INTERSECT'
                          ' SELECT test_table.*'
                          ' FROM test_table'
                          ' WHERE (b = %s)', [1, 2])

        query = query_builder.Query(DummyTableDesc())
        query.where('a = %s', 1)
        except_query = query.except_query()
        except_query.where('b = %s', 2)
        self._test(query, 'SELECT test_table.*'
                          ' FROM test_table'
                          ' WHERE (a = %s)'
                         ' EXCEPT'
                          ' SELECT test_table.*'
                          ' FROM test_table'
                          ' WHERE (b = %s)', [1, 2])

        query = query_builder.Query(DummyTableDesc())
        query.where('a = %s', 1)
        except_query = query.except_query()
        except_query.where('c = %s', 3)
        query.where('b = %s', 2)
        except_query.where('d = %s', 4)
        self._test(query, 'SELECT test_table.*'
                          ' FROM test_table'
                          ' WHERE (a = %s'
                            ' AND b = %s)'
                         ' EXCEPT'
                          ' SELECT test_table.*'
                          ' FROM test_table'
                          ' WHERE (c = %s'
                            ' AND d = %s)', [1, 2, 3, 4])

    def test_where_pkey(self):
        query = query_builder.Query(DummyTableDesc())
        query.by_primary_keys([(1, 2), (3, 4), (5, 6)])
        self._test(query, 'SELECT test_table.*'
                          ' FROM test_table'
                          ' WHERE ((pkey_a,pkey_b) IN ((%s,%s),(%s,%s),(%s,%s)))',
                   [1, 2, 3, 4, 5, 6])

    def test_fetchall(self):
        table_desc = DummyTableDesc()
        query = query_builder.Query(table_desc)
        self._test_exec(table_desc, query.delete, (), {},
                        'DELETE FROM test_table', (), None)
        query.where('a = %s', 1)
        self._test_exec(table_desc, query.delete, (), {},
                        'DELETE FROM test_table WHERE (a = %s)', (1,), 
                        None)

    def test_aggregate(self):
        table_desc = DummyTableDesc(fetch_result=[10])
        query = query_builder.Query(table_desc)
        self._test_exec(table_desc, query.aggregate, ('COUNT(*)',), {},
                        'SELECT COUNT(*) FROM test_table', (), 10)
        query.where('a = %s', 1)
        self._test_exec(table_desc, query.aggregate, ('COUNT(*)',), {},
                        'SELECT COUNT(*) FROM test_table WHERE (a = %s)', 
                        (1,), 10)

class Suite(unittest.TestSuite):
    test_list = (
        'test_expr_build',
        'test_simple',
        'test_where',
        'test_where_and',
        'test_where_or',
        'test_where_andor',
        'test_where_not',
        'test_where_in',
        'test_join',
        'test_distinct',
        'test_order_by',
        'test_for_update',
        'test_limit',
        'test_keys_only',
        'test_sub_select',
        'test_sub_select_where',
        'test_in_select',
        'test_set_op',
        'test_where_pkey',
        'test_fetchall',
        'test_aggregate',
    )
    def __init__(self):
        unittest.TestSuite.__init__(self, map(Case, self.test_list))

def suite():
    return Suite()

if __name__ == '__main__':
    unittest.main()
