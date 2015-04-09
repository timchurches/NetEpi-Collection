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
import inspect
try:
    set
except NameError:
    from sets import Set as set

from cocklebur import dbobj, form_ui, datetime, agelib, utils
from casemgr import demogfields, fuzzyperson, syndrome, globals, casetags
from casemgr.reports.common import *

# FieldOps support the Terms, providing field specific methods for date
# formating, valid discrete values, and so on. Important subclasses include:
#   DemogFieldOps
#   FormFieldOps
#   PatternFieldOps
#   RangeFieldOps
#   DateRangeFieldOps
#
# FieldOpsCache provides an accellerated lookup of FieldOp class from field
# name (and form+version).
#
# FilterBase is the basis for filter nodes. The TermBase subclass is the basis
# for filter terms such as "in", "pattern", "phonetic", "range", etc.
# Conjunction provides the AND and OR operators.
#
# FilterGroup is a helper for the FilterAdder, used when listing available
# filters and filter operators. Key subclasses are:
#   DemogFilterGroup
#   FormFilterGroup
#   AndSubexpressionGroup
#   OrSubexpressionGroup
#
# FilterAdder holds the user context while the user is adding a new filter term.
#
# FilterParamsMixin is the top level structure that holds filter-related report
# parameters.

class FieldOps(object):

    allow_negate = True

    def __init__(self, term):
        self.params = term.params
        self.term = term

    def date_format(self):
        return None

    def check(self, msgs):
        return True

    def query(self, query):
        if boolstr(self.term.negate):
            query = query.sub_expr(conjunction='AND', negate=True)
        try:
            self._query(query)
        except Error, e:
            raise Error('%s filter: %s' % (self.label(), e))


class PatternFieldOps(FieldOps):

    def _query(self, query):
        if self.term.value:
            values = utils.commasplit(self.term.value)
            colname = self.colname()
            if len(values) > 1:
                query = query.sub_expr(conjunction='OR')
                for value in values:
                    query.where('%s ILIKE %%s' % colname, dbobj.wild(value))
            else:
                query.where('%s ILIKE %%s' % colname, 
                            dbobj.wild(self.term.value))


class RangeFieldOps(FieldOps):

    iso_fmt = None

    def parse(self, v):
        return v

    def _query(self, query):
        colname = self.colname()
        from_value = to_value = None
        if self.term.from_value:
            from_value = self.parse(self.term.from_value)
        if self.term.to_value:
            to_value = self.parse(self.term.to_value)
        if from_value and to_value and to_value < from_value:
            to_value, from_value = from_value, to_value
        if from_value:
            from_op = '>'
            if boolstr(self.term.incl_from):
                from_op += '='
            query.where('%s %s %%s' % (colname, from_op), from_value)
        if to_value:
            to_op = '<'
            if boolstr(self.term.incl_to):
                to_op += '='
            query.where('%s %s %%s' % (colname, to_op), to_value)


class DateRangeFieldOps(RangeFieldOps):

    iso_fmt = '%Y-%m-%d %H:%M:%S'

    def date_format(self):
        return datetime.mx_parse_datetime.format

    def parse(self, v):
        try:
            return datetime.parse_discrete(v, past=True).mx()
        except datetime.Error, e:
            raise Error(str(e))


class DemogFieldOps(FieldOps):

    def form_label(self):
        return 'Demographics'

    def demog_field(self):
        return self.params.demog_fields().field_by_name(self.term.field)

    def label(self):
        return self.demog_field().label

    def colname(self):
        field = self.demog_field()
        return '%s.%s' % (field.table, field.name)

    def options(self):
        return [(v or '?', l) for v, l in self.demog_field().optionexpr()]

    def _query(self, query):
        if self.term.value:
            query.where('%s = %%s' % self.colname(), self.term.value)


class CasesetDemogFieldOps(DemogFieldOps):

    def _query(self, query):
        query.where_in('case_id', [int(v) for v in self.term.values])


class PatternDemogFieldOps(PatternFieldOps, DemogFieldOps):

    pass


class RangeDemogFieldOps(RangeFieldOps, DemogFieldOps):

    pass


class DateRangeDemogFieldOps(DateRangeFieldOps, DemogFieldOps):

    pass


