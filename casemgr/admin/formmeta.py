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

# Standard modules
import os
import re
import pwd
import time
import errno

# Project modules
from casemgr import globals
from cocklebur import datetime, form_ui, dbobj
from casemgr.admin import formedit
from casemgr.admin.formrollforward import formrollforward
from casemgr.formutils import deploy, delete, rename, usedby
import config

class Error(Exception): pass

Errors = (form_ui.FormError, Error, dbobj.DatabaseError)

# The form label may potentially be used as a filename, which has security
# implications if not carefully validated.
valid_identifier_re = re.compile('^[a-z][a-z0-9_]*$', re.IGNORECASE)
def valid_form_label(label):
    dbobj.valid_identifier(label, 'form name', reserve=len('form__00000_pkey'))
    if not label.islower():
        raise dbobj.IdentifierError('%r must be all lower case' % label)
    if not valid_identifier_re.match(label):
        raise dbobj.IdentifierError('form name %r contains invalid characters'% 
                                    label)


class FormMeta:
    orig_label = '[orig]'

    def __init__(self, dbrow, cred=None):
        self.name = dbrow.label         # Yes, it's muddled-up
        self.cred = cred
        self.root = None
        self.version = None
        self._set_dbrow(dbrow)
        try:
            self.load_version(self.highest_file_vers())
        except form_ui.NoFormError:
            self.from_form(form_ui.Form(''))
            self.clear_changed()

    def from_form(self, form):
        self.root = formedit.Root(form)
        if not self.name:
            self.name = form.name

    def to_form(self):
        return self.root.to_form(self.name)

    def copy_attrs(self, src, dst):
        for attr in ('allow_multiple', 'form_type'):
            setattr(dst, attr, getattr(src, attr))

    def _set_dbrow(self, dbrow):
        self.dbrow = dbobj.RowCache(dbrow)

    def vers_deployed(self):
        """
        Return the currently deployed version number
        """
        return self.dbrow.cur_version

    def _vers_from_str(self, v):
        if not v or v == self.orig_label:
            return None
        else:
            return int(v)

    def vers_changed(self, v):
        """
        Compare v to the currently loaded version.

        v can be a string (from form input), in which case
        it is cast to an int.
        """
        return self._vers_from_str(v) != self.version

    def clear_changed(self):
        """
        Clear "changed" status.
        """
        self.root.clear_changed()

    def has_changed(self):
        """
        Has anything changed?
        """
        return self.root.has_changed()

    def available_vers(self):
        return globals.formlib.versions(self.name)

    def highest_file_vers(self, name=None, path=None):
        if name is None:
            name = self.name
        return globals.formlib.latest_version(name)

    def load_version(self, version):
        if isinstance(version, basestring):
            version = self._vers_from_str(version)
        form = globals.formlib.load(self.name, version)
        self.version = version
        self.from_form(form)
        self.clear_changed()

    def _write_version(self, name, *args):
        form = self.to_form()
        if self.cred:
            form.author = self.cred.user.fullname
            form.username = self.cred.user.username
        form.update_time = datetime.now()
        globals.formlib.save(form, name, *args)
        self.root.update_time = form.update_time
        return form.version, form.update_time

    def _updaterow(self, db, action, *args, **kwargs):
        """
        Obtain a row-locked copy of the current row, and pass it
        to the supplied callback for processing. If the callback
        returns, the row will be committed. If it raises an
        exception, the transaction will be rolled back.
        """
        query = db.query('forms', for_update=True)
        query.where('label = %s', self.name)
        try:
            dbrow = query.fetchone()
            if dbrow is None:
                dbrow = db.new_row('forms')
            action(dbrow, *args, **kwargs)
        except:
            db.rollback()
            raise
        db.commit()
        self._set_dbrow(dbrow)

    def save(self, db):
        """
        Save the current form definition to the next available
        version number.
        """
        def write_update_row(dbrow):
            self.version, dbrow.def_update_time = self._write_version(self.name)
            dbrow.db_update()

        if self.dbrow.is_new():
            self.save_as(db, self.name)
        else:
            self._updaterow(db, write_update_row)
            self.clear_changed()

    def deploy(self, db, rollforward_map=None):
        """
        Deploy the current form version (create any form instance table).
        """
        def update_row(dbrow):
            highest_version = self.highest_file_vers()
            if self.version != highest_version:
                # If not the latest version, save first, so "deployed" version
                # always increments.
                version, update_time = self._write_version(self.name)
                self.version = version
            table = globals.formlib.tablename(self.name, self.version)
            form = self.to_form()
            deploy.make_form_table(db, form, table)
            if config.form_rollforward:
                assert rollforward_map is not None
                try:
                    formrollforward(db, self.name, self.version, 
                                    rollforward_map)
                except dbobj.DatabaseError, e:
                    raise Error('Data roll-forward (and deploy) failed - new schema may be incompatible (%s)' % e)
            dbrow.cur_version = self.version
            self.copy_attrs(self.root, dbrow)
            dbrow.name = self.root.text
            dbrow.db_update()
            db.save_describer()

        assert not self.has_changed()
        self._updaterow(db, update_row)

    def rename(self, db, new_name):
        """
        Rename the current form
        """
        assert not self.has_changed()
        new_name = new_name.lower()
        valid_form_label(new_name)
        try:
            self.dbrow = rename.rename_form(self.name, new_name)
            self.name = self.dbrow.label
        except dbobj.DuplicateKeyError, e:
            raise Error('New name is already used')

    def save_as(self, db, new_name):
        """
        Save the current form with a new name (creating forms table
        row and form definition file).
        """
        new_name = new_name.lower()
        valid_form_label(new_name)
        dbrow = db.new_row('forms')
        version, dbrow.def_update_time = self._write_version(new_name)
        dbrow.label = new_name
        dbrow.name = self.root.text
        try:
            dbrow.db_update()
        except dbobj.DuplicateKeyError:
            db.rollback()
            raise Error('New name is already used')
        db.commit()
        self.name = new_name
        self.version = version
        self._set_dbrow(dbrow)
        self.clear_changed()

    def used_by(self, db):
        """
        Return an ordered list of syndromes that use this form
        """
        return usedby.form_syndromes(self.name)

    def delete(self, db):
        self.dbrow = delete.delete_form(self.name)
