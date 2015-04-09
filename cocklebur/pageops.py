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

import sys
import traceback
import csv
from cStringIO import StringIO

class Confirm(Exception):
    mode = None
    title = None
    message = None
    reason_prompt = None
    reason = None
    buttons = []

    def __init__(self, mode=None, **kwargs):
        if mode is not None:
            self.mode = mode
        self.__dict__.update(kwargs)

    def set_action(self, action, args):
        self.action = action
        self.action_args = args

    def button(self, pageops, ctx, button):
        meth = getattr(self, 'button_' + button, None)
        if meth:
            meth(pageops, ctx)

    def resume(self, pageops, ctx):
        try:
            pageops.confirmed = True
            pageops.dispatch(ctx, self.action, self.action_args)
        finally:
            pageops.confirmed = False

    def button_discard(self, pageops, ctx):
        pageops.rollback(ctx)
        self.resume(pageops, ctx)

    def button_continue(self, pageops, ctx):
        ctx.locals.confirm = None

    def button_savefirst(self, pageops, ctx):
        pageops.commit(ctx)
        self.resume(pageops, ctx)

    def button_confirm(self, pageops, ctx):
        self.resume(pageops, ctx)


class ConfirmSave(Confirm):
    mode = 'save'
    title = 'Unsaved changes?'
    message = 'There are unsaved changes on this page'
    buttons = [
        ('discard', 'Discard Changes'),
        ('continue', 'Continue Editing'),
        ('savefirst', 'Save First'),
    ]

class ConfirmDelete(Confirm):
    mode = 'delete'
    message = 'Are you sure you wish to delete this record?'
    buttons = [
        ('continue', 'No, do not delete'),
        ('discard',  'Yes, delete it'),
    ]

class ConfirmUndelete(Confirm):
    mode = 'delete'
    message = 'Are you sure you wish to undelete this record?'
    buttons = [
        ('continue', 'No, do not undelete'),
        ('discard', 'Yes, undelete it'),
    ]

class ConfirmRevert(Confirm):
    mode = 'revert'
    title = 'Undo all changes'
    message = 'Do you really wish to abandon all changes?'
    buttons = [
        ('continue', 'No, keep editing'),
        ('discard', 'Yes, abandon'),
    ]


class ContinueDispatch: pass