class DOBDemogFieldOps(DateRangeDemogFieldOps):

    def parse(self, v):
        if v:
            try:
                return agelib.parse_dob_or_age(v)[0]
            except agelib.Error, e:
                raise Error('%s filter: %s' % (self.label(), e))


class InDemogFieldOps(DemogFieldOps):

    def _query(self, query):
        if self.term.values:
            if '?' in self.term.values:
                sub = query.sub_expr('OR')
                sub.where('%s IS NULL' % self.colname())
                value = [v for v in self.term.values if v != '?']
                if value:
                    sub.where_in(self.colname(), value)
            else:
                query.where_in(self.colname(), self.term.values)


class NamesDemogFieldOps(DemogFieldOps):

    def _query(self, query):
        if self.term.value:
            try:
                fuzzyperson.find(query, self.term.value)
            except ValueError, e:
                raise Error(str(e))


class DeletedDemogFieldOps(DemogFieldOps):

    allow_negate = False

    def query(self, query):
        if self.term.value == 'exclude':
            query.where('NOT cases.deleted')
        elif self.term.value == 'only':
            query.where('cases.deleted')

    def options(self):
        return [
            ('exclude', 'Excluded'),
            ('both', 'Included'),
            ('only', 'Only deleted'),
        ]


class TagsDemogFieldOps(DemogFieldOps):

    def _query(self, query):
        if self.term.value:
            subq = query.in_select('cases.case_id', 'case_tags', 
                                   columns=['case_id'])
            subq.join('JOIN tags USING (tag_id)')
            subq.where('tag ILIKE %s', self.term.value)


class FormFieldOps(FieldOps):

    def form_input(self):
        form = self.params.form_info(self.term.form).load()
        return form.columns.find_input(self.term.field)

    def form_label(self):
        return self.params.form_info(self.term.form).label

    def label(self):
        input = self.form_input()
        return input.label or input.column

    def formtable(self):
        return self.params.form_info(self.term.form).tablename()

    def colname(self):
        return '%s.%s' % (self.formtable(), self.term.field)

    def check(self, msgs):
        info = self.params.form_info(self.term.form)
        try:
            info.load().columns.find_input(self.term.field)
        except KeyError:
            msgs.msg('err', 'Form %r has been updated, filter field %r has '
                            'been deleted' % (info.label, self.term.field))
            return False
        return True


class PatternFormFieldOps(PatternFieldOps, FormFieldOps):

    pass


class RangeFormFieldOps(RangeFieldOps, FormFieldOps):

    pass


class DateRangeFormFieldOps(DateRangeFieldOps, FormFieldOps):

    iso_fmt = '%Y-%m-%d'

    def date_format(self):
        return datetime.mx_parse_date.format


class DateTimeRangeFormFieldOps(DateRangeFieldOps, FormFieldOps):

    def date_format(self):
        return datetime.mx_parse_datetime.format


class ChoicesFormFieldOps(FormFieldOps):

    def _query(self, query):
        if self.term.values:
            query.where_in(self.colname(), self.term.values)

    def options(self):
        return self.form_input().choices


class CheckboxFormFieldOps(ChoicesFormFieldOps):

    def _query(self, query):
        if self.term.values:
            subq = query.sub_expr('OR')
            basename = self.colname()
            for value in self.term.values:
                subq.where('%s%s' % (self.colname(), value.lower()))


