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

from __future__ import division

import os, sys
import math
from time import time
try:
    set
except NameError:
    from sets import Set as set

from cocklebur import dbobj, daemonize, datetime
from casemgr import globals, persondupecfg
from casemgr.persondupestat import DupeRunning, dupescan_notify

#    These are the status values currently used:
STATUS_EXCLUDED = 'E'   # operator excluded
STATUS_NEW      = 'N'   # new potential dupe
STATUS_CONFLICT = 'C'   # import conflict

uncertain = 0.5 # XXX somewhat of a fudge

class NGram(object):
    __slots__ = ('record', 'ngram_count','ngrams', 'matches')
    N = 3

    def __init__(self, record, row):
        self.record = record
        ngrams = set()
        for field in self.fields:
            value = getattr(row, field)
            if value:
                for word in value.upper().split():
                    if word == 'UNKNOWN':
                        continue
                    word = ' %s ' % word
                    ngram_count = len(word) - self.N + 1
                    i = 0
                    while i < ngram_count:
                        ngrams.add(intern(word[i:i+self.N]))
                        i += 1
        self.matches = None
        self.ngrams = tuple(ngrams)
        self.ngram_count = len(self.ngrams)
        for ngram in self.ngrams:
            self.ngram_map.setdefault(ngram, []).append(self)

    def prescan(self):
        shared_counts = {}
        for ngram in self.ngrams:
            for other in self.ngram_map[ngram]:
                if other is not self:
                    if other in shared_counts:
                        shared_counts[other] += 2
                    else:
                        shared_counts[other] = 2
        self.matches = {}
        for other, shared_count in shared_counts.iteritems():
            ratio = shared_count / (self.ngram_count + other.ngram_count)
            if ratio > uncertain:
                self.matches[other] = ratio
                #assert ratio <= 1.0, 'ratio %.1f, shared cnt %d, this cnt %d, other cnt %d' % (ratio, shared_count, self.ngram_count, other.ngram_count)
        self.ngrams = None  # No longer needed, save memory
        return self.matches

    def match(self, other):
        if not self.ngram_count or not other.ngram_count:
            return None
        return self.matches.get(other, 0.0)


class Sex(object):
    __slots__ = ('record', 'sex',)
    ngram_count = 0

    def __init__(self, record, row):
        self.record = record
        self.sex = row.sex

    def prescan(self):
        pass

    def match(self, other):
        if self.sex not in ('M', 'F') or other.sex not in ('M', 'F'):
            return None
        return ((self.sex == 'M' and other.sex == 'M') or
                (self.sex == 'F' and other.sex == 'F'))


class Age(object):
    __slots__ = ('record', 'DOB', 'DOB_prec')
    ngram_count = 0

    def __init__(self, record, row):
        self.record = record
        self.DOB = row.DOB
        self.DOB_prec = row.DOB_prec or 1

    def prescan(self):
        pass

    def match(self, other):
        if self.DOB is None or other.DOB is None:
            return None
        delta = abs((self.DOB - other.DOB).days)
        prec = max(self.DOB_prec, other.DOB_prec)
        return 1 / (delta / prec + 1.0) ** 2



class Matchers(list):
    
    def __str__(self):
        result = []
        for matcher in self:
            attrs = ['weight=%.1f' % matcher.weight]
            if hasattr(matcher, 'fields'):
                attrs.append('fields=%r' % matcher.fields)
            result.append('%s(%s)' % (matcher.__name__, ', '.join(attrs)))
        return ', '.join(result)


def get_matchers(dupepersoncfg):
    matchers = Matchers()
    for group in dupepersoncfg.ngram_groups:
        if group.enabled and group.fields:
            attrs = {'weight': group.weight, '__slots__': ()}
            if group.fields == ['sex']:
                base = Sex
            elif group.fields == ['DOB']:
                base = Age
            else:
                base = NGram
                attrs['fields'] = group.fields
                attrs['N'] = dupepersoncfg.ngram_level
                attrs['ngram_map'] = {}
            cls = type(group.label, (base,), attrs)
            matchers.append(cls)
    # Adjust relative weights
    tot_weight = sum([cls.weight for cls in matchers])
    for cls in matchers:
        cls.relweight = cls.weight / tot_weight
    return matchers


