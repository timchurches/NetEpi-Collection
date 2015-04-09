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
import os
import csv
import codecs
try:
    set
except NameError:
    from sets import Set as set

from cocklebur import utils, datetime

from casemgr import globals

import config   # XXX scratchdir

if sys.version_info < (2,4):
    # Monkey patch utf16 codecs if python version is less than 2.4 to make up
    # for the lack of a .readline() method.  See
    # http://bugs.python.org/issue920680

    def readline(self):
        if not self._utf16_readline_buffer:
            self._utf16_readline_buffer = [u'']
        while True:
            line = self._utf16_readline_buffer.pop(0)
            if len(self._utf16_readline_buffer) > 0:
                return line
            chunk = self.read(256)
            if not chunk:
                return line
            line += chunk
            self._utf16_readline_buffer = line.splitlines(True)

    from encodings import utf_16
    from encodings import utf_16_be
    from encodings import utf_16_le

    for mod in utf_16, utf_16_be, utf_16_le:
        mod.StreamReader.readline = readline
        mod.StreamReader._utf16_readline_buffer = None


class DataImpError(globals.Error): pass


class Decoder:
    """
    Read lines from /filename/, decode using /encoding/ and return each line
    re-encoded as utf-8 (as the csv module does not support unicode at this
    time). Record line number for error reporting.
    """
    name = None

    def __init__(self, filename, encoding):
        self.filename = filename
        self.line_num = 0
        self.f = codecs.open(filename, 'rb', encoding)

    def __iter__(self):
        return self

    def next(self):
        self.line_num += 1
        try:
            return self.f.next().encode('utf-8')
        except UnicodeError, e:
            raise DataImpError('line %s: %s' % (self.line_num, e))

    def close(self):
        self.f.close()


class Row(object):

    __slots__ = ('fields', 'line_num', 'record_num')

    def __init__(self, fields, line_num, record_num):
        self.fields = fields
        self.line_num = line_num
        self.record_num = record_num


class SrcLoader:

    def __init__(self, name, filename, encoding, fieldsep, mode):
        self.name = name
        self.filename = filename
        self.encoding = encoding
        self.fieldsep = fieldsep
        self.mode = mode
        self.n_cols = None
        self.n_rows = None
        self.col_names = None
        self.__utf8_lines = Decoder(self.filename, self.encoding)
        self.__csv_reader = iter(csv.reader(self.__utf8_lines, 
                                            delimiter=self.fieldsep))
        if self.mode == 'named':
            try:
                col_names = self.__csv_reader.next()
            except StopIteration:
                return
            self.col_names = [n.strip().lower() for n in col_names]
            self.col_map = dict([(n, i) for i, n in enumerate(self.col_names)])
            self.n_cols = len(self.col_names)
        elif self.mode == 'positional':
            self.n_cols = None
        else:
            raise DataImpError('Unknown import rule mode %r' % mode)

    def __getstate__(self):
        raise TypeError('Cannot pickle %s' % self.__class__)

    def col_idx(self, name):
        index = None
        if self.mode == 'named':
            try:
                index = self.col_map[name.strip().lower()]
            except KeyError:
                raise DataImpError('Column %r not found in this source' % name)
        elif self.mode == 'positional':
            try:
                index = int(name.strip()) - 1
            except (TypeError, ValueError):
                raise DataImpError('Invalid column index %r' % name)
        return index

    def __iter__(self):
        self.n_rows = 0
        start_line = 1
        try:
            while 1:
                start_line = self.__utf8_lines.line_num + 1
                try:
                    fields = self.__csv_reader.next()
                except StopIteration:
                    break
                if not fields:
                    # Last line of file is often empty
                    continue
                if self.n_cols is None:
                    self.n_cols = len(fields)
                    self.col_names = map(str, range(1, self.n_cols+1))
                elif len(fields) != self.n_cols:
                    raise DataImpError('Column count is not constant: '
                                        'has %s columns, expected %s' % 
                                        (len(fields), self.n_cols))
                self.n_rows += 1
                yield Row(fields, start_line, self.n_rows)
        except Exception, e:
            try:
                self.close()
            except Exception:
                pass
            raise DataImpError('%s: record %s (line %s): %s' %
                (self.name, self.n_rows, start_line, e))
        self.close()

    def close(self):
        if self.__utf8_lines is not None:
            self.__utf8_lines.close()
            self.__utf8_lines = None
            self.__csv_reader = None


class Preview:

    def __init__(self):
        self.error = None
        self.rows = []
        self.n_rows = 0
        self.n_cols = 0
        self.col_names = []
        self.colvalues_by_col = {}

    def __nonzero__(self):
        return bool(self.n_rows)

    def colvalues(self, colname):
        colvalues = self.colvalues_by_col.get(colname.lower())
        if colvalues:
            colvalues = list(colvalues)
            colvalues.sort()
        return colvalues

    def colpreview(self, colname):
        if self.col_names:
            try:
                colnum = self.col_names.index(colname.lower())
            except ValueError:
                pass
            else:
                return [row[colnum] for row in self.rows]
        return []


class SrcPreview(Preview):

    def __init__(self, datasrc_rows):
        Preview.__init__(self)
        try:
            for row in datasrc_rows:
                if len(self.rows) < 16:
                    self.rows.append(row.fields)
                for i, colname in enumerate(datasrc_rows.col_names):
                    try:
                        colvalues = self.colvalues_by_col[colname]
                    except KeyError:
                        colvalues = self.colvalues_by_col[colname] = set()
                    if colvalues is not None:
                        if len(colvalues) > 200:
                            self.colvalues_by_col[colname] = None
                        else:
                            value = row.fields[i].strip()
                            if value and len(value) < 100:
                                colvalues.add(value)
            self.n_rows = datasrc_rows.n_rows
            self.n_cols = datasrc_rows.n_cols
            self.col_names = datasrc_rows.col_names
        except Exception, e:
            self.error = str(e)


class DataImpSrc(object):
    # XXX scratchdir isn't really the right place for this file - other
    # users could potentially read it by guessing file names. We will
    # probably need to write it to the database, keyed by user, but that
    # may pose problems when the data file is large, as libpq reads the
    # entire DB response into memory.

    def __init__(self, name, f):
        self.clear()
        if not name:
            return
        tmpfile = os.path.join(config.scratchdir, 
                               utils.randfn('imp', 'data'))
        data_f = open(tmpfile, 'wb')
        try:
            while 1:
                data = f.read(8192)
                if not data:
                    break
                data_f.write(data)
                self.size += len(data)
        finally:
            data_f.close()
        if not self.size:
            os.unlink(tmpfile)
            return
        self.name = name
        self.tmpfile = tmpfile
        self.received = datetime.now()

    def clear(self):
        self.tmpfile = None
        self.name = None
        self.size = 0
        self.received = None
        self.preview = Preview()

    def release(self):
        if self.tmpfile:
            try:
                os.unlink(self.tmpfile)
                self.clear()
            except OSError:
                pass

    def __nonzero__(self):
        if self.tmpfile:
            if os.path.exists(self.tmpfile):
                return True
            self.clear()
        return False

    def row_iterator(self, importrules):
        return SrcLoader(self.name, self.tmpfile,
                         importrules.encoding, 
                         importrules.fieldsep, 
                         importrules.mode)

    def update_preview(self, importrules):
        try:
            row_iter = self.row_iterator(importrules)
        except DataImpError, e:
            self.preview = Preview()
            self.preview.error = str(e)
        else:
            self.preview = SrcPreview(row_iter)


NullDataImpSrc = DataImpSrc(None, None)
