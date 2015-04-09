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
try:
    import difflib23 as difflib
except ImportError:
    import difflib
from cStringIO import StringIO

from cocklebur.form_ui.xmlsave import xmlsave
from casemgr import globals
from pages import page_common

import config

def form_xml(form):
    f = StringIO()
    xmlsave(f, form)
    return f.getvalue().splitlines()

class PageOps(page_common.PageOpsBase):
    pass

page_process = PageOps().page_process

def page_enter(ctx, from_form, to_form, from_label, to_label):
    from_xml = form_xml(from_form)
    to_xml = form_xml(to_form)
    differ = difflib.HtmlDiff(wrapcolumn=80)
    ctx.locals.difftable = differ.make_table(from_xml, to_xml, 
                                    from_label, to_label, context=True)
    ctx.add_session_vars('difftable')

def page_leave(ctx):
    ctx.del_session_vars('difftable')

def page_display(ctx):
    ctx.run_template('admin_form_diff.html')

