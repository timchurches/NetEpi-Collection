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
from cocklebur.form_ui.common import *

def pyload(f):
    l = {}
    try:
        exec f in l
    except Exception:
        e_type, e_value, e_tb = sys.exc_info()
        msg = '%s: %s' % (e_type.__name__, e_value)
        raise FormParseError, FormParseError(msg), e_tb
    form = l['form']
    if not form.form_type and 'form_type' in l:
        form.form_type = l['form_type']
    if not form.allow_multiple and 'allow_multiple' in l:
        form.allow_multiple = l['allow_multiple']
    return form
