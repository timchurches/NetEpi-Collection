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

import sys
try:
    set
except NameError:
    from sets import Set as set

from cocklebur import dbobj, form_ui, agelib
from casemgr import globals, demogfields, cases, caseaccess, persondupe, \
                    syndrome, form_summary
from casemgr.dataimp import elements, datasrc
from casemgr.dataimp.datasrc import DataImpError

Error = DataImpError

catch_errors = (
    globals.Error,
    dbobj.DatabaseError, 
    form_ui.FormError,
)

class TooManyErrors(DataImpError): pass

# NOTE: Person merging must not merge persons from sources other than the local
# (null) source, or it should clear the source when merging.

class ImportErrors:

    MAX_ERRORS = 100

    def __init__(self):
        self.nerrors = 0
        self.errors = {None: []}

    def __nonzero__(self):
        return bool(self.nerrors)

    def __iter__(self):
        recnums = self.errors.keys()
        recnums.sort()
        for recnum in recnums:
            for msg in self.errors[recnum]:
                yield str(msg)

    def count(self):
        return self.nerrors

    def error(self, msg, recnum=None, row=None):
        self.nerrors += 1
        if row:
            recnum = row.record_num
            msg = 'record %s (line %s): %s' % (recnum, row.line_num, msg)
        elif recnum is not None:
            msg = 'record %s: %s' % (recnum, msg)
        self.errors.setdefault(recnum, []).append(msg)
        if self.nerrors == self.MAX_ERRORS:
            self.errors[None].insert(0, 'More than %d errors, giving up' % 
                                        self.MAX_ERRORS)
            raise TooManyErrors

    def __contains__(self, recnum=None):
        return recnum in self.errors

    def get(self, recnum=None):
        return self.errors.get(recnum, [])

    def __repr__(self):
        return '\n'.join(self)


class ColProc(object):

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def set(self, ns, value):
        if (value is not None and self.options is not None 
                and value not in self.options):
            raise Error('%r not a valid choice' % value)
        setattr(ns, self.target, value)


class ImportCol(ColProc):

    def get(self, row):
        value = self.rule.translate(row.fields[self.index].strip())
        if value == '':
            value = None
        return value


class ImportAgeCol(ImportCol):

    def get(self, row):
        value = row.fields[self.index].strip()
        if not value and self.age_index is not None:
            value = row.fields[self.age_index].strip()
        if value:
            try:
                agelib.Age.parse(value)
            except agelib.Error:
                value = self.rule.translate(value)
        else:
            value = None
        return value


class ImportMultiCol(ImportCol):

    def __init__(self, **kwargs):
        ImportCol.__init__(self, **kwargs)
        assert self.options 
        self.target = self.target.lower()
        self.options = set([o.lower() for o in self.options])

    def set(self, ns, value):
        value = set([o.lower() for o in value])
        invalid = (value - self.options)
        if invalid:
            raise Error('%s not valid choice(s)' % (', '.join(invalid)))
        for name in self.options:
            setattr(ns, self.target+name, name in value)


class ValueCol(ColProc):

    def get(self, row_ignore):
        return self.rule.value


class NS:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class GroupBase(object):
    
    pass


