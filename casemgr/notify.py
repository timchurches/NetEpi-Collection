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

# Standard libs
import time
import re
import os
import email

# Application modules
from cocklebur import template
from casemgr.sendmail import Sendmail

import config



def load_template(name):
    path = os.path.join(config.cgi_target, 'mail', name)
    f = open(path)
    try:
        return f.read()
    finally:
        f.close()


def send_template(name, o=None, **kw):
    tmpl = load_template(name)
    tmpl = template.expand_template(tmpl, o, **kw)
    sm = email.message_from_string(tmpl, Sendmail)
    sm.send()


def register_notify(user):
    if hasattr(config, 'registration_notify') and config.registration_notify:
        sponsor = None
        if user.sponsoring_user_id:
            import unituser
            sponsor_user = unituser.users[user.sponsoring_user_id]
            sponsor = '%s (%s)' % (sponsor_user.fullname, sponsor_user.username)
        try:
            send_template('registration_notify', o=user, sponsor=sponsor)
        except:
            pass


def exception_notify(body):
    if hasattr(config, 'exception_notify') and config.exception_notify:
        try:
            send_template('exception_notify', exception='\n'.join(body))
        except:
            pass


def too_bad_notify(user):
    if hasattr(config, 'registration_notify') and config.registration_notify:
        try:
            send_template('too_many_attempts', o=user)
        except:
            pass


def register_invite(ctx, user):
    url = '[not available]'
    host = ctx.request.get_param('SERVER_NAME')
    ssl = ctx.request.get_param('HTTPS')
    uri = ctx.request.get_uri()
    if host and uri:
        if ssl:
            protocol = 'https'
        else:
            protocol = 'http'
        url = '%s://%s%s?invite=%s' % (protocol, host, uri, user.enable_key)
    send_template('register_invite', o=user, url=url)
