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
from cocklebur import dbobj, pt, datetime
from casemgr import globals
from casemgr.casestatus import EditSyndromeCaseStates
from casemgr.caseassignment import EditSyndromeCaseAssignment
from pages import page_common
import config

def normalise_date(label, dt):
    if dt is not None:
        try:
            return str(datetime.mx_parse_datetime(dt))
        except datetime.Error, e:
            raise page_common.PageError('%s: %s' % (label, e))

class PageOps(page_common.PageOpsBase):
    def unsaved_check(self, ctx):
        if ctx.locals.pt_search.db_has_changed():
            raise page_common.ConfirmSave
        if ctx.locals.group_edit.db_has_changed():
            raise page_common.ConfirmSave
        if ctx.locals.syndrome.db_has_changed():
            raise page_common.ConfirmSave

    def commit(self, ctx):
        synd = ctx.locals.syndrome
        synd.post_date = normalise_date('Post date', synd.post_date)
        synd.expiry_date = normalise_date('Expiry date', synd.expiry_date)
        ctx.admin_log(synd.db_desc())
        try:
            synd.db_update()
        except dbobj.DuplicateKeyError:
            raise dbobj.DuplicateKeyError('Name is already used - choose another')
        ctx.locals.pt_search.set_key(synd.syndrome_id)
        ctx.admin_log(ctx.locals.pt_search.db_desc())
        ctx.locals.pt_search.db_update()
        ctx.locals.group_edit.set_key(synd.syndrome_id)
        ctx.admin_log(ctx.locals.group_edit.db_desc())
        ctx.locals.group_edit.db_update()
        globals.db.commit()
        ctx.add_message('Updated %s %r' % (config.syndrome_label.lower(), synd.name))
        globals.notify.notify('syndromes')
        globals.notify.notify('syndrome_units')

    def revert(self, ctx):
        ctx.locals.syndrome.db_revert()
        ctx.locals.pt_search.db_revert()
        ctx.locals.group_edit.db_revert()

    def do_update(self, ctx, ignore):
        self.commit(ctx)

    def do_form_search(self, ctx, ignore):
        ctx.locals.pt_search.search('name')

    def do_demog_fields(self, ctx, ignore):
        assert ctx.locals.syndrome.syndrome_id is not None
        ctx.push_page('admin_synd_fields', ctx.locals.syndrome.syndrome_id)

    def do_case_status(self, ctx, ignore):
        assert ctx.locals.syndrome.syndrome_id is not None
        syndcateg = EditSyndromeCaseStates(ctx.locals.syndrome.syndrome_id)
        ctx.push_page('admin_synd_categ', syndcateg)

    def do_case_assignment(self, ctx, ignore):
        assert ctx.locals.syndrome.syndrome_id is not None
        syndcateg = EditSyndromeCaseAssignment(ctx.locals.syndrome.syndrome_id)
        ctx.push_page('admin_synd_categ', syndcateg)

    def do_select(self, ctx, which, op):
        assert op in ('add', 'remove')
        select_pt = getattr(ctx.locals, which)
        meth = getattr(select_pt, op)
        meth()

    def do_pt_search(self, ctx, op, *args):
        ctx.locals.pt_search.do(op, *args)

    def do_group_edit(self, ctx, op, *args):
        ctx.locals.group_edit.do(op, *args)

    def do_wikiedit(self, ctx, field):
        prompt = {
            'description': 'Description',
            'additional_info': 'Additional Information',
        }[field]
        ctx.push_page('admin_wikiedit', ctx.locals.syndrome, field, prompt,
                      '%s %s' % (config.syndrome_label, 
                                 ctx.locals.syndrome.name),
                      'admin-syndromes')

    def do_delete(self, ctx, ignore):
        self.check_unsaved_or_confirmed(ctx)
        if ctx.locals.syndrome.syndrome_id is not None:
            ctx.push_page('admin_synd_drop')

    def do_clear(self, ctx, ignore):
        self.check_unsaved_or_confirmed(ctx)
        if ctx.locals.syndrome.syndrome_id is not None:
            ctx.push_page('admin_synd_clear')


pageops = PageOps()


def page_enter(ctx, syndrome_id):
    if syndrome_id is None:
        ctx.locals.syndrome = globals.db.new_row('syndrome_types',
                                                 priority=3)
    else:
        query = globals.db.query('syndrome_types')
        query.where('syndrome_id = %s', syndrome_id)
        ctx.locals.syndrome = query.fetchone()
    ctx.add_session_vars('syndrome')

    # Syndrome forms
    synd_forms_pt = globals.db.participation_table('syndrome_forms',
                                                   'syndrome_id', 'form_label')
    synd_forms_pt.preload_from_result([ctx.locals.syndrome])
    synd_form_pt = synd_forms_pt[syndrome_id]
    ctx.locals.pt_search = pt.OrderedSearchPT(synd_form_pt, 'label', 
                                              filter='cur_version is not null')
    ctx.add_session_vars('pt_search')

    # Syndrome groups
    synds_groups_pt = globals.db.participation_table('group_syndromes',
                                                     'syndrome_id', 'group_id')
    synds_groups_pt.preload_from_result([ctx.locals.syndrome])
    synds_groups_pt.get_slave_cache().preload_all()
    synd_groups_pt = synds_groups_pt[syndrome_id]
    ctx.locals.group_edit = pt.SelectPT(synd_groups_pt, 'group_name')
    ctx.add_session_vars('group_edit')


def page_leave(ctx):
    ctx.del_session_vars('syndrome', 'search_pt', 'group_edit')


def page_display(ctx):
    if ctx.locals.syndrome.syndrome_id is not None:
        try:
            synd = ctx.locals.syndromes[ctx.locals.syndrome.syndrome_id]
        except LookupError:
            ctx.locals.synd_status = ['Unknown']
        else:
            ctx.locals.synd_status = synd.desc_status()
    else:
        ctx.locals.synd_status = ['New %s' % config.syndrome_label]
    ctx.run_template('admin_syndrome.html')


def page_process(ctx):
    pageops.page_process(ctx)
