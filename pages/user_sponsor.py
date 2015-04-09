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

from cocklebur import datetime

from casemgr import globals, user_edit, credentials, unituser, notify

from pages import page_common

import config

class Invite:
    cols = (
        'user_id', 'username', 'fullname', 'email', 'enable_key',
        'creation_timestamp',
    )

    def __init__(self, *args):
        for col, value in zip(self.cols, args):
            setattr(self, col, value)
        self.date = datetime.mx_parse_datetime(self.creation_timestamp)

def load_invites(ctx):
    query = globals.db.query('users', order_by='email')
    query.where('sponsoring_user_id = %s', ctx.locals._credentials.user.user_id)
    query.where('(NOT enabled AND NOT deleted)')
    if config.user_registration_mode == 'invite':
        query.where('username is null')
    ctx.locals.outstanding_invites = []
    ctx.locals.pending_enable = []
    for row in query.fetchcols(Invite.cols):
        invite = Invite(*row)
        if invite.username:
            ctx.locals.pending_enable.append(invite)
        else:
            ctx.locals.outstanding_invites.append(invite)


class RevokeConfirm(page_common.Confirm):
    title = 'Revoke invitation'
    buttons = [
        ('continue', 'No'),
        ('confirm', 'Yes'),
    ]


class PageOps(page_common.PageOpsBase):

    def do_invite(self, ctx, ignore):
        ue = user_edit.Sponsor(ctx.locals._credentials,
                               fullname=ctx.locals.fullname,
                               email=ctx.locals.email)
        ctx.add_messages(ue.messages)
        globals.db.commit()
        notify.register_invite(ctx, ue.user)
        ctx.locals.email = None
        ctx.locals.fullname = None

    def do_enable(self, ctx, user_id):
        if config.user_registration_mode == 'sponsor':
            ue = user_edit.SponsorEnable(ctx.locals._credentials, int(user_id))
            ctx.push_page('useredit', ue)

    def do_resend(self, ctx, user_id):
        query = globals.db.query('users')
        query.where('user_id = %s', int(user_id))
        query.where('username IS NULL')
        user = query.fetchone()
        if user:
            notify.register_invite(ctx, user)

    def do_revoke(self, ctx, user_id):
        if not self.confirmed:
            raise RevokeConfirm(message='Are you sure you want to revoke the invitation for %s?' % unituser.users[int(user_id)].fullname)
        fullname = credentials.revoke_invite(globals.db, int(user_id))
        if fullname:
            globals.db.commit()
            ctx.msg('info', 'Revoked invitation for %s' % fullname)
        else:
            ctx.msg('warn', 'No invitation found')


page_process = PageOps().page_process


def page_enter(ctx):
    ctx.locals.email = None
    ctx.locals.fullname = None
    ctx.add_session_vars('email', 'fullname')


def page_leave(ctx):
    ctx.del_session_vars('email', 'fullname')


def page_display(ctx):
    load_invites(ctx)
    ctx.run_template('user_sponsor.html')

