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

import sys, os
import re
try:
    set
except NameError:
    from sets import Set as set
from optparse import OptionParser, OptionGroup


def formlist(forms, names, options):
    if options.historical:
        formlist = forms
    else:
        formlist = forms.latest()
    if names:
        names = set(names)
        for flf in formlist:
            if flf.name in names:
                yield flf
    else:
        for flf in formlist:
            yield flf

def list_forms(forms, names, options):
    for flf in formlist(forms, names, options):
        print '%s:%d' % (flf.name, flf.version)


def export_forms(forms, names, options):
    if options.format == 'py':
        from cocklebur.form_ui.pysave import pysave as writer
    else:
        from cocklebur.form_ui.xmlsave import xmlsave as writer
    for flf in formlist(forms, names, options):
        form = flf.load()
        if options.historical:
            fn = '%s_%d.form' % (flf.name, flf.version)
        else:
            fn = '%s.form' % flf.name
        fn = os.path.join(options.exportdir, fn)
        try:
            f = open(fn, 'w')
        except IOError, (eno, estr):
            print >> sys.stderr, '%s: %s' % (fn, estr)
            continue
        bytecount = None
        try:
            try:
                writer(f, form)
                bytecount = f.tell()
            finally:
                f.close()
        except Exception:
            os.unlink(fn)
            raise
        if options.verbose and bytecount is not None:
            print 'exported %s:%s as %s (%d bytes)' %\
                (flf.name, flf.version, fn, bytecount)

class FFError(Exception): pass

class FF:
    form_mod_re = re.compile('^([a-zA-Z0-9_]+?)(_[0-9]+)?(\.[^.]*)$')

    def __init__(self, name, fn):
        if not os.path.exists(fn):
            raise FFError('%s: does not exist' % fn)
        self.fn = fn
        match = self.form_mod_re.match(name)
        if not match or match.group(3) not in ('.form', '.py'):
            raise FFError('%s: ignored' % fn)
        self.name = match.group(1)
        self.version = match.group(2)
        if self.version is not None:
            self.version = int(self.version[1:])

    def __cmp__(self, other):
        return cmp((self.name, self.version), (other.name, other.version))

def update_forms(db, name, form):
    query = db.query('forms')
    query.where('label = %s', name)
    if not query.fetchone():
        row = db.new_row('forms')
        row.label = name
        row.name = form.text
        row.allow_multiple = form.allow_multiple
        row.form_type = form.form_type
        row.def_update_time = form.update_time
        row.db_update()

def import_forms(db, forms, names, options):
    if options.format == 'py':
        from cocklebur.form_ui.pyload import pyload as reader
    else:
        from cocklebur.form_ui.xmlload import xmlload as reader
    form_mod_re = re.compile('^([a-zA-Z0-9_]+?)(_[0-9]+)?(\.[^.]*)$')
    if names:
        names = set(names)
    name_versions = {}
    for name in os.listdir(options.importdir):
        fn = os.path.join(options.importdir, name)
        try:
            ff = FF(name, fn)
        except FFError, e:
            print >> sys.stderr, e
            continue
        if not names or ff.name in names or name in names:
            name_versions.setdefault(ff.name, []).append(ff)
    for versions in name_versions.itervalues():
        versions.sort()
        if not options.historical:
            del versions[:-1]
        for ff in versions:
            f = open(ff.fn)
            try:
                try:
                    form = reader(f)
                finally:
                    f.close()
            except Exception, e:
                print >> sys.stderr, '%s: %s' % (ff.fn, e)
                continue
            version = forms.save(form, ff.name)
            update_forms(db, ff.name, form)
            if options.verbose:
                print 'imported %s as %s:%s' % (ff.fn, ff.name, version)
    db.commit()


def main():
    parser = OptionParser(usage='usage: %prog [options] <formname> ...')
    parser.add_option('-H', '--historical', 
                      dest='historical', action='store_true',
                      help='include historical versions')
    parser.add_option('-v', '--verbose', 
                      dest='verbose', action='store_true',
                      help='print status messages to stdout')
    parser.add_option('-D', '--debug', 
                      dest='debug', action='store_true',
                      help='enable debugging output')
    parser.add_option('-C', '--cgi', metavar='DIR',
                      dest='cgidir', default='/usr/www/cgi-bin/collection',
                      help='Collection cgi-bin directory (default %default)')
    parser.add_option('-F', '--format', 
                      dest='format', default='xml',
                      help='form format (xml or py, default %default)')
    group = OptionGroup(parser, 'Actions')
    group.add_option('-i', '--import', 
                      dest='importdir', metavar='DIR',
                      help='import forms from DIR')
    group.add_option('-o', '--export', 
                      dest='exportdir', metavar='DIR',
                      help='export forms to DIR')
    group.add_option('-l', '--list', 
                      dest='list', action='store_true', 
                      help='list forms in library')
    parser.add_option_group(group)
    options, args = parser.parse_args()
    modeopts = options.importdir, options.exportdir, options.list
    modecnt = sum([bool(o) for o in modeopts])
    if not modecnt:
        parser.error('Specify one of --import, --export or --list.')
    elif modecnt > 1:
        parser.error('--import, --export and --list are mutually exclusive.')
    if options.format not in ('xml', 'py'):
        parser.error('--format must be xml or py.')
    sys.path.insert(0, options.cgidir)
    try:
        import config as config
        from cocklebur import dbobj
        from cocklebur.form_ui import formlib
    except ImportError:
        parser.error('import casemgr modules failed, check --cgi argument')
    dbobj.execute_debug(options.debug)
    db = dbobj.get_db(os.path.join(options.cgidir, 'db'), config.dsn)
    forms = formlib.FormLibXMLDB(db, 'form_defs')
    if options.list:
        list_forms(forms, args, options)
    elif options.exportdir:
        export_forms(forms, args, options)
    elif options.importdir:
        import_forms(db, forms, args, options)

if __name__ == '__main__':
    main()
