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

import re

bad_re = re.compile(r'[^a-zA-Z0-9]+')

def filename_safe(name):
    """
    Transform a string to make it safe for use as a filename
    """
    fields = []
    for f in bad_re.split(name):
        if f.islower():
            f = f.capitalize()
        fields.append(f)
    return ''.join(fields)

if __name__ == '__main__':
    print filename_safe('IGgLe nog-flib._.pot9')