class FieldOpsCache:

    def __init__(self):
        self.cache = {}

    def demog_field_ops(self, field):
        if field.name == 'DOB':
            return [('range', DOBDemogFieldOps)]
        if isinstance(field, demogfields.SelDemogField):
            return [('in', InDemogFieldOps)]
        if isinstance(field, demogfields.DatetimeBase):
            return [('range', DateRangeDemogFieldOps)]
        if field.name == 'case_id':
            return [('range', RangeDemogFieldOps)]
        if field.name in ('surname', 'given_names'):
            return [
                ('pattern', PatternDemogFieldOps),
                ('phonetic', NamesDemogFieldOps),
            ]
        if field.name == 'deleted':
            return [('select', DeletedDemogFieldOps)]
        if field.name == 'tags':
            return [('select', TagsDemogFieldOps)]
        return [('pattern', PatternDemogFieldOps)]

    form_cls_ops_map = {
        form_ui.TextInput: [('pattern', PatternFormFieldOps)],
        form_ui.IntInput: [('range', RangeFormFieldOps)],
        form_ui.FloatInput: [('range', RangeFormFieldOps)],
        form_ui.TextArea: [('pattern', PatternFormFieldOps)],
        form_ui.DropList: [('in', ChoicesFormFieldOps)],
        form_ui.RadioList: [('in', ChoicesFormFieldOps)],
        form_ui.CheckBoxes: [('in', CheckboxFormFieldOps)],
        form_ui.DateInput: [('range', DateRangeFormFieldOps)],
        form_ui.TimeInput: [('range', RangeFormFieldOps)],
        form_ui.DatetimeInput: [('range', DateTimeRangeFormFieldOps)],
    }

    def form_field_ops(self, input):
        for inputbase in inspect.getmro(input.__class__):
            if inputbase in self.form_cls_ops_map:
                return self.form_cls_ops_map[inputbase]
        return [('pattern', PatternFormFieldOps)]

    def get_ops(self, params, field_name, form_name=None):
        if form_name and form_name != 'demog':
            info = params.form_info(form_name)
            key = form_name, info.version, field_name
            try:
                ops = self.cache[key]
            except KeyError:
                input = info.load().columns.find_input(field_name)
                ops = self.cache[key] = self.form_field_ops(input)
        else:
            key = field_name
            try:
                ops = self.cache[key]
            except KeyError:
                field = params.demog_fields().field_by_name(field_name)
                ops = self.cache[key] = self.demog_field_ops(field)
        return ops

    def term_ops(self, term):
        for op, ops_cls in self.get_ops(term.params, term.field, term.form):
            if term.op == op:
                return ops_cls(term)
    
    def available_ops(self, params, field, form):
        return [op for op, ops_cls in self.get_ops(params, field, form)]

field_ops_cache = FieldOpsCache()


terms_by_op = {}

class FilterMeta(type):

    def __init__(cls, name, bases, dict):
        if cls.op:
            terms_by_op[cls.op.lower()] = cls


def make_term(op, **kw):
    try:
        cls = terms_by_op[op.lower()]
    except KeyError:
        raise Error('Unknown filter operator %r' % op)
    try:
        return cls(**kw)
    except Exception:
        print cls
        raise


class FilterBase(object):

    """
    Public interface:
        form                    group name (null for demog, form name for forms)
        field                   field name
        value                   match value for single-value matches
        values                  match values for multi-match filters

        form_label()            Group label (Demographics/form name)
        label()                 Field label
        get_markup()            Filter op markup name
        options()               For discrete filters, value options
        date_format()           User's preferred date fmt (date/time cols only)
        parse()                 Convert filter value to py type
        query(query)            Add this term to the given Query object
        to_xml(xmlgen)          Add this term to the given XMLWriter object

    Internal interface:
        _attr_to_xml(xmlgen)    XML: Emit attrs
        _value_to_xml(xmlgen)   XML: Emit value
    """

    __metaclass__ = FilterMeta
    params = None
    op = None

    def desc(self):
        return None

    def _set_params(self, params):
        self.params = params

    def _forms_used(self, used):
        pass

    def _check(self, msgs):
        return True

    def _trim(self):
        return 1

    def to_xml(self):
        raise NotImplementedError


class TermBase(FilterBase):

    field = None
    form = None
    value = None
    negate = False
    field_ops = None

    def __init__(self, field, **kw):
        self.field = field
        self.__dict__.update(kw)

    def _set_params(self, params):
        if self.params is None:
            self.params = params
            self.field_ops = field_ops_cache.term_ops(self)

    def get_markup(self):
        return self.op

    def deleted_filter(self):
        return not self.form and self.field == 'deleted'

    def date_format(self):
        return self.field_ops.date_format()

    def parse(self, v):
        return self.field_ops.parse(v)

    def options(self):
        return self.field_ops.options()

    def query(self, query):
        return self.field_ops.query(query)

    def label(self):
        return self.field_ops.label()

    def form_label(self):
        return self.field_ops.form_label()

    def allow_negate(self):
        return self.field_ops.allow_negate

    def _forms_used(self, used):
        if self.form:
            used.add(self.form)

    def _check(self, msgs):
        return self.field_ops.check(msgs)

    def _attr_to_xml(self, node):
        pass

    def _value_to_xml(self, xmlgen):
        if self.value:
            v = xmlgen.push('value')
            v.text(self.value)
            xmlgen.pop()

    def to_xml(self, xmlgen):
        node = xmlgen.push('term')
        if self.form:
            node.attr('form', self.form)
        node.attr('field', self.field)
        node.attr('op', self.op)
        if boolstr(self.negate):
            node.attr('negate', 'yes')
        self._attr_to_xml(node)
        self._value_to_xml(xmlgen)
        xmlgen.pop()