class DemogGroup(GroupBase):
    def __init__(self, importer):
        self.label = 'Demographics'
        fields = demogfields.get_demog_fields(globals.db, importer.syndrome_id)
        fields = fields.context_fields('case')
        self.col_procs = []
        importer.key_proc = None
        for field in fields:
            try:
                rule = importer.importrules[field.name]
            except KeyError:
                continue
            try:
                method = None
                # rather use str.rsplit, but it's not in py 2.3
                # ns, field = col_proc.field.rsplit('.', 1)
                names = field.field.split('.')
                args = {
                    'name': field.name, 
                    'label': field.label, 
                    'entity': names[1],
                    'target': names[2],
                    'rule': rule,
                    'outtrans': field.outtrans,
                    'options': None,
                }
                if field.name == 'DOB':
                    method = ImportAgeCol
                    args['index'] = importer.dataimp_rows.col_idx(rule.src)
                    age_idx = None
                    if isinstance(rule, elements.ImportAgeSource):
                        age_idx = importer.dataimp_rows.col_idx(rule.age)
                    args['age_index'] = age_idx
                elif isinstance(rule, elements.ImportSource):
                    method = ImportCol
                    args['index'] = importer.dataimp_rows.col_idx(rule.src)
                elif isinstance(rule, elements.ImportFixed):
                    method = ValueCol
                elif isinstance(rule, elements.ImportIgnore):
                    continue
                else:
                    raise Error('unknown rule type: %r' % rule)
                if field.optionexpr is not None:
                    args['options'] = set([v[0] for v in field.optionexpr()])
                col_proc = method(**args)
                self.col_procs.append(col_proc)
                if field.name == 'local_case_id':
                    importer.key_proc = col_proc
            except Error, e:
                importer.error('field %r: %s' % (field.label, e))

    def apply(self, importer, case, row):
        for col_proc in self.col_procs:
            try:
                value = col_proc.get(row)
                if col_proc.entity == 'person':
                    col_proc.set(case.person, value)
                elif col_proc.entity == 'case_row':
                    col_proc.set(case.case_row, value)
            except catch_errors, e:
                importer.error('%s: %s' % (col_proc.label, e), row=row)

    def validate(self, importer, case, row):
        try:
            case.validate()
            return True
        except catch_errors, e:
            importer.error(e, row=row)
            return False

    def update(self, importer, case, row):
        self.apply(importer, case, row)
        if self.validate(importer, case, row):
            case.update()

    def __len__(self):
        return len(self.col_procs)

    def headings(self):
        return [col_proc.label for col_proc in self.col_procs]

    def preview(self, importer, case, row):
        ns = NS(case=case)
        self.apply(importer, case, row)
        self.validate(importer, case, row)
        preview = []
        for col_proc in self.col_procs:
            try:
                preview.append(col_proc.outtrans(ns))
            except catch_errors, e:
                preview.append('???')
        return preview


class FormGroup(GroupBase):
    def __init__(self, importer, form_rules):
        self.name = form_rules.name
        self.formdataimp = form_summary.FormDataImp(importer.syndrome_id,
                                                    self.name, 
                                                  importer.importrules.srclabel)
        self.label = self.formdataimp.form.name
        self.version = self.formdataimp.form.cur_version
        form = globals.formlib.load(self.name, self.version)
        self.col_procs = []
        for input in form.get_inputs():
            try:
                rule = form_rules[input.column]
            except KeyError:
                continue
            label = input.label or input.column
            try:
                method = None
                args = {
                    'name': input.column, 
                    'label': label, 
                    'target': input.get_column_name(),
                    'rule': rule,
                    'outtrans': input.outtrans,
                    'options': None,
                }
                if isinstance(rule, elements.ImportMultiValue):
                    method = ImportMultiCol
                    args['index'] = importer.dataimp_rows.col_idx(rule.src)
                elif isinstance(rule, elements.ImportSource):
                    method = ImportCol
                    args['index'] = importer.dataimp_rows.col_idx(rule.src)
                elif isinstance(rule, elements.ImportFixed):
                    method = ValueCol
                elif isinstance(rule, elements.ImportIgnore):
                    continue
                else:
                    raise Error('unknown rule type: %r' % rule)
                if hasattr(input, 'choices'):
                    args['options'] = set([v[0] for v in input.choices])
                self.col_procs.append(method(**args))
            except Error, e:
                importer.error('form %r input %r: %s' % (self.label, label, e))

    def apply(self, importer, ns, row):
        for col_proc in self.col_procs:
            try:
                col_proc.set(ns, col_proc.get(row))
            except catch_errors, e:
                importer.error('%s: %s' % (col_proc.label, e), row=row)

    def validate(self, importer, ns, row):
        form = globals.formlib.load(self.name, self.version)
        form_errors = form.validate(ns)
        if form_errors:
            for error in form_errors.in_order:
                importer.error('%s: %s' % (self.label, error), row=row)
            return False
        return True

    def update(self, importer, case, row):
        try:
            edit_form, form_data = self.formdataimp.edit(case.case_row.case_id)
            self.apply(importer, form_data, row)
        except Error, e:
            edit_form.abort()
            importer.error('%s: %s' % (self.label, e), row=row)
        else:
            if self.validate(importer, form_data, row):
                edit_form.update()
            else:
                edit_form.abort()

    def __len__(self):
        return len(self.col_procs)

    def headings(self):
        return [col_proc.label for col_proc in self.col_procs]

    def preview(self, importer, case, row):
        ns = NS()
        self.apply(importer, ns, row)
        self.validate(importer, ns, row)
        return [col_proc.outtrans(ns) for col_proc in self.col_procs]


