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
#   Copyright (C) 2004-2011 Health Administration Corporation and others. 
#   All Rights Reserved.
#
#   Contributors: See the CONTRIBUTORS file for details of contributions.
#

# Standard library
import csv
try:
    set
except NameError:
    from sets import Set as set

# 3rd Party Libs
from mx import DateTime

# Application libs
from dbapi import db, execute

class ReportError(Exception): pass

labs = [
    ('CHW',             'Children\'s Hospital at Westmead'),
    ('ICPMR',           'ICPMR'),
    ('SWAPS',           'SWAPS'),
    ('SEALS',           'SEALS'),
    ('PaLMS',           'PaLMS'),
    ('HAPS',            'HAPS'),
    ('RPAH',            'RPAH'),
    ('DHM',             'DHM'),
    ('Symbion',         'Symbion'),
    ('StVincents',      'St Vincents'),
]

tests = [
    ('DIF', 'DIF'),
    ('Culture', 'Culture'),
    ('PCR', 'PCR'),
    ('SerologyFFR', 'Serology - four fold rise'),
    ('SerologySHT', 'Serology - single high titre'),
    ('POC', 'Point of Care'),
]

choose = ('', 'Choose...')


def iso_to_mx_date(date):
    if date:
        return DateTime.strptime(date, '%Y-%m-%d')


def mx_to_iso_date(date):
    if date:
        return date.strftime('%Y-%m-%d')

def mx_to_iso_datetime(date):
    if date:
        return date.strftime('%Y-%m-%d %H:%M')


# Tim: Medical shorthand often uses "3/52" to mean 3 weeks, "4/12" to mean 4
# months, "5/7" to mean 5 days, "13/24" to mean 13 hours, but not "43/60"
# because that could be minutes or seconds. But 3wks or 3w, 4mths or 4m, 5d,
# 13hrs etc are also used. You could support some or all of these conventions,
# plus interpret integers or floats as years. Anything other than years should
# be converted to a float (in years). Sometimes things like "3y 3m" is used to
# mean 3.25 yrs.

age_formats = [
    (12, ('m', 'mth', 'mths', 'month', 'months')),
    (52, ('w', 'wk', 'wks', 'week', 'weeks')),
    (1, ('y', 'yr', 'yrs', 'year', 'years')),
    (365.25, ('d', 'day', 'days')),
]

def age_to_float(age):
    if not age:
        return None
    age = age.strip()
    if not age:
        return None
    try:
        if '/' in age:
            a, b = age.split('/', 1)
            a = float(a.rstrip())
            b = int(b.lstrip())
            if b in (12, 52):
                return a / b
            elif b == 7:
                return a / 365.25
            elif b == 24:
                return a / (365.25 * 24)
            raise ValueError
        for divisor, suffixes in age_formats:
            for suffix in suffixes:
                if age.lower().endswith(suffix):
                    return float(age[:-len(suffix)].rstrip()) / divisor
        return float(age)
    except ValueError:
        raise ReportError('Unknown age format: %r' % age)


def float_to_age(age):
    if not age or age < 0:
        return ''
    if age >= 1:
        return '%.0f' % age
    months = age * 12
    if months >= 2:
        return '%.0fm' % months
    weeks = age * 52
    if weeks >= 1:
        return '%.0fw' % (age * 52)
    return '0'


def chunk(iter, chunksize=100):
    chunk = []
    for row in iter:
        if len(chunk) == chunksize:
            yield chunk
            chunk = []
        chunk.append(row)
    if chunk:
        yield chunk


class Monitor(object):
    """
    Monitor a set of instance attribues for change
    """
    __slots__ = 'inst', 'attrs', 'state'
    def __init__(self, inst, *attrs):
        self.inst = inst
        self.attrs = attrs
        self.clear()

    def clear(self):
        state = {}
        for attr in self.attrs:
            state[attr] = getattr(self.inst, attr)
        self.state = state

    def check(self):
        for attr in self.attrs:
            then = self.state[attr]
            now = getattr(self.inst, attr)
            if (then or now) and then != now:
                return True
        return False