class PlaceholderTerm(TermBase):

    op = 'placeholder'

    def __init__(self):
        pass

    def _set_params(self, params):
        pass

    def label(self):
        return ''

    def form_label(self):
        return ''

    def desc(self):
        return ' '

    def _trim(self):
        return 0

    def to_xml(self, xmlgen):
        pass

    
class PatternTerm(TermBase):
    
    op = 'pattern'

    def desc(self):
        if boolstr(self.negate):
            return 'not matching pattern %r' % self.value
        else:
            return 'matching pattern %r' % self.value


class PhoneticTerm(TermBase):
    
    op = 'phonetic'

    def desc(self):
        return 'phonetically matches %r' % self.value


class RangeTerm(TermBase):

    op = 'range'
    from_value = ''
    to_value = ''
    incl_from = True
    incl_to = False

    def desc(self):
        desc = []
        if boolstr(self.negate):
            desc.append('not')
        if self.from_value:
            desc.append('from %s' % self.from_value)
            if self.incl_from:
                desc.append('(inclusive)')
        if self.to_value:
            desc.append('to %s' % self.to_value)
            if self.incl_to:
                desc.append('(inclusive)')
        return ' '.join(desc)

    def _value_to_xml(self, xmlgen):
        if self.from_value:
            se = xmlgen.push('from')
            if self.incl_from:
                se.attr('inclusive', 'yes')
            value = self.from_value
            if self.field_ops and self.field_ops.iso_fmt:
                value = self.parse(value).strftime(self.field_ops.iso_fmt)
            se.text(value)
            xmlgen.pop()
        if self.to_value:
            se = xmlgen.push('to')
            value = self.to_value
            if self.field_ops and self.field_ops.iso_fmt:
                value = self.parse(value).strftime(self.field_ops.iso_fmt)
            se.text(value)
            if self.incl_to:
                se.attr('inclusive', 'yes')
            xmlgen.pop()


class InTerm(TermBase):
    
    op = 'in'

    def __init__(self, field, **kw):
        self.values = []
        TermBase.__init__(self, field, **kw)

    def desc(self):
        if len(self.values) == 1:
            if boolstr(self.negate):
                op = 'is not'
            else:
                op = 'is'
        else:
            if boolstr(self.negate):
                op = 'is not in'
            else:
                op = 'is in'
        label_map = dict(self.options())
        values = [label_map.get(v, v) for v in self.values]
        values.sort()
        return '%s %s' % (op, ', '.join(values))

    def get_markup(self):
        if len(self.options()) > 10:
            return 'multiselect'
        else:
            return 'checkboxes'

    def _value_to_xml(self, xmlgen):
        for value in self.values:
            v = xmlgen.push('value')
            v.text(value)
            xmlgen.pop()


class CasesetTerm(TermBase):
    
    op = 'caseset'

    def __init__(self, case_ids=None, caseset=None, field='case_id', **kw):
        TermBase.__init__(self, field, **kw)
        if case_ids is None:
            case_ids = []
        self.values = case_ids
        self.caseset = caseset

    def _set_params(self, params):
        if self.params is None:
            self.params = params
            self.field_ops = CasesetDemogFieldOps(self)

    def desc(self):
        return 'Case set: %s (%d cases)' % (self.caseset, len(self.values))

    def _attr_to_xml(self, node):
        node.attr('caseset', self.caseset)

    def _value_to_xml(self, xmlgen):
        e = xmlgen.push('commalist')
        e.text(','.join([str(v) for v in self.values]))
        xmlgen.pop()


