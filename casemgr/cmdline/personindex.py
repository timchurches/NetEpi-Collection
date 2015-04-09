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
import sys, os
from casemgr import fuzzyperson
from casemgr import globals

def main(args):
    curs = globals.db.cursor()
    try:
        curs.execute('SELECT person_id, surname, given_names FROM persons')
        rows = curs.fetchall()
    finally:
        curs.close()
    last_pc = 0
    rowcnt = len(rows)
    for i, (person_id, surname, given_names) in enumerate(rows):
        pc = i * 100 / rowcnt
        if last_pc != pc:
            sys.stdout.write(' %d of %d %2d%% done\r' % (i+1, rowcnt, pc))
            sys.stdout.flush()
            last_pc = pc
        fuzzyperson.update(globals.db, person_id, surname, given_names)
    print ' %d of %d 100%% done' % (i+1, rowcnt)
    globals.db.commit()

if __name__ == '__main__':
    main(sys.argv[1:])