class ReportMixin:
    report_cols = 'report_id', 'lab', 'week', 'notes', 'completed'

    def init_report(self, lab=None):
        self.report_id = None
        self.notes = ''
        self.completed = None

        self.lab_options = list(labs)
        self.lab_options.insert(0, choose)
        if lab:
            for name, label in labs:
                if name.lower() == lab.lower():
                    lab = name
                    break
            else:
                lab = None
        if lab:
            self.lab = lab
            self.lab_readonly = True
        else:
            self.lab = self.lab_options[0][0]
            self.lab_readonly = False

        prev_week = DateTime.RelativeDateTime(weeks=-1) 
        self.week_options = []
        d = DateTime.now() + \
            DateTime.RelativeDateTime(days=-4, weekday=(DateTime.Friday, 0), 
                                      hour=0, minute=0, second=0)
        for n in range(8):
            self.week_options.append(d.strftime('%Y-%m-%d'))
            d += prev_week
        self.week_options.reverse()
        self.week = self.week_options[-1]
        self.__monitor = Monitor(self, *self.report_cols)

    def load_report(self):
        if not self.lab:
            raise ReportError('Please select a lab')
        curs = db.cursor()
        try:
            execute(curs, 'SELECT report_id, completed, notes'
                          ' FROM lab_reports WHERE lab=%s AND week=%s',
                    self.lab, iso_to_mx_date(self.week))
            row = curs.fetchone()
            if not row:
                return False
            self.report_id, self.completed, self.notes = row
            self.__monitor.clear()
            return True
        finally:
            curs.close()

    def new_report(self):
        assert self.lab
        assert self.week
        curs = db.cursor()
        try:
            execute(curs, 'INSERT INTO lab_reports (lab, week) VALUES (%s, %s)',
                    self.lab, iso_to_mx_date(self.week))
        finally:
            curs.close()

    def update_report(self):
        assert self.report_id
        if self.__monitor.check():
            curs = db.cursor()
            try:
                execute(curs, 'UPDATE lab_reports SET completed=%s, notes=%s'
                            ' WHERE report_id=%s',
                        self.completed, self.notes, self.report_id)
            finally:
                curs.close()
            db.commit()
            self.__monitor.clear()

    def reports(self):
        cols = 'report_id', 'lab', 'week', 'completed'
        class Report(object): __slots__ = cols
        reports = []
        curs = db.cursor()
        try:
            execute(curs, 'SELECT %s FROM lab_reports ORDER BY week, lab' % 
                            ','.join(cols))
            for row in curs.fetchall():
                report = Report()
                for a, v in zip(cols, row):
                    setattr(report, a, v)
                reports.append(report)
        finally:
            curs.close()
        return reports

    def export_notes(self):
        curs = db.cursor()
        try:
            execute(curs, 'SELECT week, lab, completed, notes FROM lab_reports'
                          ' ORDER BY week, lab')
            rows = curs.fetchall()
        finally:
            curs.close()
        yield ['Week Ending', 'Lab', 'Completed', 'Notes']
        for week, lab, completed, notes in rows:
            yield (mx_to_iso_date(week), lab, 
                   mx_to_iso_datetime(completed), notes)
        

class TestTotals:
    tests = [
        ('DIF', 'By DIF'),
        ('Culture', 'By culture'),
        ('Serology', 'By serology'),
        ('PCR', 'By PCR'),
        ('POC', 'By Point-of-Care tests'),
        ('Who', 'Sent to WHO'),
    ]

    def __init__(self, name, label):
        self.name = name
        self.label = label
        self.count = self.load_count = None


