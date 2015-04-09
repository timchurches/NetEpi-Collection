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

from time import time
import random
from pyPgSQL import PgSQL

def wq_rows(unit_ids, user_ids):
    st = time()
    rows = [(u, None) for u in unit_ids]
    rows += [(None, u) for u in user_ids]
    rows += [(None, None) for n in xrange(len(unit_ids) / 2)]
    rows = [('Q %d' % n, 'X') + r for n, r in enumerate(rows)]
    random.shuffle(rows)
    print 'workqueues %d (%.1f)' % (len(rows), time() - st)
    return rows

def wqm_rows(shared_queues, unit_ids, user_ids):
    st = time()
    rows = []
    idcount = len(unit_ids) + len(user_ids)
    thresh = len(unit_ids)
    for queue_id in shared_queues:
        users = set()
        units = set()
        for n in xrange(random.randrange(3, 50)):
            if random.randrange(idcount) < thresh:
                while 1:
                    id = random.choice(unit_ids)
                    if id not in units:
                        break
                units.add(id)
                rows.append((queue_id, id, None))
            else:
                while 1:
                    id = random.choice(user_ids)
                    if id not in users:
                        break
                users.add(id)
                rows.append((queue_id, None, id))
    random.shuffle(rows)
    print 'wq members %d (%.1f)' % (len(rows), time() - st)
    return rows

def task_rows(case_ids, queue_ids):
    st = time()
    rows = []
    c = 0
    for queue_id in queue_ids:
        case_id = random.choice(case_ids)
        for n in xrange(random.randrange(1, 30)):
            rows.append((queue_id, 'T %d %d' % (c, n), case_id))
            c += 1
    random.shuffle(rows)
    print 'tasks %d (%.1f)' % (len(rows), time() - st)
    return rows

def fetchids(curs):
    return [r[0] for r in curs.fetchall()]

def many(curs, name, cmd, arg):
    st = time()
    curs.executemany(cmd, arg)
    print '%s %d (%.1f)' % (name, len(arg), time() - st)

def main():
    db = PgSQL.connect(database='casemgr')
    curs = db.cursor()
    curs.execute('create index wqdesc on workqueues (description);')
    curs.execute('select unit_id from units where unit_id not in (select unit_id from workqueues where unit_id is not null)')
    unit_ids = fetchids(curs)
    curs.execute('select user_id from users where user_id not in (select user_id from workqueues where user_id is not null)')
    user_ids = fetchids(curs)
    print 'Units %d, Users %d' % (len(unit_ids), len(user_ids))
    # Create workqueues
    many(curs, 'insert wq', 'insert into workqueues (name,description, unit_id, user_id) values (%s,%s,%s,%s)', wq_rows(unit_ids, user_ids))
    # Find shared queues
    curs.execute("select queue_id from workqueues where unit_id is null and user_id is null and description = 'X'")
    shared_queues = fetchids(curs)
    # Add members to shared queues
    print 'Shared queues %s' % len(shared_queues)
    many(curs, 'insert wqm', 'insert into workqueue_members (queue_id, unit_id, user_id) values (%s,%s,%s)', wqm_rows(shared_queues, unit_ids, user_ids))
    # Create tasks
    curs.execute("select master_id from cases")
    case_ids = fetchids(curs)
    curs.execute("select queue_id from workqueues where description='X'")
    queue_ids = fetchids(curs)
    many(curs, 'insert tasks', 'insert into tasks (queue_id, task_description, case_id) values (%s, %s, %s)', task_rows(case_ids, queue_ids))
    curs.execute('drop index wqdesc;')
    db.commit()

if __name__ == '__main__':
    main()
