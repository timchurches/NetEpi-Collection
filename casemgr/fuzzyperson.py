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
import string
import itertools

from cocklebur import dbobj
from casemgr.nickcache import get_nicks
from casemgr.phonetic_encode import dmetaphone


transmap = string.maketrans('-,', '  ')

def encode_phones(*fields):
    word_phones = []
    for field in fields:
        if field:
            words = field.lower().translate(transmap).split()
            wordnicks = get_nicks(words)
            for nicks in wordnicks:
                word_phones.append([dmetaphone(nick) for nick in nicks])
    return word_phones


def update(db, person_id, *names):
    curs = db.cursor()
    try:
        dbobj.execute(curs, 'DELETE FROM person_phonetics WHERE person_id=%s',
                      (person_id,))
        for mp in itertools.chain(*encode_phones(*names)):
            dbobj.execute(curs, 'INSERT INTO person_phonetics VALUES (%s, %s)', 
                          (person_id, mp))
    finally:
        curs.close()

def find(query, *names):
    for name in names:
        if name and dbobj.is_wild(name):
            raise ValueError('Phonetic searching does not support wildcards')
    word_phones = encode_phones(*names)
    if not word_phones:
        return
    for i, dmps in enumerate(word_phones):
        if i:
            subquery = subquery.intersect_query()
        else:
            subquery = query.in_select('person_id', 'person_phonetics')
        subquery.where_in('phonetics', dmps)