class TotalsMixin:

    def totals_set_initial(self):
        for tt in self.test_totals:
            tt.load_count = tt.count

    def init_test_totals(self):
        self.test_totals = [TestTotals(*t) for t in TestTotals.tests]
        self.totals_set_initial()

    def load_totals(self):
        assert self.report_id
        tt_by_name = {}
        for tt in self.test_totals:
            tt_by_name[tt.name] = tt
        curs = db.cursor()
        try:
            execute(curs, 'SELECT test, count FROM lab_totals'
                          ' WHERE report_id=%s', self.report_id)
            for test, count in curs.fetchall():
                try:
                    tt = tt_by_name[test]
                except KeyError:
                    continue
                tt.count = count
        finally:
            curs.close()
        self.totals_set_initial()

    def update_totals(self):
        assert self.report_id
        updated = False
        curs = db.cursor()
        try:
            for tt in self.test_totals:
                if tt.count:
                    try:
                        tt.count = int(tt.count)
                    except ValueError:
                        raise ReportError('%s count must be an integer' %
                                          tt.label)
                else:
                    tt.count = None
                if tt.count == tt.load_count:
                    continue
                execute(curs, 'UPDATE lab_totals SET count=%s'
                              ' WHERE report_id=%s AND test=%s',
                              (tt.count, self.report_id, tt.name))
                if not curs.rowcount:
                    execute(curs, 'INSERT INTO lab_totals VALUES (%s,%s,%s)',
                            (self.report_id, tt.name, tt.count))
                updated = True
        finally:
            curs.close()
        if updated:
            db.commit()
            self.totals_set_initial()

    def export_totals(self):
        reports = self.reports()
        totals_by_report = {}
        curs = db.cursor()
        try:
            execute(curs, 'SELECT report_id, test, count FROM lab_totals')
            for report_id, test, count in curs.fetchall():
                totals_by_report.setdefault(report_id, {})[test] = count
        finally:
            curs.close()
        heading = ['Week Ending', 'Lab', 'Completed']
        for n, l in TestTotals.tests:
            heading.append(n)
        yield heading
        for report in reports:
            row = [mx_to_iso_date(report.week), report.lab,
                   mx_to_iso_datetime(report.completed)]
            totals = totals_by_report.get(report.report_id, {})
            for n, l in TestTotals.tests:
                row.append(totals.get(n, ''))
            yield row


class TestDiags:
    tests = tests

    diagnoses = [
        ('FluA H1', 'Flu A (H1)'),
        ('FluA H3', 'Flu A (H3)'),
        ('FluA H1N1/09', 'Flu H1N1 (Swine)'),
        ('FluA', 'Flu A not subtyped'),
        ('FluB', 'Flu B'),
        ('Adeno', 'Adeno'),
        ('Paraflu', 'Paraflu 1, 2 or 3'),
        ('RSV', 'RSV'),
        ('Rhino', 'Rhino'),
    ]
    diagnosis_map = {}
    for i, (name, label) in enumerate(diagnoses):
        diagnosis_map[name] = i

    def __init__(self, name, label):
        self.name = name
        self.label = label
        self.counts = [None] * len(self.diagnoses)


