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

"""
Logic to support editing users

Includes:
    SelfRegister        A new user pre-registering
    DisabledEdit        A disabled user attempting to log in (edit details only)
    Sponsor             Sponsor another user onto the system
    SponsoredRegister   A new user registering via a sponsor key
    SponsorEnable       Sponsor enabling a sponsored user
    EditSelf            A logged-in user editing their own details
    SystemAdmin         An admin adding or editing a user
    RoleAdmin           A role-only admin adding or editing a user
"""


try:
    set
except NameError:
    from sets import Set as set

from mx import DateTime

from cocklebur import dbobj, pageops, utils

from casemgr import globals, credentials, messages, notify, unituser


class ConfirmUserEnable(pageops.Confirm):
    mode = 'enable'
    title = 'You are enabling this account'
    message = 'Have you verified the bona fides of this user?'
    buttons = [
        ('continue', 'No, I have not'),
        ('confirm', 'Yes, I have'),
    ]

    def button_confirm(self, pageops, ctx):
        ctx.locals.ue.confirm_enable()
        self.resume(pageops, ctx)


class UserEditBase:

    admin_edit = False
    edit_username = False
    passwd_setting = False
    passwd_setting_check_old = False
    unregistered = False
    submit_button = 'Save'
    need_key = False
    enabling = False
    view_only = False

    def __init__(self, cred, *load_args):
        self.cred = cred
        self.load(*load_args)
        self.sponsor = None
        if self.user.sponsoring_user_id is not None:
            self.sponsor = unituser.users[self.user.sponsoring_user_id]
        if self.passwd_setting:
            self.pwd = credentials.NewPass()

    def load(self, user_id=None):
        if user_id is not None:
            query = globals.db.query('users')
            query.where('user_id = %s', user_id)
            self.user = query.fetchone()
            if self.user is None:
                raise credentials.CredentialError('User not found')
        else:
            self.user = globals.db.new_row('users')
            self.user.enabled = False

    def lock_remain(self):
        return credentials.timelock_remain_str(self.user)

    def check_details(self):
        return credentials.need_check(self.user)

    def mark_checked(self):
        credentials.mark_checked(self.user)
        globals.db.commit()

    def has_changed(self):
        return self.user.db_has_changed()

    def log(self, desc):
        credentials.user_log(globals.db, self.user.user_id, desc)

    def add_unit(self, unit_id):
        uu = globals.db.new_row('unit_users')
        uu.unit_id = unit_id
        uu.user_id = self.user.user_id
        uu.db_update()

    def validate(self):
        # Check username, fullname and contact details are okay
        self.messages = messages.Messages()
        if self.edit_username:
            try:
                credentials.valid_username(self.user)
            except credentials.CredentialError, e:
                self.messages.msg('err', e)
        try:
            credentials.valid_fullname(self.user)
        except credentials.CredentialError, e:
            self.messages.msg('err', e)
        try:
            credentials.valid_contact(self.user)
        except credentials.CredentialError, e:
            self.messages.msg('err', e)
        # Check password
        if self.passwd_setting and self.pwd.has_new():
            try:
                if self.passwd_setting_check_old:
                    credentials.pwd_check(self.user, self.pwd.old)
                self.pwd.set(self.user)
            except credentials.CredentialError, e:
                self.messages.msg('err', e)
        if not self.user.password and self.user.enabled:
            self.user.enabled = False
            self.messages.msg('err', 'Set a password before enabling this user')

    def save(self):
        self.validate()
        if self.messages.have_errors():
            raise self.messages
        if self.user.username:
            self.user.username = self.user.username.lower()
        if not self.admin_edit:
            self.user.checked_timestamp = DateTime.now()
        desc = self.user.db_desc()
        try:
            self.user.db_update()
        except dbobj.DuplicateKeyError, e:
            raise credentials.UsernameError('Sorry, that user name is already used - pick another')
        self.log(desc)
        self.done()

    def done(self):
        self.messages.msg('info', 'User details updated')


class SelfRegister(UserEditBase):
    
    title = 'Register for an account'
    unregistered = True
    edit_username = True
    submit_button = 'Apply'
    passwd_setting = True
    passwd_setting_check_old = False
    passwd_setting_prompt = '''\
        You must supply a strong password (please see the notes to the right):
    '''

    def log(self, desc):
        credentials.user_log(globals.db, self.user.user_id, 'REGISTER')

    def done(self):
        notify.register_notify(self.user)
        self.messages.msg('info', 
            'Your account registration details have been recorded. An '
            'administrator will contact you in order to verify the information '
            'which you have provided.')


class DisabledEdit(UserEditBase):

    title = 'Account not activated. You can only review your details.'
    unregistered = True
    

class Sponsor(UserEditBase):
    
    title = 'Enter details of the user you wish to sponsor'
    edit_username = False

    def __init__(self, cred, **user_attrs):
        UserEditBase.__init__(self, cred)
