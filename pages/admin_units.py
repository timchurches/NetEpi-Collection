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
from cocklebur import dbobj
from casemgr import globals, paged_search
from pages import page_common
import config

class PageOps(page_common.PageOpsBase):
    def do_add(self, ctx, ignore):
        ctx.locals.unit_result.reset()
        ctx.push_page('admin_unit', None)

    def do_edit(self, ctx, unit_id):
        ctx.locals.unit_result.reset()
        ctx.push_page('admin_unit', int(unit_id))

    def do_select_all(self, ctx, ignore):
        ctx.locals.selected = unit_ids(ctx)

    def do_select_none(self, ctx, ignore):
        ctx.locals.selected = []

    def do_select_group(self, ctx, cmd):
        group_id = int(ctx.locals.select_group_id)
        groups_pt = get_groups_pt(ctx)
        group = groups_pt.get_slave_cache()[group_id]
        for unit_id in ctx.locals.selected:
            unit_id = int(unit_id)
            if cmd == 'del':
                groups_pt[unit_id].remove(group)
            else:
                groups_pt[unit_id].add(group)
        groups_pt.db_update()
        globals.db.commit()

pageops = PageOps()

def unit_ids(ctx):
    return [pkey[0] for pkey in ctx.locals.unit_result.page_pkeys()]

def get_groups_pt(ctx):
    groups_pt = globals.db.participation_table('unit_groups', 
                                               'unit_id', 'group_id')
    groups_pt.preload(unit_ids(ctx))
    groups_pt.get_slave_cache().preload_all()
    return groups_pt

def page_enter(ctx, unit_result):
    unit_result.headers = [
        (None, 'Selected'),
        ('name', 'Name'),
        ('street_address', 'Street Address'),
        ('enabled', 'Enabled'),
        (None, config.group_label),
    ]
    ctx.locals.unit_result = unit_result
    paged_search.push_pager(ctx, ctx.locals.unit_result)
    ctx.locals.selected = []
    ctx.add_session_vars('unit_result', 'selected')
 
def page_leave(ctx):
    paged_search.pop_pager(ctx)
    ctx.del_session_vars('unit_result', 'selected')

def page_display(ctx):
    ctx.locals.groups_pt = get_groups_pt(ctx)
    group_cache = ctx.locals.groups_pt.get_slave_cache()
    ctx.locals.option_groups = group_cache.option_list('group_name')
    ctx.run_template('admin_units.html')

def page_process(ctx):
    pageops.page_process(ctx)
