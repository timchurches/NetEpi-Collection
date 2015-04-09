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

from casemgr import globals, syndrome, dataexport

import config

class ExportSelect:
    def __init__(self, syndrome_id):
        self.syndrome_id = syndrome_id
        self.export_scheme = 'classic'
        self.deleted = 'n'
        self.strip_newlines = False
        self.exporter = None
        self.ready = False
        self.saved_args = None
        self.clear_forms()

    def show_schemes(self):
        return bool(self.syndrome_id)

    def scheme_options(self):
        return [
            ('classic', 'By case, include form name in column labels'),
            ('doha', 'By case, short column labels'),
            ('form', 'By form'),
            ('contacts', 'Case %ss' % config.contact_label),
        ]

    def multi_form_sel(self):
        return self.export_scheme != 'form'

    def clear_forms(self):
        self.include_forms = []

    def select_all_forms(self):
        if self.exporter is None:
            self.include_forms = []
        else:
            self.include_forms = [form.label for form in self.exporter.forms]

    def refresh(self, credentials):
        args = [self.syndrome_id]
        if self.export_scheme == 'contacts':
            cls = dataexport.ContactExporter
        else:
            cls = dataexport.CaseExporter
        kwargs = {}
        kwargs['format'] = self.export_scheme
        kwargs['deleted'] = self.deleted
        kwargs['strip_newlines'] = (str(self.strip_newlines) == 'True')
#        print >> sys.stderr, 'ExportSelect: %s saved %r now %r' %\
#            (self.exporter.__class__, self.saved_args, (args, kwargs))
        if (self.exporter is None or not isinstance(self.exporter, cls)
                or self.saved_args != (args, kwargs)):
            self.exporter = cls(credentials, *args, **kwargs)
            self.saved_args = args, kwargs
            if self.multi_form_sel():
                if not isinstance(self.include_forms, list):
                    self.include_forms = [self.include_forms]
            else:
                if isinstance(self.include_forms, list):
                    if self.include_forms:
                        self.include_forms = self.include_forms[0]
                    else:
                        self.include_forms = None
            return True
        return False

    def filename(self):
        return self.exporter.filename()

    def row_gen(self):
        include_forms = self.include_forms
        if not isinstance(include_forms, list):
            include_forms = [include_forms]
        return self.exporter.row_gen(include_forms)