class Record(object):
    __slots__ = ('key', 'last_update', 'data', 'likely')

    def __init__(self, row, matchers):
        self.key = row.person_id
        self.last_update = row.last_update
        self.data = [cls(self, row) for cls in matchers]
        self.likely = set()

    def prescan(self):
        for mg in self.data:
            likely = mg.prescan()
            if likely is not None:
                for mg in likely:
                    self.likely.add(mg.record)

    def match(self, other):
        score = 0.0
        for a, b in zip(self.data, other.data):
            s = a.match(b)
            if s is None:
                s = uncertain
            score += s * a.relweight
#        if score > 0.70:
#            print >> sys.stderr, self.key, other.key, score
#            for a, b in zip(self.data, other.data):
#                print >> sys.stderr, a.__class__.__name__, a.match(b)
        return score

    def desc_match(self, other):
        desc = []
        desc.append('%s:%s' % (self.key, other.key))
        score = 0.0
        for a, b in zip(self.data, other.data):
            s = a.match(b)
            if s is None:
                s = uncertain
            score += s * a.relweight
            name = a.__class__.__name__
            desc.append('%s:%.0f%%' % (name, s * 100.0))
        desc.append('TOTAL:%.0f%%' % (score * 100.0))
        return ', '.join(desc)

    def ngram_count(self):
        return sum([data.ngram_count for data in self.data])


class MatchPair(object):
    """
    This mirrors a row from the /dupe_persons/ table, and records a pair
    of person Id's that are a likely match, or who have been explicitly
    excluded.
    """
    cols = (
        'low_person_id', 'high_person_id', 'confidence', 'status',
        'exclude_reason',
    )
    def __init__(self, low_person_id, high_person_id, 
                 confidence=None, status=STATUS_NEW, exclude_reason=''):
        assert low_person_id < high_person_id
        self.low_person_id = low_person_id
        self.high_person_id = high_person_id
        self.confidence = confidence
        self.status = status
        self.exclude_reason = exclude_reason

    def dbrow(self, db):
        row = db.new_row('dupe_persons')
        for col in self.cols:
            setattr(row, col, getattr(self, col))
        return row

    def __cmp__(self, other):
        return cmp(self.confidence, other.confidence)

    def confpc(self):
        if self.confidence is None:
            return 'n/a'
        return '%.0f%%' % (self.confidence * 100)


def last_run(db):
    query = db.query('dupe_persons')
    return datetime.mx_parse_datetime(query.aggregate('min(timechecked)'))


def get_status(id_a, id_b, for_update=False):
    if id_a > id_b:
        id_b, id_a = id_a, id_b
    query = globals.db.query('dupe_persons', for_update=for_update)
    query.where('low_person_id=%s AND high_person_id=%s', id_a, id_b)
    row = query.fetchone()
    if not row:
        return STATUS_NEW, ''
    return row.status, row.exclude_reason


def set_status(id_a, id_b, status, exclude_reason=None, confidence=None):
    if id_a > id_b:
        id_b, id_a = id_a, id_b
    query = globals.db.query('dupe_persons', for_update=True)
    query.where('low_person_id=%s AND high_person_id=%s', id_a, id_b)
    row = query.fetchone()
    if not row:
        row = globals.db.new_row('dupe_persons')
        row.low_person_id, row.high_person_id = id_a, id_b
    row.status = status
    row.exclude_reason = exclude_reason
    if confidence is not None:
        row.confidence = confidence
    row.db_update(refetch=False)


def exclude(id_a, id_b, reason):
    set_status(id_a, id_b, STATUS_EXCLUDED, reason)


def clear_exclude(id_a, id_b):
    set_status(id_a, id_b, STATUS_NEW)


def conflict(id_a, id_b):
    set_status(id_a, id_b, STATUS_CONFLICT, confidence=1.0)


def dupe_lock(db, mode='SHARE'):
    try:
        db.lock_table('dupe_persons', mode, wait=False)
    except dbobj.DatabaseError:
        raise DupeRunning