class SelectTerm(TermBase):

    op = 'select'

    def desc(self):
        label_map = {}
        for v, l in self.options():
            label_map[str(v)] = l
        return 'is %s' % label_map.get(str(self.value), self.value)


class Conjunction(FilterBase):

    def __init__(self):
        self.children = []

    def desc(self):
        return self.op

    def deleted_filter(self):
        for child in self.children:
            if child.deleted_filter():
                return True
        return False

    def _set_params(self, params):
        self.params = params
        for child in self.children:
            child._set_params(params)

    def add_filter(self, filter):
        if self.params is not None and self.params.syndrome_id is not None:
            filter._set_params(self.params)
        self.children.append(filter)

    def del_filter(self, filter):
        try:
            self.children.remove(filter)
            return True
        except ValueError:
            for child in self.children:
                if hasattr(child, 'children') and child.del_filter(filter):
                    if not child.children:
                        self.children.remove(child)
                    return True
            return False

    def toggle_conj(self):
        if self.op == 'and':
            self.op = 'or'
        else:
            self.op = 'and'

    def _forms_used(self, used):
        for child in self.children:
            child._forms_used(used)

    def _check(self, msgs):
        okay_children = []
        for child in self.children:
            if not child._check(msgs):
                continue
            okay_children.append(child)
        self.children = okay_children
        return True

    def _trim(self):
        okay_children = []
        size = 0
        for child in self.children:
            child_size = child._trim()
            if child_size:
                okay_children.append(child)
                size += child_size
        self.children = okay_children
        return size

    def query(self, query):
        query = query.sub_expr(conjunction=self.op)
        for child in self.children:
            child.query(query)

    def to_xml(self, xmlgen):
        if self.children:
            e = xmlgen.push('filter')
            e.attr('op', self.op)
            for child in self.children:
                child.to_xml(xmlgen)
            xmlgen.pop()


class AndExpr(Conjunction):

    op = 'and'


class OrExpr(Conjunction):

    op = 'or'


class FilterGroup:

    has_field = None

    def __init__(self, params):
        self.params = params

    def available_filters(self):
        filters = [(fl.lower(), fl, fn) 
                   for fn, fl in self.filters()]
        filters.sort()
        filters = [(fn, fl) for fll, fl, fn in filters]
        filters.insert(0, ('', '- Choose filter -'))
        return filters


class DemogFilterGroup(FilterGroup):

    name = 'demog'
    label = 'Demographics'
    has_field = True

    def filters(self):
        demog_fields = self.params.demog_fields('report')
        for field in demog_fields:
            if field.name != 'case_definition':
                yield field.name, field.label

    def make_filter(self, adder):
        return make_term(adder.op, field=adder.field)

    def __repr__(self):
        return '<DemogFilterGroup name=%r, label=%r>' %\
            (self.name, self.label)


class FormFilterGroup(FilterGroup):

    has_field = True

    def __init__(self, params, name, label):
        FilterGroup.__init__(self, params)
        self.name = name
        self.label = label

    def filters(self):
        for input in self.params.form_info(self.name).load().get_inputs():
            name = input.column.lower()
            yield name, input.label or input.column

    def make_filter(self, adder):
        return make_term(adder.op, field=adder.field, form=adder.group)

    def __repr__(self):
        return '<FormFilterGroup name=%r, label=%r>' %\
            (self.name, self.label)


class AndSubexpressionGroup(FilterGroup):
    
    name = 'andsubexpr'
    label = 'AND Subexpression'

    def make_filter(self, adder):
        return AndExpr()


class OrSubexpressionGroup(FilterGroup):
    
    name = 'orsubexpr'
    label = 'OR Subexpression'

    def make_filter(self, adder):
        return OrExpr()


