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

#   Describe a library of forms

__all__ = 'FormLibPyFiles', 'FormLibXMLDB', 

import os
import re
import fcntl
from cStringIO import StringIO
from cocklebur import dbobj
from cocklebur.form_ui.common import *
from cocklebur.form_ui.xmlsave import xmlsave
from cocklebur.form_ui.xmlload import xmlload
from cocklebur.form_ui.pysave import pysave
from cocklebur.form_ui.pyload import pyload

class nextversion: pass

class _FormLibForm:
    def __init__(self, formlib, name, version, **kw):
        self.__dict__.update(kw)
        self.formlib = formlib
        self.name = name
        self.version = version

    def load(self):
        return self.formlib.load(self.name, self.version)

    def __repr__(self):
        return '<form %s vers %s>' % (self.name, self.version)

    def __cmp__(self, other):
        return cmp((self.name, self.version), (other.name, other.version))


class FormLibBase:
    def __init__(self):
        self.cache = {}

    def __iter__(self):
        return []

    def __len__(self):
        return 0

    table_re = re.compile(r'^form_(.*)_(\d{5})$')

    def form_tables(self, db, table_name):
        for table in db.get_tables():
            match = self.table_re.match(table.name)
            if match and match.group(1) == table_name:
                yield table

    def tablename(self, name, version):
        if version is None:
            version = 0
        return 'form_%s_%05d' % (name, version)

    def latest(self):
        latest = {}
        for ff in self:
            try:
                prev_ff = latest[ff.name]
            except KeyError:
                latest[ff.name] = ff
            else:
                if prev_ff.version < ff.version:
                    latest[ff.name] = ff
        latest = latest.values()
        latest.sort()
        return latest

    def latest_version(self, name):
        pass

    def versions(self, name):
        return []

    def save(self, form, name, version=nextversion):
        pass

    def load(self, name, version):
        try:
            form = self.cache[(name, version)]
        except KeyError:
            form = self.cache[(name, version)] = self._load(name, version)
        return form

    def rename(self, oldname, newname):
        pass

    def delete(self, name):
        pass

    def _update(self, form, name, version):
        form.name = name
        form.version = version
        form.table = self.tablename(name, version)
        form.update_columns()
        form.update_labels()
        form.update_xlinks()


class FormLibPyFiles(FormLibBase):
    """
    A library of forms stored as .py files in a filesystem directory
    """
    form_mod_re = re.compile('^([a-zA-Z0-9_]+?)(_[0-9]+)?(\.[^.]*)$')

    def __init__(self, path):
        FormLibBase.__init__(self)
        self.path = path
        self.lock_fd = None
        self.lockfilename = os.path.join(self.path, '.lock')

    def __iter__(self):
        files = os.listdir(self.path)
        files.sort()
        for fn in files:
            match = self.form_mod_re.match(fn)
            if match:
                name, rev, ext = match.groups()
                if ext != '.py':
                    continue
                if rev:
                    rev = int(rev[1:])
                yield _FormLibForm(self, name, rev, 
                                   filename=os.path.join(self.path, fn))

    def __len__(self):
        return len(list(iter(self)))

    def _lock(self):
        self.lock_fd = os.open(self.lockfilename, os.O_WRONLY|os.O_CREAT, 0666)
        fcntl.lockf(self.lock_fd, fcntl.LOCK_EX)

    def _unlock(self):
        if self.lock_fd is not None:
            os.close(self.lock_fd)
            self.lock_fd = None

    def filename(self, name, version=None, ext='.py'):
        if version:
            fn = '%s_%05d%s' % (name, version, ext)
        else:
            fn = '%s%s' % (name, ext)
        return os.path.join(self.path, fn)

    def latest_version(self, name):
        version = 0
        for ff in self:
            if ff.name == name and ff.version > version:
                version = ff.version
        return version

    def versions(self, name):
        return [ff.version for ff in self if ff.name == name]

    def save(self, form, name, version=nextversion):
        self._lock()
        try:
            if version is nextversion:
                version = self.latest_version(name) + 1
            filename = self.filename(name, version)
            f = open(filename, 'w')
            try:
                pysave(f, form)
            except:
                f.close()
                os.unlink(filename)
                raise
            f.close()
            self._update(form, name, version)
            return version
        finally:
            self._unlock()

    def _load(self, name, version):
        try:
            f = open(self.filename(name, version))
        except IOError, e:
            raise NoFormError(str(e))
        try:
            form = pyload(f)
        finally:
            f.close()
        self._update(form, name, version)
        return form

    def rename(self, oldname, newname):
        self._lock()
        try:
            if self.versions(newname):
                raise DuplicateFormError('form name %r is already used' % 
                                         newname)
            count = 0
            for ff in self:
                if ff.name == oldname:
                    os.rename(ff.filename, self.filename(newname, ff.version))
                    count += 1

            if not count:
                raise NoFormError('No form %r' % (oldname))
        finally:
            self._unlock()

    def delete(self, name):
        # FUTURE work - some sort of "trashcan" undelete?
        self._lock()
        try:
            count = 0
            for ff in self:
                if ff.name == name:
                    count += 1
                    try:
                        os.unlink(ff.filename)
                    except OSError:
                        pass
            if not count:
                raise NoFormError('No form %r' % (name))
        finally:
            self._unlock()