class DupePersons:
    """
    In-core representation of the dupe_persons table. 
    
    Explicit table locks are used to provide mutual exclusion. The
    background dupe identification process obtains an EXCLUSIVE lock,
    while clients briefly obtain a SHARE lock (while loading the
    table). This does not prevent dupe identification being run while
    clients are working on dupe data, but does prevent multiple dupe
    identification runs being started, and the EXCLUSIVE prevents clients
    from committing exclusion updates, which would otherwise be clobbered.
    """
    MAX_MATCHES = 10000

    def __init__(self):
        self.matchpairs = {}
        self.load_status = None

    def load(self, db, status=None):
        query = db.query('dupe_persons')
        if status is not None:
            self.load_status = status
            query.where('status = %s', status)
        for row in query.fetchcols(MatchPair.cols):
            mp = MatchPair(*row)
            key = mp.low_person_id, mp.high_person_id
            self.matchpairs[key] = mp

    def save(self, db):
        query = db.query('dupe_persons')
        query.where('status != %s', STATUS_CONFLICT)
        query.delete()
        for mp in self.matchpairs.itervalues():
            mp.dbrow(db).db_update(False)

    def get(self, id_a, id_b):
        if id_a > id_b:
            lowhigh = id_b, id_a
        else:
            lowhigh = id_a, id_b
        mp = self.matchpairs.get(lowhigh)
        if mp is None:
            mp = MatchPair(*lowhigh)
            self.matchpairs[lowhigh] = mp
        return mp

    def sorted(self):
        pairs = self.matchpairs.values()
        pairs.sort()
        pairs.reverse()
        return pairs

    def __len__(self):
        return len(self.matchpairs)

    def adjust_cutoff(self, cutoff):
        while len(self.matchpairs) > self.MAX_MATCHES and cutoff < 0.9:
            cutoff += 0.05
            for mp in self.matchpairs.values():
                if mp.confidence < cutoff and mp.status == STATUS_NEW:
                    lowhigh = mp.low_person_id, mp.high_person_id
                    del self.matchpairs[lowhigh]
        return cutoff


def loaddupe(db):
    """
    Load the dupe_persons table data, return a sorted list from best to
    worst match.
    """
    dp = DupePersons()
    dupe_lock(db)
    dp.load(db)
    return dp.sorted()


def loadconflicts(db):
    """
    Load the dupe_persons table data, return a sorted list from best to
    worst match.
    """
    dp = DupePersons()
    dp.load(db, status=STATUS_CONFLICT)
    return dp.sorted()


class Timer:

    def __init__(self):
        self.times = []
        self.timers = {}

    def start(self, label):
        self.timers[label] = time()

    def stop(self, label):
        el = time() - self.timers.pop(label)
        self.times.append((label, el))

    def __str__(self):
        times = []
        for label, el in self.times:
            if el > 90:
                times.append('%s: %.1fm' % (label, el / 60.0))
            else:
                times.append('%s: %.2fs' % (label, el))
        return ', '.join(times)