class PageOpsBase:
    """
    Albatross page_process helper/dispatcher

    The page_process(ctx) method iterates over fields in the submitted
    form.  The field name is split on the ':' character. If the first
    component of the split field matches a method on this object with
    'do_' prefixed, the method is called with arguments consisting of
    the remaining split components.

    A number of common do_ methods are implemented here:

        do_back

            Check for unsaved changes, call self.rollback and then pop a page

        do_logout   
        
            Log out of the app

        do_home

            go to the "home" page (self.home_page)

        do_confirm
            
            Dispatch actions associated with the "confirm" screen. If in
            "confirm" mode, action names that do not start with "confirm"
            are ignored.

    Sub-classes should override the unsaved_check() method if they
    need to intercept attempts to leave the page. This method should
    raise Confirm(confirm_action) if confirmation is required.  The page
    template should test for "confirm", and display an appropriate dialog
    containing confirm_discard, confirm_continue, and confirm_savefirst
    inputs.

    Actions that need to be confirmed should call check_unsaved_or_confirmed().
    This method will call the unsaved_check() method (potentially raising
    a Confirm exception), but only if the associated action has not
    already been confirmed.

    """
    home_page = 'home'
    debug = False

    def __init__(self, template=None):
        self.confirmed = False
        self.template = template

    def unsaved_check(self, ctx):
        """ 
        Subclasses to overload this and raise Confirm if
        they have unsaved data.
        """
        pass

    def commit(self, ctx):
        """ Subclasses to overload this if they need commit actions """
        pass

    def rollback(self, ctx):
        """ Subclasses to overload this if they need cleanup actions """
        pass

    def check_unsaved_or_confirmed(self, ctx):
        if not self.confirmed:
            self.unsaved_check(ctx)

    def do_logout(self, ctx, ignore):
        self.check_unsaved_or_confirmed(ctx)
        ctx.logout()

    def do_home(self, ctx, ignore):
        self.check_unsaved_or_confirmed(ctx)
        ctx.pop_page(self.home_page)

    def do_back(self, ctx, ignore):
        self.check_unsaved_or_confirmed(ctx)
        self.rollback(ctx)
        ctx.pop_page()

    def do_confirm(self, ctx, button):
        confirm = ctx.locals.confirm
        if confirm is not None:
            confirm.button(self, ctx, button)
            # getattr in case button is "logout", which empties ctx.locals
            if getattr(ctx.locals, 'confirm', None) is confirm:
                ctx.locals.confirm = None

    def dispatch(self, ctx, meth_name, fields):
        assert isinstance(fields, (list, tuple))
        meth = getattr(self, 'do_' + meth_name)
        if self.debug: 
            print >> sys.stderr, 'page_proc meth %s%r' %\
                (meth_name, tuple(fields))
        try:
            return meth(ctx, *fields)
        except Confirm, confirm:
            if self.debug:
                tb = sys.exc_info()[2]
                try:
                    while tb.tb_next:
                        tb = tb.tb_next
                    print >> sys.stderr, 'Confirm from %s, line %s' % (
                        tb.tb_frame.f_code.co_filename, tb.tb_lineno)
                finally:
                    del tb
            if ctx.locals.confirm is not None:
                confirm.set_action(ctx.locals.confirm.action,
                                   ctx.locals.confirm.action_args)
            else:
                confirm.set_action(meth_name, fields)
            ctx.locals.confirm = confirm

    def page_process(self, ctx):
        """
        Attempt to dispatch the request to an appropriate "do_" method. 

        Method arguments can be encoded in the field name, or in the
        field value (the "value" attribute is used as the label for submit
        buttons, so application values have to be encoded in their name).
        """
        if self.debug: 
            print >> sys.stderr, 'fields: %r' % ctx.request.field_names()
        for field_name in ctx.request.field_names():
            # <input type="image"> returns fieldname.x and fieldname.y
            if field_name.endswith('.x'):
                field_name = field_name[:-2]
            elif field_name.endswith('.y'):
                continue
            fields = field_name.split(':')
            meth_name = fields.pop(0)
            if (getattr(ctx.locals, 'confirm', False) 
                and not meth_name.startswith('confirm')):
                # Ignore non-confirm ops if we are confirming.
                continue
            if hasattr(self, 'do_' + meth_name):
                if not fields:
                    # If args not encoded in field name, try the field
                    # value (how revolutionary!)
                    value = ctx.request.field_value(field_name)
                    if type(value) is list:
                        # Browser can return multiple values for a field, but
                        # some might be null
                        fields = filter(None, value)
                    elif value:
                        fields = [value]
                if fields:
                    if self.dispatch(ctx, meth_name, fields)!=ContinueDispatch:
                        return True
        return False


class DownloadBase(object):
    def __init__(self, ctx, file_name, content_type=None):
        self.file_name = file_name
        if content_type is None:
            content_type = 'application/unknown'
        self.content_type = content_type
        ctx.locals.download = self

    def set_headers(self, ctx):
        ctx.set_save_session(False)
        # IE will not download via SSL if caching is disabled. 
        # See: http://support.microsoft.com/?kbid=323308
        ctx.del_header('Cache-Control')
        ctx.del_header('Pragma')
        ctx.set_header('Content-Type', self.content_type)
        ctx.set_header('Content-Disposition', 
                    'attachment; filename="%s"' % self.file_name)


class download(DownloadBase):
    def __init__(self, ctx, file_name, data=None,
                    content_type='application/unknown'):
        DownloadBase.__init__(self, ctx, file_name, content_type)
        self.data = []
        if data:
            self.data.append(data)

    def write(self, data):
        self.data.append(data)

    def send(self, ctx):
        self.set_headers(ctx)
        ctx.send_content(''.join(self.data))


class csv_download(DownloadBase):
    # text/csv is the "correct" MIME type, however this results in a "Save-As"
    # dialog, and users want Excel to open directly, so we use the
    # vendor-specific application/vnd.ms-excel instead, which works everywhere
    # except OS X (where the filename gets mucked up).
    def __init__(self, ctx, rowgen, file_name, 
                 content_type='application/vnd.ms-excel'):
        DownloadBase.__init__(self, ctx, file_name, content_type)
        self.rowgen = rowgen

    def send(self, ctx):
        # Warning - We bypass albatross here, because csv.writer wants a
        # file-like object, and it's a lot of inefficient mucking around to
        # make send_content look like a file.
        self.set_headers(ctx)
        ctx.write_headers()
        csv.writer(sys.stdout).writerows(self.rowgen)
        sys.stdout.flush()


def send_download(ctx):
    download = getattr(ctx.locals, 'download', None)
    if download:
        try:
            download.send(ctx)
        except Exception:
            # HTML body may have been partially emitted by the time an export
            # exception occurs, so we can't render our usual friendly page.
            traceback.print_exc(None, sys.stderr)
        return True
    return False
