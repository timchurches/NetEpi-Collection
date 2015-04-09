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
from cocklebur import dbobj, pt
from casemgr import globals, credentials, tasks
from pages import page_common

import config

class ConfirmDelete(page_common.ConfirmDelete):
    title = 'You are deleting this task queue'


class PageOps(page_common.PageOpsBase):
    def unsaved_check(self, ctx):
        if ctx.locals.unit_pt_search.db_has_changed():
            raise page_common.ConfirmSave
        if ctx.locals.user_pt_search.db_has_changed():
            raise page_common.ConfirmSave
        if ctx.locals.queue.db_has_changed():
            raise page_common.ConfirmSave

    def commit(self, ctx):
        queue_updated = ctx.locals.queue.db_has_changed()
        ctx.admin_log(ctx.locals.queue.db_desc())
        ctx.locals.queue.db_update()
        ctx.locals.unit_pt_search.set_key(ctx.locals.queue.queue_id)
        ctx.admin_log(ctx.locals.unit_pt_search.db_desc())
        ctx.locals.unit_pt_search.db_update()
        ctx.locals.user_pt_search.set_key(ctx.locals.queue.queue_id)
        ctx.admin_log(ctx.locals.user_pt_search.db_desc())
        ctx.locals.user_pt_search.db_update()
        globals.db.commit()
        if queue_updated:
            globals.notify.notify('workqueues', ctx.locals.queue.queue_id)
        ctx.add_message('Updated queue %r' % ctx.locals.queue.name)

    def revert(self, ctx):
        ctx.locals.unit_pt_search.db_revert()
        ctx.locals.user_pt_search.db_revert()
        ctx.locals.queue.db_revert()

    def do_update(self, ctx, ignore):
        ctx.locals.unit_pt_search.clear_search_result()
        ctx.locals.user_pt_search.clear_search_result()
        self.commit(ctx)
        ctx.pop_page()

    def do_delete(self, ctx, ignore):
        if ctx.locals.queue.queue_id:
            if ctx.locals.queue_stats.active:
                raise page_common.PageError('workqueue %r cannot be deleted as it has outstanding tasks' % ctx.locals.queue.name)
            if not self.confirmed:
                raise ConfirmDelete(message='Deleting this task queue will irreversably delete %d completed task records' % ctx.locals.queue_stats.completed)
            else:
                tasks.delete_queue(ctx.locals.queue.queue_id)
                globals.db.commit()
                globals.notify.notify('workqueues', ctx.locals.queue.queue_id)
        ctx.add_message('Deleted queue %r' % ctx.locals.queue.name)
        ctx.pop_page()

    def do_unit_pt_search(self, ctx, op, *args):
        ctx.locals.unit_pt_search.do(op, *args)

    def do_user_pt_search(self, ctx, op, *args):
        ctx.locals.user_pt_search.do(op, *args)

pageops = PageOps()


def page_enter(ctx, queue_id):
    if queue_id is None:
        ctx.locals.queue = globals.db.new_row('workqueues')
        ctx.locals.queue_stats = None
    else:
        query = globals.db.query('workqueues')
        query.where('queue_id = %s', queue_id)
        ctx.locals.queue = query.fetchone()
        ctx.locals.queue_stats = tasks.QueueStats(ctx.locals.queue.queue_id)
    queue_units = globals.db.ptset('workqueue_members', 'queue_id', 
                                   'unit_id', queue_id, 'user_id is null')
    ctx.locals.unit_pt_search = pt.SearchPT(queue_units, 'name', 
                                            name='unit_pt_search',
                                            filter='enabled')
    queue_users = globals.db.ptset('workqueue_members', 'queue_id', 
                                   'user_id', queue_id, 'unit_id is null')
    ctx.locals.user_pt_search = pt.SearchPT(queue_users, 'fullname', 
                                            name='user_pt_search',
                                            filter='enabled')
    ctx.add_session_vars('queue', 'queue_stats', 'unit_pt_search', 'user_pt_search')

def page_leave(ctx):
    ctx.del_session_vars('queue', 'queue_stats', 'unit_pt_search', 'user_pt_search')

def page_display(ctx):
    ctx.run_template('admin_queue.html')

def page_process(ctx):
    pageops.page_process(ctx)