class FilterAdder(list):

    def __init__(self, params, parent):
        self.params = params
        self.parent = parent
        self.group = 'demog'
        self.field = None
        self.op = None
        self.append(DemogFilterGroup(self.params))
        self.append(AndSubexpressionGroup(self.params))
        self.append(OrSubexpressionGroup(self.params))
        for info in self.params.all_form_info():
            self.append(FormFilterGroup(self.params, info.name, info.label))
        self.group_map = dict([(group.name, group) for group in self])
        self.placeholder = PlaceholderTerm()
        if parent is not None:
            self.parent.add_filter(self.placeholder)

    def groups(self):
        return [(group.name, group.label) for group in self]

    def has_field(self):
        group = self.group_map.get(self.group)
        return group is not None and group.has_field

    def fields(self):
        return self.group_map.get(self.group).available_filters()

    def field_ops(self):
        return field_ops_cache.available_ops(self.params, 
                                             self.field, self.group)

    def abort(self):
        self.parent.del_filter(self.placeholder)

    def is_complete(self):
        group = self.group_map.get(self.group)
        if group is None:
            return False
        if not group.has_field:
            return True
        if not self.field:
            return False
        ops = self.field_ops()
        if len(ops) < 2:
            self.op = ops[0]
            return True
        return bool(self.op)

    def add(self):
        self.parent.del_filter(self.placeholder)
        group = self.group_map.get(self.group)
        filter = group.make_filter(self)
        if filter is not None:
            self.parent.add_filter(filter)
        return filter


def yield_nodes(root):
    """
    Yield a stream of events like:
      'open', parent
        'clause', child
        'op', 'AND'
        'open', child
          'clause', childchild
          'op', 'OR'
          'clause', childchild
        'close, child
      'close', parent
    """
    class StackLevel:
        def __init__(self, node):
            self.node = node
            self.index = 0
            self.child_iter = iter(node.children)

        def next_child(self):
            try:
                node = self.child_iter.next()
            except StopIteration:
                node = None
            try:
                return self.index, node
            finally:
                self.index += 1

    stack = [StackLevel(root)]
    path = [None]
    while stack:
        level = stack[-1]
        index, child = level.next_child()
        path[-1] = str(index)
        levelpath = '.'.join(path[:-1])
        if index == 0:
            yield 'open', levelpath, level.node
        if child is None:
            yield 'close', levelpath, level.node
            del stack[-1]
            del path[-1]
        else:
            #if index != 0:
            #    yield 'op', levelpath, level.node
            if hasattr(child, 'children'):
                stack.append(StackLevel(child))
                path.append(None)
            else:
                yield 'clause', '.'.join(path), child


class FilterParamsMixin:

    show_filters = True

    def init(self):
        self.add_filter(AndExpr())

    def walk_filters(self):
        return yield_nodes(self.filter)

    def path_filter(self, path):
        node = self.filter
        if path:
            path = map(int, path.split('.'))
            for index in path:
                node = node.children[index]
        return node

    def make_term(self, op, **kw):
        term = make_term(op, **kw)
        term._set_params(self)
        return term

    def add_filter(self, filter):
        filter._set_params(self)
        self.filter = filter

    def del_filter(self, filter):
        return self.filter.del_filter(filter)

    def filter_adder(self, parent):
        return FilterAdder(self, parent)

    def caseset_filter(self, case_ids, name):
        self.filter.add_filter(CasesetTerm(case_ids, name))

    def deleted_filter(self):
        return self.filter.deleted_filter()

    def filter_query(self, query, form_based=False):
        if not self.filter._trim():
            return
        forms = set()
        self.filter._forms_used(forms)
        if forms:
            if not form_based:
                # This isolates the cartesian product effect of form joins
                # from the case query, preventing duplication of cases.
                query = query.in_select('cases.case_id', 'cases',
                                    columns=['cases.case_id'])
                query.join('JOIN persons USING (person_id)')
                query.where('syndrome_id = %s', self.syndrome_id)
            for form_name in forms:
                table = self.form_info(form_name).tablename()
                # We use a implicit view-join here to hide the indirection
                # through the case_form_summary table, making the results of
                # the join more intuitive.
                query.join('LEFT JOIN (SELECT case_id, %s.* FROM %s'
                            ' JOIN case_form_summary USING (summary_id)'
                            ' WHERE NOT deleted)'
                           ' AS %s USING (case_id)' % (table, table, table))
        self.filter.query(query)

    def _check(self, msgs):
        self.filter._set_params(self)
        self.filter._check(msgs)

    def _forms_used(self, used):
        self.filter._forms_used(used)

    def _to_xml(self, xmlgen, curnode):
        self.filter._trim()
        self.filter.to_xml(xmlgen)
