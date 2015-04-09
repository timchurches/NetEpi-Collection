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

from pages import page_common

from cocklebur import utils
from casemgr import globals, casetags

import config


class PageOps(page_common.PageOpsBase):

    def do_back(self, ctx, ignore):
        utils.nssetattr(ctx.locals, ctx.locals.targetfield, 
                        ' '.join(ctx.locals.tags))
        ctx.pop_page()

    def do_edit(self, ctx, tag_id):
        ctx.push_page('tagedit', tag_id)


pageops = PageOps()

def page_enter(ctx, tagbrowse_title, targetfield=None):
    ctx.locals.tagbrowse_title = tagbrowse_title
    ctx.locals.targetfield = targetfield
    tags = utils.nsgetattr(ctx.locals, ctx.locals.targetfield)
    ctx.locals.tags = list(casetags.tags_from_str(tags))
    ctx.add_session_vars('tagbrowse_title', 'targetfield', 'tags')


def page_leave(ctx):
    ctx.del_session_vars('tagbrowse_title', 'targetfield', 'tags')

def page_display(ctx):
    ctx.run_template('tagbrowse.html')


def page_process(ctx):
    pageops.page_process(ctx)
