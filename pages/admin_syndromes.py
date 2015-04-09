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
from casemgr import globals, syndrome, paged_search
from pages import page_common
import config

class PageOps(page_common.PageOpsBase):
    def do_edit(self, ctx, syndrome_id):
        ctx.locals.synd_result.reset()
        ctx.push_page('admin_syndrome', int(syndrome_id))

    def do_add(self, ctx, ignore):
        ctx.locals.synd_result.reset()
        ctx.push_page('admin_syndrome', None)


page_process = PageOps().page_process


def page_enter(ctx, synd_result):
    synd_result.headers = [
        ('priority', 'Prio'),
        ('name', 'Name'),
        (None, config.group_label),
        (None, 'Status'),
    ]
    ctx.locals.synd_result = synd_result
    paged_search.push_pager(ctx, ctx.locals.synd_result)
    ctx.add_session_vars('synd_result')

def page_leave(ctx):
    paged_search.pop_pager(ctx)
    ctx.del_session_vars('synd_result')

def page_display(ctx):
#    try:
#        query = globals.db.query('syndrome_types')
#        ctx.locals.syndromes = query.fetchall()
#    except dbobj.DatabaseError, e:
#        ctx.add_error(e)
    ctx.locals.all_synd = syndrome.syndromes.all()
    groups_pt = globals.db.participation_table('group_syndromes', 
                                               'syndrome_id', 'group_id')
    synd_ids = [pkey[0] for pkey in ctx.locals.synd_result.page_pkeys()]
    groups_pt.preload(synd_ids)
    groups_pt.get_slave_cache().preload_all()
    ctx.locals.groups_pt = groups_pt
    ctx.locals.page = [syndrome.syndromes[id] for id in synd_ids]
    ctx.run_template('admin_syndromes.html')
