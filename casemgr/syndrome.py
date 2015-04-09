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
import time
try:
    set
except NameError:
    from sets import Set as set

from cocklebur import dbobj, datetime
import config
from casemgr import globals, cached

def query_by_group(group_id):
    query = globals.db.query('syndrome_types', 
                             order_by=config.order_syndromes_by)
    query.where('enabled')
    synd_query = query.in_select('syndrome_id', 'group_syndromes')
    synd_query.where('group_id = %s', group_id)
    cont_query = synd_query.in_select('syndrome_id', 'group_syndromes')
    cont_query.where('group_id = %s', group_id)
    return query


class SyndFormInfo(object):
    __slots__ = 'name', 'label', 'version'

    def __init__(self, name, label, version):
        self.name = name
        self.label = label
        self.version = version

    def __getinitargs__(self):
        return self.name, self.label, self.version

    def load(self):
        return globals.formlib.load(self.name, self.version)

    def tablename(self):
        return globals.formlib.tablename(self.name, self.version)


class Syndrome(object):
    def __init__(self, syndrome_id):
        self.syndrome_id = syndrome_id
        self.case_count = None

    def update(self, name, description, priority, enabled, 
               post_date, expiry_date,
               has_additional_info):
        self.name = name
        self.description = description
        self.priority = priority
        self.enabled = enabled
        self.post_date = datetime.mx_parse_datetime(post_date)
        self.expiry_date = datetime.mx_parse_datetime(expiry_date)
        self.has_additional_info = has_additional_info
        self.forms = None
        self.forms_by_name = None

    def active(self):
        now = datetime.now()
        return (self.enabled 
                and (not self.post_date or self.post_date <= now)
                and (not self.expiry_date or self.expiry_date > now))

    def getrow(self):
        query = globals.db.query('syndrome_types')
        query.where('syndrome_id = %s', self.syndrome_id)
        return query.fetchone()

    def load_synd_forms(self):
        query = globals.db.query('syndrome_forms', order_by='name')
        query.join('JOIN forms ON (form_label = label)')
        query.where('syndrome_id = %s', self.syndrome_id)
        self.forms = []
        self.forms_by_name = {}
        for row in query.fetchcols(('form_label', 'name', 'cur_version')):
            info = SyndFormInfo(*row)
            self.forms.append(info)
            self.forms_by_name[info.name.lower()] = info

    def all_form_info(self):
        if self.forms is None:
            self.load_synd_forms()
        return self.forms

    def form_info(self, name):
        if self.forms_by_name is None:
            self.load_synd_forms()
        return self.forms_by_name.get(name.lower())

    def desc_status(self):
        res = []
        if self.active():
            res.append('active')
        else:
            if self.enabled:
                res.append('disabled by post date or expiry date')
            else:
                res.append('disabled administratively')
        if self.case_count == 1:
            res.append('1 record')
        elif self.case_count:
            res.append('%d records' % self.case_count)
        return res

    def __reduce__(self):
        # No point pickling the whole object, just the constructor and ID
        return _syndrome_reduce, (self.syndrome_id,)

def _syndrome_reduce(syndrome_id):
    return syndromes[syndrome_id]


class CaseCountMixin(object):
    def __init__(self):
        self.__want_refresh = set()
        self.__syndrome_ids = set()
        self.__refresh_time = time.time()
        globals.notify.subscribe('syndromecasecount',
                                 self.__notification)

    def __notification(self, *args):
        self.__want_refresh.update(map(int, args))

    def refresh(self):
        now = time.time()
        all = set(self.syndrome_ids())
        seen = self.__syndrome_ids
        if self.__refresh_time + 120 < now:
            seen = set()
        # Any new syndromes, plus ones with new cases
        refresh = all - seen | self.__want_refresh
        self.__syndrome_ids = all
        if refresh:
            self.__refresh_time = now
            query = globals.db.query('cases', group_by='syndrome_id')
            query.where('not deleted')
            query.where_in('syndrome_id', refresh)
            cols = 'syndrome_id', 'count(*)'
            for syndrome_id, count in query.fetchcols(cols):
                try:
                    synd = self.by_id[syndrome_id]
                except KeyError:
                    pass
                else:
                    synd.case_count = count
            self.__want_refresh = set()


def membership_sets(table, group_col, member_col):
    membership_by_group = {}
    query = globals.db.query(table)
    for group, member in query.fetchcols((group_col, member_col)):
        try:
            membership = membership_by_group[group]
        except KeyError:
            membership = membership_by_group[group] = set()
        membership.add(member)
    return membership_by_group


