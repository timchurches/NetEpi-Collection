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

from casemgr import globals, casetags

import config


class PageOps(page_common.PageOpsBase):

    def do_okay(self, ctx, ignore):
        casetags.check_tag(ctx.locals.tag)
        if ctx.locals.tag.is_new():
            ctx.locals.tags.append(ctx.locals.tag.tag)
        ctx.locals.tag.db_update(refetch=False)
        globals.db.commit()
        ctx.msg('info', 'Tag %r updated' % ctx.locals.tag.tag)
        casetags.notify()
        ctx.pop_page()

    def do_delete(self, ctx, ignore):
        if not self.confirmed and not ctx.locals.tag.is_new():
            case_count = casetags.use_count(ctx.locals.tag.tag_id)
            if case_count:
                raise page_common.ConfirmDelete(
                    message='Deleting this tag will remove the tag from '
                            '%s case(s). This can not be undone. Are you sure '
                            'you wish to proceed?' % case_count)
        if ctx.locals.tag.tag_id:
            casetags.delete_tag(ctx.locals.tag.tag_id)
        globals.db.commit()
        ctx.msg('info', 'Tag %r deleted' % ctx.locals.tag.tag)
        casetags.notify()
        ctx.pop_page()


pageops = PageOps()

def page_enter(ctx, tag_id):
    ctx.locals.tag = casetags.edit_tag(tag_id)
    ctx.add_session_vars('tag')

def page_leave(ctx):
    ctx.del_session_vars('tag')

def page_display(ctx):
    ctx.run_template('tagedit.html')

def page_process(ctx):
    pageops.page_process(ctx)

