#
#   The contents of this file are subject to the HACOS License Version 1.2
#   (the "License"); you may not use this file except in compliance with
#   the License.  Software distributed under the License is distributed
#   on an "AS IS" basis, WITHOUT WARRANTY OF ANY KIND, either express or
#   implied. See the LICENSE file for the specific language governing
#   rights and limitations under the License.  The Original Software
#   is "SimpleInst". The Initial Developer of the Original
#   Software is the Health Administration Corporation, incorporated in
#   the State of New South Wales, Australia.  Copyright (C) 2004 Health
#   Administration Corporation. All Rights Reserved.
#
"""
The standard glob doesn't support the concept of a base dir - something
that we need in this application
"""
import os
import re
import fnmatch

glob_re = re.compile('[*?[]')

def glob(basedir, pattern):
    def has_glob(pattern):
        return glob_re.search(pattern) is not None

    dirs = ['']
    pattern_components = pattern.split(os.path.sep)
    for pc in pattern_components:
        new_dirs = []
        if has_glob(pc):
            for dir in dirs:
                try:
                    files = os.listdir(os.path.join(basedir, dir))
                except OSError:
                    continue
                if not pattern.startswith('.'):
                    files = [f for f in files if not f.startswith('.')]
                new_dirs.extend([os.path.join(dir, f) 
                                 for f in fnmatch.filter(files, pc)])
        else:
            for dir in dirs:
                if os.path.exists(os.path.join(basedir, dir, pc)):
                    new_dirs.append(os.path.join(dir, pc))
        dirs = new_dirs
    if not dirs:
        return [pattern]
    else:
        return dirs