class DiagsMixin:

    def diag_set_initial(self):
        for td in self.test_diags:
            td.load_counts = list(td.counts)
        
    def init_test_diags(self):
        self.test_diags = [TestDiags(*t) for t in TestDiags.tests]
        self.diag_set_initial()

    def load_diags(self):
        assert self.report_id
        td_by_name = {}
        for td in self.test_diags:
            td_by_name[td.name] = td
        curs = db.cursor()
        try:
            execute(curs, 'SELECT test, diagnosis, count FROM lab_diags'
                          ' WHERE report_id=%s', self.report_id)
            for test, diagnosis, count in curs.fetchall():
                try:
                    td = td_by_name[test]
                    d_index = TestDiags.diagnosis_map[diagnosis]
                except KeyError:
                    continue
                td.counts[d_index] = count
        finally:
            curs.close()
        self.diag_set_initial()

    def update_diags(self):
        assert self.report_id
        updated = False
        curs = db.cursor()
        try:
            for td in self.test_diags:
                for i, c in enumerate(td.counts):
                    diagnosis = TestDiags.diagnoses[i][0]
                    if c:
                        try:
                            td.counts[i] = c = int(c)
                        except ValueError:
                            raise ReportError('%s, %s count must be an integer'
                                                % (td.name, diagnosis))
                    else:
                        td.counts[i] = c = None
                    if c == td.load_counts[i]:
                        continue
                    execute(curs, 'UPDATE lab_diags SET count=%s WHERE'
                                  ' report_id=%s AND test=%s AND diagnosis=%s',
                                (c, self.report_id, td.name, diagnosis))
                    if not curs.rowcount:
                        execute(curs, 'INSERT INTO lab_diags'
                                      ' VALUES (%s,%s,%s,%s)',
                                (self.report_id, td.name, diagnosis, c))
                    updated = True
        finally:
            curs.close()
        if updated:
            db.commit()
            self.diag_set_initial()

    def export_diags(self):
        reports = self.reports()
        diags_by_report = {}
        curs = db.cursor()
        try:
            execute(curs, 'SELECT report_id, test, diagnosis, count'
                          ' FROM lab_diags')
            for report_id, test, diagnosis, count in curs.fetchall():
                diags = diags_by_report.setdefault(report_id, {})
                diags[(test, diagnosis)] = count
        finally:
            curs.close()
        heading = ['Week Ending', 'Lab', 'Completed']
        for test_name, test_label in TestDiags.tests:
            for diag_name, diag_label in TestDiags.diagnoses:
                heading.append('%s_%s' % (test_name, diag_name))
        yield heading
        for report in reports:
            row = [mx_to_iso_date(report.week), report.lab,
                   mx_to_iso_datetime(report.completed)]
            totals = diags_by_report.get(report.report_id, {})
            for test_name, test_label in TestDiags.tests:
                for diag_name, diag_label in TestDiags.diagnoses:
                    row.append(totals.get((test_name, diag_name), ''))
            yield row


class PositiveCase:
    tests = [choose] + tests
    sexes = ['', 'M', 'F']
    attrs = 'test', 'diagnosis', 'age', 'sex', 'suburb', 'postcode'
    diagnoses = ['', 'A', 'B', 'H1N1 Swine']

    def __init__(self, idx):
        self.idx = idx
        self.test = ''
        self.diagnosis = ''
        self.age = ''
        self.sex = ''
        self.suburb = ''
        self.postcode = ''
        self.monitor = Monitor(self, *self.attrs)

    def from_db(self, row):
        for a, v in zip(self.attrs, row):
            if a == 'age':
                v = float_to_age(v)
            setattr(self, a, v)
        self.monitor.clear()

    def update(self, curs, report_id):
        set_sql = []
        args = []
        for a in self.attrs:
            v = getattr(self, a)
            if a == 'age':
                v = age_to_float(v)
            set_sql.append('%s=%%s' % a)
            args.append(v)
        args.append(report_id)
        args.append(self.idx)
        execute(curs, 'UPDATE lab_cases SET %s WHERE'
                        ' report_id=%%s AND idx=%%s'
                    % (', '.join(set_sql)), args)
        if not curs.rowcount:
            cols = list(self.attrs) + ['report_id', 'idx']
            fmt = ['%s'] * len(cols)
            execute(curs, 'INSERT INTO lab_cases (%s) VALUES (%s)'
                    % (','.join(cols), ','.join(fmt)), args)

    def check(self):
        if self:
            age = age_to_float(self.age)
            if age and not 0 <= age < 120:
                raise ReportError('Invalid age: %.0f years' % age)

    def __nonzero__(self):
        return bool(self.age or self.suburb or self.postcode)