class MatchPersons:
    """
    This object manages the duplicate person identification.

    The scan compares every person against every other person, and where
    the match strength is greater than /uncertain/, creates (or updates)
    a MatchPair record in the /dupes/ structure (which is an instance
    of DupePersons).
    """

    def __init__(self, db, config=None, updated_only=False):
        self.records = []
        if config is None:
            config = persondupecfg.new_persondupecfg()
        self.configure(config)
        self.dupes = DupePersons()
        self.timer = Timer()
        dupe_lock(db, 'EXCLUSIVE')
        self.load(db, updated_only)
        self.prescan()
        self.cross_compare(updated_only)

    def configure(self, dupepersoncfg):
        self.matchers = get_matchers(dupepersoncfg)
        self.cutoff = dupepersoncfg.cutoff

    def load(self, db, updated_only):
        self.timer.start('load')
        dupescan_notify('load', 0, 0)
        query = db.query('persons')
        #query.where('(person_id % 3) = 0') # XXX speed-up for debugging only
        for row in query.yieldall():
            self.records.append(Record(row, self.matchers))
        if updated_only:
            self.dupes.load(db)
        else:
            self.dupes.load(db, status=STATUS_EXCLUDED)
        self.timer.stop('load')
        self.last_run = last_run(db)

    def prescan(self):
        self.timer.start('prescan')
        last_pc = 0
        iterations = len(self.records)
        t0 = time()
        for n, record in enumerate(self.records):
            pc = n * 100 // iterations
            if pc != last_pc:
                el = time() - t0
                etc = int(el / n * (iterations - n))
                dupescan_notify('index', pc, etc)
                last_pc = pc
            record.prescan()
        self.timer.stop('prescan')

    def save(self, db):
        self.timer.start('save')
        self.dupes.save(db)
        self.timer.stop('save')

    def _yield_update_pairs(self):
        thres = self.last_run
        updated_records = [r for r in self.records
                            if not r.last_update or r.last_update >= thres]
        iterations = len(self.records) * len(updated_records)
        count = 0
        checked = set()
        for a in updated_records:
            for b in self.records:
                count += 1
                if a.key == b.key:
                    continue
                if a.key > b.key:
                    keypair = b.key, a.key
                else:
                    keypair = a.key, b.key
                if keypair in checked:
                    continue
                checked.add(keypair)
                yield count, iterations, a, b

    def _yield_all_pairs(self):
        records = self.records
        nrecords = len(records)
        iterations = (nrecords - 1) * nrecords // 2
        count = 0
        for ai in xrange(nrecords-1):
            for bi in xrange(ai+1, nrecords):
                count += 1
                a = records[ai]
                b = records[bi]
                yield count, iterations, a, b

    def _yield_likely_pairs(self):
        iterations = sum([len(a.likely) for a in self.records])
        count = 0
        for a in self.records:
            for b in a.likely:
                count += 1
                yield count, iterations, a, b

    def cross_compare(self, updated_only=False):
        self.timer.start('scan')
        t0 = time()
        if updated_only:
            gen = self._yield_update_pairs
        else:
            #gen = self._yield_all_pairs
            gen = self._yield_likely_pairs
        thres = self.last_run
        last_pc = 0
        for n, iterations, a, b in gen():
                pc = n * 100 // iterations
                if iterations > 100000 and pc != last_pc:
                    el = time() - t0
                    etc = int(el / n * (iterations - n))
                    dupescan_notify('scan', pc, etc)
                    last_pc = pc
                match_confidence = a.match(b)
                if match_confidence > self.cutoff:
                    mp = self.dupes.get(a.key, b.key)
                    mp.confidence = match_confidence
                    self.cutoff = self.dupes.adjust_cutoff(self.cutoff)
        self.timer.stop('scan')

    def ngram_count(self):
        return sum([rec.ngram_count() for rec in self.records])

    def stats(self):
        n_ngrams = self.ngram_count()
        ngram_rate = '??'
        if self.records:
            ngram_rate = '%.1f' % (n_ngrams / len(self.records))
        return 'Times: %s (%d ngrams, %d records, %s ngrams/rec, %d likely matches)' %\
            (self.timer,
             n_ngrams, len(self.records), 
             ngram_rate, len(self.dupes))

    def report(self):
        pairs = self.dupes.sorted()
        print 'top %d:' % (min(len(pairs), 20))
        for mp in pairs[:20]:
            print '%8d vs %-8d: %5s (%s:%s)' %\
                (mp.low_person_id, mp.high_person_id, mp.confpc(), 
                 mp.status, mp.exclude_reason)


def explain_dupe(prefs, person_a, person_b):
    config = prefs.get('persondupecfg')
    if config is None:
        config = persondupecfg.new_persondupecfg()
    matchers = get_matchers(config)
    #print >> sys.stderr, person_a.surname, person_a.given_names
    #print >> sys.stderr, person_b.surname, person_b.given_names
    #print >> sys.stderr, uncertain, matchers
    a = Record(person_a, matchers)
    b = Record(person_b, matchers)
    b.prescan()
    a.prescan()
    return a.desc_match(b)


def persondupe(db, dup_config, updated_only=False):
    # We have to close our connection to the database, or the forked child will
    # inherit it, which is not allowed, and attempting to close one results in
    # both being torn down.
    import config
    db.close()
    if daemonize.daemonize():
        return
    try:
        try:
            import psyco
        except ImportError:
            pass
        else:
            psyco.full()
        print >> sys.stderr, '%s: Person dupe detection started' % config.appname
        mp = MatchPersons(db, dup_config, updated_only)
        mp.save(db)
        print >> sys.stderr, '%s: Person dupe detection: %s' % (config.appname, mp.stats())
        db.commit()
    except DupeRunning:
        print >> sys.stderr, 'Person dupe detection already running'
    os._exit(0)


if __name__ == '__main__':
    from casemgr import globals
    try:
        mp = MatchPersons(globals.db, None, sys.argv[1] == 'updated')
        mp.save(globals.db)
        print mp.stats()
        mp.report()
        globals.db.commit()
    except DupeRunning:
        sys.exit('Already running')
