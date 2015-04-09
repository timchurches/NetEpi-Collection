#!/usr/bin/env python
#
# This tool checks that all .py and .html files contain the following license
# header text:

"""
    The contents of this file are subject to the HACOS License Version 1.2
    (the "License"); you may not use this file except in compliance with
    the License.  Software distributed under the License is distributed
    on an "AS IS" basis, WITHOUT WARRANTY OF ANY KIND, either express or
    implied. See the LICENSE file for the specific language governing
    rights and limitations under the License.  The Original Software
    is "NetEpi Collection". The Initial Developer of the Original
    Software is the Health Administration Corporation, incorporated in
    the State of New South Wales, Australia.
    
    Copyright (C) 2004-2011 Health Administration Corporation, Australian
    Government Department of Health and Ageing, and others.
    All Rights Reserved.

    Contributors: See the CONTRIBUTORS file for details of contributions.
"""

import sys
import os
import re

# Check all files with these extensions
check_exts = '.py', '.html', '.js', '.css'
# Additional files to check
extras = [
    'Makefile',
]
# Ignore listed files
ignore = [
    'cocklebur/safehtml.py',            # Object Craft Licence (BSD)
    'cocklebur/hsv.py',
    'app/help/copyright.html',          # Contains the full Licence
    'casemgr/phonetic_encode.py',       # ANUOS LICENCE 1.1
    'app/lang/calendar-en.js',          # LGPL
    'app/calendar.js',                  # LGPL
    'app/calendar.css',                 # LGPL
    'app/wiki.css',                     # Modified BSD
    'casemgr/svnrev.py',                # empty file
    'app/backiframe.html',              # trivial file
]

ignore_dirs = [
    'simpleinst',                       # External pkg, HACOS Licence
    'httpinteract',                     # External pkg, HACOS Licence
    'LiveCD',                           # External pkg, HACOS Licence
    'labsurv',                          # External pkg, HACOS Licence
    'wiki',                             # Trac (modified BSD) licence
    'mod_auth_pgsql-2.0.3-netepi.4101', # External pkg, Apache licence
]

filt_re = re.compile(r'(^(%|#|--|[ \t]+\*)?[ \t]*)|([ \t\r;]+$)', re.MULTILINE)

exit_status = 0

def strip(buf):
    return filt_re.sub('', buf)

def check(filepath, want):
    f = open(filepath)
    try:
        head = f.read(2048)
    finally:
        f.close()
    if want not in strip(head):
        global exit_status
        exit_status = 1
        print filepath


want = strip(__doc__)
for filepath in extras:
    check(filepath, want)
for dirpath, dirnames, filenames in os.walk('.'):
    dirnames[:] = [dirname 
                   for dirname in dirnames 
                   if dirname not in ignore_dirs]
    for filename in filenames:
        for ext in check_exts:
            if filename.endswith(ext):
                break
        else:
            continue
        filepath = os.path.normpath(os.path.join(dirpath, filename))
        if filepath in ignore:
            continue
        check(filepath, want)
sys.exit(exit_status)