#        self.user.fullname = user_attrs['fullname']
#        self.user.email = user_attrs['email']
        for attr, value in user_attrs.iteritems():
            setattr(self.user, attr, value)
        self.save()

    def key(self):
        import binascii
        return binascii.b2a_hex(utils.secret(128))

    def save(self):
        # canonical e-mail query
        # if email already in user db, resend?
        # what if already a user? what about generic addrs? Might want multiple
        # outstanding invites?
        #self.validate()
        #if self.messages.have_errors():
        #    raise self.messages
        #query = globals.db.query('users')
        #query.where('email = %s', self.user.email)
        #row = query.fetchone()
        #if row is not None:
        #    if row.enabled:
        #        raise credentials.CredentialsError('
        self.user.sponsoring_user_id = self.cred.user.user_id
        self.user.enable_key = self.key()
        UserEditBase.save(self)
        self.add_unit(self.cred.unit.unit_id)

    def done(self):
        self.messages.msg('info', 'An invitation has been sent to %r' % 
                                self.user.email)
#        self.messages.msg('info', 'Key is %s' % self.user.enable_key)


class SponsoredRegister(UserEditBase):

    title = 'Register for an account'
    unregistered = True
    edit_username = True
    submit_button = 'Apply'
    need_key = True
    enable_key = None
    passwd_setting = True
    passwd_setting_check_old = False
    passwd_setting_prompt = '''\
        You must supply a strong password (please see the notes to the right):
    '''

    def __init__(self, cred, enable_key=None):
        self.enable_key = enable_key
        UserEditBase.__init__(self, cred)

    def load(self):
        if self.enable_key:
            query = globals.db.query('users')
            query.where('enable_key = %s', self.enable_key.strip())
            user = query.fetchone()
            if user is None:
                raise credentials.CredentialError('Invalid key')
            self.user = user
            self.need_key = False
        else:
            self.user = globals.db.new_row('users')
            self.user.enabled = False

    def save(self):
        self.user.enable_key = None
        UserEditBase.save(self)

    def done(self):
        notify.register_notify(self.user)
        self.messages.msg('info', 
            'Your account registration details have been recorded. An '
            'administrator will contact you in order to verify the information '
            'which you have provided.')


class SponsorEnable(UserEditBase):

    title = 'Review and verify bona fides of sponsored user'
    enabling = True
    view_only = True
    confirmed = False
    submit_button = 'Verified'

    def confirm_enable(self):
        self.confirmed = True

    def validate(self):
        UserEditBase.validate(self)
        if not self.confirmed:
            raise ConfirmUserEnable
        self.user.enabled = True


class EditSelf(UserEditBase):

    title = 'Edit your account details'
    passwd_setting = True
    passwd_setting_check_old = True
    passwd_setting_prompt = '''\
        The following fields only need to be completed if you wish to
        change your password (please read the password selection notes to
        the right):
    '''

    def __init__(self, cred):
        UserEditBase.__init__(self, cred, cred.user.user_id)

    def done(self):
        if not self.user.privacy:
            self.messages.msg('warn', credentials.privacy_reminder)


class AdminCommon(UserEditBase):

    title = 'Add a new user'
    edit_username = True
    admin_edit = True
    passwd_setting = True
    passwd_setting_check_old = False
    passwd_setting_prompt = '''\
        The following fields only need to be completed if you wish to
        change the user's password (please read the password selection
        notes to the right):
    '''

    def __init__(self, cred, user_id):
        if 'UNITADMIN' not in cred.rights and 'ADMIN' not in cred.rights:
            raise credentials.CredentialError('You are not an administrator')
        UserEditBase.__init__(self, cred, user_id)
        self.was_enabled = self.user.enabled
        self.rights = list(credentials.Rights(self.user.rights))
        if not self.user.is_new():
            self.title = 'Edit details for user %r - %s' % (
                    self.user.username, self.user.fullname)

    def reset_attempts(self):
        credentials.reset_attempts(self.user)
        globals.db.commit()

    def has_changed(self):
        self.user.rights = str(credentials.Rights(self.rights))
        return UserEditBase.has_changed(self)

    def log(self, desc):
        UserEditBase.log(self, desc)
        credentials.admin_log(globals.db, self.cred.user.user_id, desc)

    def validate(self):
        UserEditBase.validate(self)
        if self.messages.have_errors():
            raise self.messages
        if self.user.enabled and not self.was_enabled:
            raise ConfirmUserEnable
        self.user.rights = str(credentials.Rights(self.rights))

    def confirm_enable(self):
        self.was_enabled = True


class SystemAdmin(AdminCommon):

    def delete(self):
        credentials.delete_user(self.user)
        globals.db.commit()

    def undelete(self):
        credentials.undelete_user(self.user)
        globals.db.commit()


class RoleAdmin(AdminCommon):
    
    def save(self):
        is_new = self.user.is_new()
        AdminCommon.save(self)
        if is_new:
            self.add_unit(self.cred.unit.unit_id)
