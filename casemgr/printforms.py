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

from cocklebur import form_ui
from casemgr import globals, demogfields, syndrome

class UIError(globals.Error): pass

class DemographicsForm:
    def __init__(self, syndrome_id):
        self.label = '_demographics'
        self.syndrome_id = syndrome_id
        self.name = 'Demographics/Identification'
        self.version = None

    def get_form_ui(self):
        synd = syndrome.syndromes[self.syndrome_id]
        f = form_ui.Form('%s %s' % (synd.name, self.name), table='None')
        f.question(text=synd.description, inputs=[])
        demog_fields = demogfields.get_demog_fields(globals.db, 
                                                    self.syndrome_id)
        for field in demog_fields.context_fields('case'):
            if field.render in ('textinput', 'case_dob'):
                f.question(text=field.label, 
                    input=form_ui.TextInput(field.name))
            elif field.render == 'textarea':
                f.question(text=field.label,
                    input=form_ui.TextArea(field.name))
            elif field.render == 'dateinput':
                f.question(text=field.label, 
                    input=form_ui.TextInput(field.name, post_text='dd-mm-yyyy'))
            elif field.render == 'datetimeinput':
                f.question(text=field.label, 
                    input=form_ui.TextInput(field.name, 
                                post_text='dd-mm-yyyy HH:MM'))
            elif field.render == 'select':
                f.question(text=field.label, 
                           input=form_ui.RadioList(field.name, 
                                                   choices=field.optionexpr()))
        f.update_labels()
        return f


class LoadForm:
    def __init__(self, label, name, version):
        self.label = label
        self.name = name
        self.version = version

    def get_form_ui(self):
        return globals.formlib.load(self.label, self.version)


class Forms:
    def __init__(self, syndrome_id):
        self.clear()
        self.loaded_syndrome_id = None
        self.loaded_form_type = None
        self.syndrome_id = syndrome_id
        self.forms = None
        self.refresh()

    def refresh(self):
        if self.loaded_syndrome_id != self.syndrome_id:
            query = globals.db.query('forms', order_by='syndrome_forms_id')
            query.join('RIGHT JOIN syndrome_forms'
                       ' ON forms.label = syndrome_forms.form_label')
            query.where('syndrome_id = %s', self.syndrome_id)
            rows = query.fetchcols(('label', 'name', 'cur_version'))
            self.forms = [LoadForm(*r) for r in rows]
            self.forms.insert(0, DemographicsForm(self.syndrome_id))
            self.loaded_syndrome_id = self.syndrome_id

    def select_all(self):
        self.include_forms = [f.label for f in self.forms]

    def clear(self):
        self.include_forms = []

    def selected_forms(self):
        forms = []
        for form in self.forms:
            if form.label in self.include_forms:
                forms.append(form)
        return forms

    def check_forms(self):
        if not self.include_forms:
            raise UIError('Please select one or more forms')
        all_okay = True
        for form in self.forms:
            if form.label in self.include_forms:
                try:
                    form.get_form_ui()
                except FormError:
                    self.include_forms.remove(form.label)
                    all_okay = False
        if not all_okay:
            raise UIError('Some forms contain errors and have been disabled')
