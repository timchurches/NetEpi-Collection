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
from cocklebur import dbobj, datetime
from cocklebur.pt import SelectPT
from casemgr import globals
from pages import page_common
import config

class PageOps(page_common.PageOpsBase):
    def unsaved_check(self, ctx):
        if ctx.locals.group_edit.db_has_changed():
            raise page_common.ConfirmSave
        if ctx.locals.bulletin.db_has_changed():
            raise page_common.ConfirmSave

    def commit(self, ctx):
        def normalise_date(msg, dt):
            if dt is not None:
                try:
                    return str(datetime.mx_parse_datetime(dt))
                except datetime.Error, e:
                    raise page_common.PageError('%s: "%s": %s' % (msg, dt, e))
        bull = ctx.locals.bulletin
        bull.post_date = normalise_date('Post date', bull.post_date)
        bull.expiry_date = normalise_date('Expiry date', bull.expiry_date)
        ctx.admin_log(bull.db_desc())
        bull.db_update()
        ctx.locals.group_edit.set_key(bull.bulletin_id)
        ctx.admin_log(ctx.locals.group_edit.db_desc())
        ctx.locals.group_edit.db_update()
        globals.db.commit()
        ctx.add_message('Updated bulletin %r' % bull.title)

    def revert(self, ctx):
        ctx.locals.group_edit.db_revert()
        ctx.locals.bulletin.db_revert()

    def do_update(self, ctx, ignore):
        self.commit(ctx)
        ctx.pop_page()

    def do_delete(self, ctx, ignore):
        if not ctx.locals.bulletin.is_new():
            if not self.confirmed:
                raise page_common.ConfirmDelete
            ctx.locals.bulletin.db_delete()
            globals.db.commit()
        ctx.add_message('Deleted bulletin %r' % ctx.locals.bulletin.title)
        ctx.pop_page()

    def do_group_edit(self, ctx, op, *args):
        ctx.locals.group_edit.do(op, *args)

    def do_wikiedit(self, ctx, field):
        prompt = {
            'detail': 'Detail',
        }[field]
        ctx.push_page('admin_wikiedit', ctx.locals.bulletin, field, prompt,
                      'Bulletin ' + ctx.locals.bulletin.title, 
                      'admin-bulletins')
    

pageops = PageOps()


def page_enter(ctx, bulletin_id):
    if bulletin_id is None:
        ctx.locals.bulletin = globals.db.new_row('bulletins')
    else:
        query = globals.db.query('bulletins')
        query.where('bulletin_id = %s', bulletin_id)
        ctx.locals.bulletin = query.fetchone()
    ctx.locals.group_pt = globals.db.ptset('group_bulletins', 'bulletin_id', 
                                           'group_id', bulletin_id)
    ctx.locals.group_pt.get_slave_cache().preload_all()
    ctx.locals.group_edit = SelectPT(ctx.locals.group_pt, 'group_name')
    ctx.add_session_vars('bulletin', 'group_pt', 'group_edit')

def page_leave(ctx):
    ctx.del_session_vars('bulletin', 'group_pt', 'group_edit')

def page_display(ctx):
    ctx.run_template('admin_bulletin.html')

def page_process(ctx):
    if pageops.page_process(ctx):
        return