class UnitSyndromes(cached.NotifyCache):

    notification_target = 'syndrome_units'

    def __init__(self):
        cached.NotifyCache.__init__(self)

    def load(self):
        syndromes_by_group = membership_sets('group_syndromes', 
                                             'group_id', 'syndrome_id')
        query = globals.db.query('unit_groups')
        unit_syndromes_by_unit = {}
        for unit_id, group_id in query.fetchcols(('unit_id', 'group_id')):
            group_syndromes = syndromes_by_group.get(group_id)
            if group_syndromes:
                try:
                    unit_syndromes = unit_syndromes_by_unit[unit_id]
                except KeyError:
                    unit_syndromes_by_unit[unit_id] = group_syndromes
                else:
                    unit_syndromes = unit_syndromes | group_syndromes
                    unit_syndromes_by_unit[unit_id] = unit_syndromes
        self.unit_syndromes = unit_syndromes_by_unit

    def get_unit_syndromes(self, unit_id):
        self.refresh()
        return self.unit_syndromes.get(unit_id, ())

unit_syndromes = UnitSyndromes()


class Syndromes(cached.NotifyCache, CaseCountMixin):

    notification_target = 'syndromes'

    def __init__(self):
        cached.NotifyCache.__init__(self)
        CaseCountMixin.__init__(self)
        self.by_id = {}
        self.in_order = []
        self.active_in_order = []

    def refresh(self):
        cached.NotifyCache.refresh(self)
        CaseCountMixin.refresh(self)

    def load(self):
        query = globals.db.query('syndrome_types', 
                                 order_by=config.order_syndromes_by)
        by_id = {}
        in_order = []
        active_in_order = []
        cols = (
            'syndrome_id', 'name', 'description', 
            'priority', 'enabled', 'post_date', 'expiry_date',
            'additional_info is not null'
        )
        for row in query.fetchcols(cols):
            syndrome_id = row[0]
            try:
                synd = self.by_id[syndrome_id]
            except KeyError:
                synd = Syndrome(syndrome_id)
            synd.update(*row[1:])
            by_id[syndrome_id] = synd
            in_order.append(synd)
            if synd.active():
                active_in_order.append(synd)
        # We defer setting attributes until the last moment so if an error
        # occurs, the previous state of the object is still usable.
        self.by_id = by_id
        self.in_order = in_order
        self.active_in_order = active_in_order

    def syndrome_ids(self):
        return [s.syndrome_id for s in self.in_order]

    def __getitem__(self, index):
        self.refresh()
        try:
            return self.by_id[int(index)]
        except (LookupError, TypeError, ValueError):
            raise LookupError('Invalid %s id %r' % (config.syndrome_label, index))

    def all(self):
        self.refresh()
        return self.in_order

    def __contains__(self, syndrome_id):
        self.refresh()
        return syndrome_id in self.by_id

    def __iter__(self):
        self.refresh()
        return iter(self.active_in_order)

    def __nonzero__(self):
        self.refresh()
        return len(self.active_in_order) > 0

    def __getstate__(self):
        # Prevent pickling - force people to use module-level instance
        raise TypeError

    def optionexpr(self):
        return [(s.syndrome_id, s.name) for s in self.all()]


#    def __reduce__(self):
#        # Ensure pickle uses module level instance
#        return _syndromes_reduce
#
#def _syndromes_reduce():
#    return syndromes

syndromes = Syndromes()

class UnitSyndromesView:
    """
    A view of the global /syndromes/, including only syndromes the user
    has the rights to see.
    """

    def __init__(self, credentials):
        self.credentials = credentials

    def _unit_syndromes(self):
        return unit_syndromes.get_unit_syndromes(self.credentials.unit.unit_id)

    def __getitem__(self, syndrome_id):
        return syndromes[syndrome_id]

    def __nonzero__(self):
        if config.show_all_syndromes:
            return bool(syndromes)
        else:
            us = self._unit_syndromes()
            for synd in syndromes:
                if synd.syndrome_id in us:
                    return True
            return False

    def __contains__(self, syndrome_id):
        if config.show_all_syndromes:
            return syndrome_id in syndromes
        else:
            return syndrome_id in self._unit_syndromes()

    def __iter__(self):
        if config.show_all_syndromes:
            for synd in syndromes:
                yield synd
        else:
            us = self._unit_syndromes()
            for synd in syndromes:
                if synd.syndrome_id in us:
                    yield synd

    def options(self):
        return [(s.syndrome_id, s.name) for s in self]

    def anyoptions(self):
        options = self.options()
        options.insert(0, ('Any', 'Any'))
        return options

    def can_add(self, syndrome_id):
        return syndrome_id in self
