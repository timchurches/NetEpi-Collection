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
import ocpgdb as dbapi 

syndrome_id = 8

splitre = re.compile(r'[ ,/]*')

def yield_cases(db):
    curs = db.cursor()
    curs.execute('select case_id, fax_phone from cases join persons using (person_id) where syndrome_id=%s and fax_phone is not null', [syndrome_id])
    for case_id, tags in curs.fetchall():
        yield case_id, tags

def tally(it):
    tally = {}
    for case_id, tags in it:
        for tag in splitre.split(tags):
            tag = tag.upper()
            try:
                ts = tally[tag]
            except KeyError:
                ts = tally[tag] = set()
            ts.add(case_id)
    lt = [(len(ts), tag) for tag, ts in tally.iteritems()]
    lt.sort()
    lt.reverse()
    for cnt, tag in lt[:40]:
        print '%5d %s' % (cnt, tag)


match_tags = [
    'DOH LAB TEST ENTRY', 'COMPLETE EMR',
    'RN1', 'PD1', 'RE1', 'CP1', 
    'GP NO ACTION', 'COMM', 'RF:UPDATED', 'GPSS', 'GP SURVEILLANCE',
    'SCHOOL', 'SCHOOLCONTACT', 'TONGANCONTACT', 'TONGAN', 'KAPOOKA',
    'INPATIENT', 'OUTPATIENT', 'DISCHARGED', 'ICU',
    'ACTCONTACT', 'ACT', 'ACTX', 'VIC', 'VICCONTACT', 'QLD', 'QLDCONTACT',
    'C ICU DISCHARGE DATA UPDATED',
    'OS', 'CONTACTED', 'CRICKET', 'ELINK', 'NARR1',
    'CONCORD OUTPATIENT',
    'FLU CLINIC',
]

tag_remap = {
    'GP SURVEILLANCE': 'GPSS',
}

def preproc(it):
    tagspat = '|'.join([r'\s*\b%s\b\s*' % tag for tag in match_tags])
    tagsre = re.compile('(%s)' % tagspat, re.I)
    ignored = {}
    cases_tags = []
    seen_tags = set()
    for case_id, tags in it:
        case_tags = set()
        for i, t in enumerate(tagsre.split(tags)):
            t = t.strip().upper()
            if i & 1:
                t = tag_remap.get(t, t)
                t = t.replace(' ', '_')
                case_tags.add(t)
                seen_tags.add(t)
            elif t:
                try:
                    cs = ignored[t]
                except KeyError:
                    cs = ignored[t] = set()
                cs.add(case_id)
        cases_tags.append((case_id, case_tags))
    return seen_tags, cases_tags


def make_tags(db, seen_tags):
    curs = db.cursor()
    tag_ids = {}
    for tag in seen_tags:
        curs.execute("SELECT nextval('tags_tag_id_seq')")
        id = curs.fetchone()[0]
        curs.execute('INSERT INTO tags (tag_id, tag) VALUES (%s, %s)',
                        (id, tag))
        tag_ids[tag] = id
    return tag_ids


def tag_cases(db, tag_ids, cases_tags):
    curs = db.cursor()
    for case_id, tags in cases_tags:
        for tag in tags:
            curs.execute('INSERT INTO case_tags (tag_id, case_id) VALUES (%s,%s)', (tag_ids[tag], case_id))


def main(dbname):
    db = dbapi.connect(database=dbname)
    #tally(yield_cases(db))
    seen_tags, cases_tags = preproc(yield_cases(db))

    tag_ids = make_tags(db, seen_tags)
    tag_cases(db, tag_ids, cases_tags)
    db.commit()


main('sftest')

