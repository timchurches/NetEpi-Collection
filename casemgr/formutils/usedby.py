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

from casemgr import globals, cached

class FormSyndromes(cached.Cached):
    time_to_live = 10
    def __init__(self, name):
        self.name = name

    def load(self):
        query = globals.db.query('syndrome_types')
        query.join('LEFT JOIN syndrome_forms USING (syndrome_id)')
        query.where('form_label = %s', self.name)
        self.form_syndromes = query.fetchcols('name')
        self.form_syndromes.sort()

class FormsSyndromes(dict):
    def form_syndromes(self, name):
        """
        Return an ordered list of syndromes that use this form
        """
        if not name:
            return []
        name = name.lower()
        try:
            form_syndromes = self[name]
        except KeyError:
            form_syndromes = self[name] = FormSyndromes(name)
        form_syndromes.refresh()
        return form_syndromes.form_syndromes

form_syndromes = FormsSyndromes().form_syndromes