class CasesMixin:
    def init_positive_cases(self):
        self.case_page_size = 10
        self.case_page = 0
        self.positive_cases = []
        self.add_case_page()

    def load_positive_cases(self):
        assert self.report_id
        curs = db.cursor()
        try:
            execute(curs, 'SELECT idx, %s FROM lab_cases WHERE report_id=%%s' %
                            ', '.join(PositiveCase.attrs), self.report_id)
            for row in curs.fetchall():
                idx = row[0]
                while len(self.positive_cases) <= idx:
                    self.add_case_page()
                self.positive_cases[idx].from_db(row[1:])
        finally:
            curs.close()

    def update_positive_cases(self):
        assert self.report_id
        curs = db.cursor()
        try:
            updated = False
            for case in self.positive_cases:
                if case.monitor.check():
                    case.update(curs, self.report_id)
                    updated = True
        finally:
            curs.close()
        if updated:
            db.commit()
            for case in self.positive_cases:
                case.monitor.clear()

    def add_case_page(self):
        for n in xrange(self.case_page_size):
            i = len(self.positive_cases)
            self.positive_cases.append(PositiveCase(i))

    def positive_case_page(self):
        s = self.case_page_size * self.case_page
        e = s + self.case_page_size
        return self.positive_cases[s:e]

    def case_page_info(self):
        return 'Page %d of %d' % (self.case_page + 1,
                                len(self.positive_cases) / self.case_page_size)

    def case_page_empty(self):
        for case in self.positive_case_page():
            if case:
                return False
        return True

    def case_page_full(self):
        for case in self.positive_case_page():
            if not case:
                return False
        return True

    def check_page(self):
        for case in self.positive_case_page():
            case.check()

    def next_case_page(self):
#        if not self.case_page_full():
#            return False
        # Last slot filled?
        if not self.positive_case_page()[-1]:
            return False
        self.case_page += 1
        if len(self.positive_cases) <= (self.case_page * self.case_page_size):
            self.add_case_page()
        return True

    def prev_case_page(self):
        if self.case_page:
            if self.case_page_empty():
                del self.positive_cases[-self.case_page_size:]
            self.case_page -= 1
            return True
        else:
            return False

    def export_cases(self):
        reports = self.reports()
        cols = ['idx'] + list(PositiveCase.attrs)
        cases_by_report = {}
        curs = db.cursor()
        try:
            execute(curs, 'SELECT report_id, %s FROM lab_cases' %
                            ', '.join(cols))
            for row in curs.fetchall():
                cases = cases_by_report.setdefault(row[0], [])
                cases.append(row[1:])
        finally:
            curs.close()
        heading = ['Week Ending', 'Lab', 'Completed']
        for col in cols:
            heading.append(col.title())
        yield heading
        for report in reports:
            cases = cases_by_report.get(report.report_id)
            if cases:
                cases.sort()
                report_row = [mx_to_iso_date(report.week), report.lab, 
                              mx_to_iso_datetime(report.completed)]
                for case in cases:
                    row = list(report_row)
                    for a, v in zip(col, case):
                        if a == 'age':
                            v = float_to_age(v)
                        row.append(v)
                    yield row


class LabSurv(ReportMixin, TotalsMixin, DiagsMixin, CasesMixin):
    """
    Represents an individual lab surveillance report.
    """

    def __init__(self, lab=None):
        self.init_report(lab)

    def load(self):
        # Operator has chosen lab & week, load any prior report
        self.init_test_totals()
        self.init_test_diags()
        self.init_positive_cases()
        loaded = self.load_report()
        if not loaded:
            self.new()
            self.load_report()
        # Now load the rest
        self.load_totals()
        self.load_diags()
        self.load_positive_cases()
        return loaded

    def new(self):
        self.new_report()
        db.commit()

    def submit(self):
        self.completed = DateTime.now()
        self.update_report()

    def export(self, mode):
        meth = getattr(self, 'export_' + mode)
        return list(meth())