class ImportBase(object):

    def __init__(self, syndrome_id, dataimp_src, importrules):
        self.errors = ImportErrors()
        self.col_procs = None
        self.syndrome_id = syndrome_id
        self.importrules = importrules
        self.locked_cases = []
        self.rownum = None
        if not dataimp_src:
            return self.error('No data source selected')
        if not importrules.srclabel:
            return self.error('You must supply a data source name (in Params)')
        self.dataimp_rows = dataimp_src.row_iterator(self.importrules)
        self.demog_group = DemogGroup(self)
        self.groups = [self.demog_group]
        for form_rules in self.importrules.forms():
            self.groups.append(FormGroup(self, form_rules))

    def yield_keys(self):
        assert self.key_proc is not None
        for row in self.dataimp_rows:
            yield self.key_proc.get(row)

    def error(self, msg, **kw):
        self.errors.error(msg, **kw)


class PreviewImport(ImportBase):

    def __init__(self, credentials, syndrome_id, dataimp_src, importrules):
        ImportBase.__init__(self, syndrome_id, dataimp_src, importrules)
        self.rows = []
        self.header = []
        self.group_header = []
        if self.errors:
            return
        for group in self.groups:
            self.group_header.append((group.label, len(group)))
            self.header.extend(group.headings())
        self.n_cols = len(self.header)
        try:
            for row in self.dataimp_rows:
                case = cases.new_case(credentials, self.syndrome_id,
                                      defer_case_id=True)
                row_pp = []
                for group in self.groups:
                    row_pp.extend(group.preview(self, case, row))
                self.rows.append(row_pp)
        except TooManyErrors:
            pass
        except Error, e:
            # For aborting errors
            self.error(e)


def locked_case_ids(credentials, syndrome_id, dataimp_src, importrules):
    importer = ImportBase(syndrome_id, dataimp_src, importrules)
    if importer.key_proc is None:
        raise Error('No key/ID column defined')
    local_ids = importer.yield_keys()
    query = globals.db.query('cases')
    query.join('JOIN persons USING (person_id)')
    caseaccess.acl_query(query, credentials)
    query.where('(data_src is null OR data_src != %s)', importrules.srclabel)
    query.where('(data_src is null OR data_src != %s)', importrules.srclabel)
    query.where_in('local_case_id', local_ids)
    return query.fetchcols('case_id')


class DataImp(ImportBase):

    def __init__(self, credentials, syndrome_id, dataimp_src, importrules):
        ImportBase.__init__(self, syndrome_id, dataimp_src, importrules)
        if self.errors:
            return
        self.update_cnt = self.new_cnt = self.conflict_cnt = 0
        try:
            for row in self.dataimp_rows:
                case = None
                dup_person_id = None
                if self.key_proc is not None:
                    key = self.key_proc.get(row)
                    # XXX We may get a dbapi.IntegrityError exception here,
                    # because the local_case_id column does not have a unique
                    # constraint, and this query may return multiple rows - how
                    # to fix?
                    try:
                        case = cases.case_query(credentials, 
                                                syndrome_id=self.syndrome_id,
                                                local_case_id=key)
                    except dbobj.IntegrityError:

                        self.error('%r %s is not unique' % (self.key_proc.label, key))
                        continue
                if (case is not None 
                        and case.person.data_src != self.importrules.srclabel):
                    if self.importrules.conflicts == 'duplicate':
                        dup_person_id = case.person.person_id
                        case = None
                    else:
                        self.locked_cases.append(key)
                        continue
                if case is None:
                    case = cases.new_case(credentials, self.syndrome_id,
                                          defer_case_id=False)
                    case.person.data_src = self.importrules.srclabel
                    self.new_cnt += 1
                else:
                    self.update_cnt += 1
                for group in self.groups:
                    group.update(self, case, row)
                if dup_person_id is not None:
                    persondupe.conflict(dup_person_id, case.person.person_id)
                    self.conflict_cnt += 1
            self.status = ('Loaded %d records, updated %d, created %d' %
                            (self.update_cnt + self.new_cnt,
                             self.update_cnt, self.new_cnt)) 
            if self.importrules.conflicts == 'duplicate' and self.conflict_cnt:
                self.status += ' (%s duplicates created)' % self.conflict_cnt
        except TooManyErrors:
            pass
        except Error, e:
            self.error(e)
