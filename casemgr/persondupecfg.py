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

import copy

from casemgr import globals
from casemgr import demogfields

class NGramGroup(object):
    special_fields = ('DOB', 'Sex')
    def __init__(self, label, weight, fields, editable=True):
        self.label = label
        self.weight = weight
        self.fields = fields
        self.editable = editable
        self.enabled = True

    def demogfields(self):
        fields = demogfields.get_demog_fields(globals.db, None)
        return [fields.field_by_name(field) for field in self.fields]

    def fields_optionexpr(self):
        fields = demogfields.get_demog_fields(globals.db, None)
        return [(field.name, field.label) 
                for field in fields
                if (field.entity == 'person'
                    and field.name not in self.special_fields)]

        self.label = other.label
        self.weight = other.weight
        self.fields = list(other.fields)

    def reset(self):
        try:
            group_defaults = defaults[self.index]
        except IndexError:
            return
        self.label = group_defaults.label
        self.weight = group_defaults.weight
        self.fields = group_defaults.fields
        self.enabled = group_defaults.enabled


defaults = [
    NGramGroup('Names', 1.0, ['surname', 'given_names']),
    NGramGroup('Sex', 1.0, ['sex'], editable=False),
    NGramGroup('Age', 1.0, ['DOB'], editable=False),
    NGramGroup('Addresses', 1.0, 
                ['street_address', 'locality',
                'state', 'postcode', 'country',
                'alt_street_address', 'alt_locality',
                'alt_state', 'alt_postcode', 'alt_country',
                'work_street_address', 'work_locality',
                'work_state', 'work_postcode', 'work_country']),
    NGramGroup('Phone', 1.0, 
                ['home_phone', 'work_phone',
                'mobile_phone', 'fax_phone', 'e_mail']),
    NGramGroup('Passport', 1.0, 
                ['passport_number', 'passport_country',
                'passport_number_2', 'passport_country_2'])
]


class PersonDupeCfg(object):
    cutoff_options = [(c / 100.0, '%d%%' % c)
                        for c in range(55,100,5)]

    def __init__(self):
        self.ngram_level = 3
        self.cutoff = 0.5
        self.ngram_groups = []

    def edit_group(self, index):
        if index is None:
            group = NGramGroup('', 1.0, [])
            group.initial = group
        else:
            group = copy.deepcopy(self.ngram_groups[index])
        group.index = index
        return group

    def apply_group(self, group):
        index = group.index
        if group.fields or (index and index < len(defaults)):
            del group.index
            group.enabled = (str(group.enabled) == 'True')
            group.weight = float(group.weight)
            if index is None:
                self.ngram_groups.append(group)
            else:
                self.ngram_groups[index] = group
        elif index:
            del self.ngram_groups[index]

    def reset(self):
        self.ngram_level = 3
        self.cutoff = 0.5
        self.ngram_groups = copy.deepcopy(defaults)

    def start_editing(self):
        return copy.deepcopy(self)

    def stop_editing(self):
        self.ngram_level = int(self.ngram_level)
        self.cutoff = float(self.cutoff)
#        self.ngram_groups = [group for group in self.ngram_groups
#                             if group.fields]


def new_persondupecfg():
    cfg = PersonDupeCfg()
    cfg.reset()
    return cfg