class FormLibXMLDB(FormLibBase):
    """
    A library of forms stored as XML in a database table 
    (with optional filesystem caching?).
    """
    # Implement filesystem caching of parsed forms
    # Implement in-core caching of names and versions? Only really of use to
    # admin form edit.

    def __init__(self, db, table):
        FormLibBase.__init__(self)
        self.db = db
        self.table = table

    def __iter__(self):
        query = self.db.query(self.table, order_by=('name', 'version'))
        for name, version in query.fetchcols(('name', 'version')):
            yield _FormLibForm(self, name, version)

    def __len__(self):
        query = self.db.query(self.table)
        return int(query.aggregate('COUNT(*)'))

    def latest_version(self, name):
        query = self.db.query(self.table)
        query.where('name = %s', name)
        version = query.aggregate('max(version)')
        if version:
            return version
        return 0

    def versions(self, name):
        query = self.db.query(self.table, order_by='version')
        query.where('name = %s', name)
        return query.fetchcols('version')

    def save(self, form, name, version=nextversion):
        f = StringIO()
        xmlsave(f, form)
        row = self.db.new_row(self.table)
        row.name = name
        row.xmldef = f.getvalue()
        self.db.lock_table(self.table, 'EXCLUSIVE')
        if version is nextversion:
            version = self.latest_version(name) + 1
        else:
            if version is None:
                version = 0
        row.version = version
        row.db_update()
        self._update(form, name, version)
        return version

    def _load(self, name, version):
        if version is None:
            version = 0
        query = self.db.query(self.table)
        query.where('name = %s', name)
        query.where('version = %s', version)
        row = query.fetchone()
        if row is None:
            raise NoFormError('No form %r, version %d' % (name, version))
        form = xmlload(StringIO(row.xmldef))
        self._update(form, name, version)
        return form

    def rename(self, oldname, newname):
        self.db.lock_table(self.table, 'EXCLUSIVE')
        if self.versions(newname):
            raise DuplicateFormError('form name %r is already used' % newname)
        curs = self.db.cursor()
        try:
            dbobj.execute(curs, 
                          'UPDATE %s SET name=%%s WHERE name=%%s' % self.table,
                          (newname, oldname))
            if curs.rowcount == 0:
                raise NoFormError('No form %r' % oldname)
        finally:
            curs.close()

    def delete(self, name):
        self.db.lock_table(self.table, 'EXCLUSIVE')
        curs = self.db.cursor()
        try:
            dbobj.execute(curs, 
                          'DELETE FROM %s WHERE name=%%s' % self.table, (name,)) 
            if curs.rowcount == 0:
                raise NoFormError('No form %r' % name)
        finally:
            curs.close()
