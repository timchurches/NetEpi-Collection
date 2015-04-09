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
The "credentials" object combines user authentication, access rights,
preferences and logging functional (yes, it's grown somewhat beyond what it's
name suggests).

Note that we defer importing "globals" until it's needed, as parts of this code
are used by the initial installer, and globals is not valid in that context.
"""

# Standard Python Libs
import re
try:
    set
except NameError:
    from sets import Set as set

# 3rd Party
from mx import DateTime

# Application
import config
import notify
from cocklebur import dbobj, utils
from casemgr.preferences import Preferences
from casemgr.rights import Rights
from casemgr.unituser import units, users, null_unit, null_user
from casemgr import pwcrypt

class CredentialError(Exception):
    pass

class DisabledUser(CredentialError):
    def __init__(self, msg, user=None):
        CredentialError.__init__(self, msg)
        self.user = user

class TooManyAttempts(CredentialError):
    pass

class PasswordError(CredentialError):
    pass

class UsernameError(CredentialError):
    pass

class SelectUnit(Exception):
    pass

pwerror = PasswordError('Invalid username or incorrect password')

privacy_reminder = (
    'You have not set your privacy preferences - your contact details will '
    'not be visible to other users of this system. If you wish to share '
    'your contact details with other users, go to Tools->Preferences->Privacy'
)

details_reminder = (
    'You have not checked your contact details in the last %s days. Please '
    'take a moment to review them under Tools->User->Details and make '
    'any corrections necessary.'
) % config.user_check_interval


max_bad_passwords = 5
bad_time_penalty_mins = 5


def pwd_check(user, password):
    if not password:
        raise PasswordError('Please enter your password')
    if not pwcrypt.pwd_check(user.password, password):
        raise PasswordError('Incorrect password')

valid_user_re = re.compile(r'^[a-z][a-z0-9_.-]{2,}$', re.IGNORECASE)

def valid_username(user):
    if not user.username or not valid_user_re.match(user.username):
        raise UsernameError(
            'Usernames must be at least 3 characters long, can only contain '
            'upper or lower case letters, numbers, period, underscores and '
            'hypens, and must start with a letter')

def valid_fullname(user):
    if not user.fullname or len(user.fullname.strip()) < 3:
        raise CredentialError('A full name (greater than 3 characters) must be '
                              'supplied.')

def valid_contact(user):
    for attr in ('phone_home', 'phone_work', 'phone_mobile', 'email'):
        value = getattr(user, attr)
        if value and len(value.strip()) >= 3:
            break
    else:
        raise CredentialError('Either home phone, work phone, mobile phone or '
                              'e-mail address must be supplied')
    if user.email:
        try:
            parts = utils.parse_addr(user.email)
        except ValueError, e:
            raise CredentialError(str(e))
        user.email = '%s@%s' % parts


def get_user_units(db, user_id, cols='unit_id'):
    query = db.query('units', distinct = True)
    query.where('units.enabled = True')
    query.join('LEFT JOIN unit_users USING (unit_id)')
    query.where('unit_users.unit_id = units.unit_id')
    query.where('unit_users.user_id = %s', user_id)
    return query.fetchcols(cols)


def logger(db, table, user_id, event_type, **kwargs):
    from casemgr import globals
    if not event_type:
        return
    log = db.new_row(table)
    log.user_id = user_id
    log.event_type = event_type
    log.remote_addr = globals.remote_host
    for k, v in kwargs.items():
        if v is not None:
            setattr(log, k, v)
    log.db_update(refetch=False)

def user_log(db, user_id, event_type, **kw):
    logger(db, 'user_log', user_id, event_type, **kw)

def admin_log(db, user_id, event_type, **kw):
    logger(db, 'admin_log', user_id, event_type, **kw)

def timelock_remain(user):
    now = DateTime.now()
    five_minutes = DateTime.DateTimeDelta(0,0,bad_time_penalty_mins)
    if (user.bad_attempts >= max_bad_passwords 
        and user.bad_timestamp + five_minutes > now):
        return (user.bad_timestamp + five_minutes) - now

def timelock_remain_str(user):
    remain = timelock_remain(user)
    if remain:
        if remain.hour > 1:
            return '%d hours' % round(remain.hours)
        if remain.minute > 1:
            return '%d minutes' % round(remain.minutes)
        else:
            return '%d seconds' % round(remain.seconds)
    return ''


def delete_user(user):
    if user.user_id is None:
        return                  # New user, not saved
    if user.enabled:
        raise CredentialError('Disable user before deleting')
    if user.deleted:
        raise CredentialError('User is already deleted?')
    user.deleted = True
    isodate = DateTime.now().strftime('%Y-%m-%d %H:%M:%S')
    user.username = '%s DELETED %s' % (user.username, isodate)
    user.db_update()


def undelete_user(user):
    if not user.deleted:
        raise CredentialError('User is not deleted')
    user.deleted = False
    n = user.username.find(' DELETED')
    if n >= 0:
        user.username = user.username[:n]
    user.db_update()


def delete_unit(unit):
    if unit.unit_id is None:
        return                  # New unit, not saved
    if unit.enabled:
        raise CredentialError('Disable unit before deleting')
    query = unit.db().query('users')
    query.join('JOIN unit_users USING (user_id)')
    query.where('unit_users.unit_id = %s', unit.unit_id)
    query.where('not users.deleted')
    users = query.fetchcols('username')
    if users:
        raise CredentialError(config.unit_label + ' is associated with users'
                              ' and cannot be deleted')
    query = unit.db().query('units')
    query.where('unit_id = %s', unit.unit_id)
    try:
        query.delete()
    except dbobj.ConstraintError:
        raise CredentialError(config.unit_label + ' is referenced by another entity')


def group_units(db, group_id):
    """
    Return a list of units that reference the specified group_id
    """
    query = db.query('unit_groups')
    query.where('group_id = %s', group_id)
    return query.fetchcols('unit_id')


class Credentials(object):
    def __init__(self):
        self.clear()

    def __getstate__(self):
        state = self.__dict__.copy()
        state['user_id'] = state.pop('user').user_id
        state['unit_id'] = state.pop('unit').unit_id
        return state

    def __setstate__(self, state):
        state['user'] = users[state.pop('user_id')]
        state['unit'] = units[state.pop('unit_id')]
        self.__dict__.update(state)

    def clear(self):
        self.unit = null_unit
        self.user = null_user
        self._unit_options = None
        self.prefs = None
        self.messages = []

    def _get_rights(self):
        return self.user.rights | self.unit.rights
    rights = property(_get_rights)

    def __nonzero__(self):
        return bool(self.user) and self.prefs is not None

    def admin_log(self, db, event_type):
        admin_log(db, self.user.user_id, event_type)

    def user_log(self, db, event_type, user_id=None, **kw):
        if user_id is None and self.user:
            user_id = self.user.user_id
        user_log(db, user_id, event_type, **kw)

    def set_unit(self, db, unit_id):
        for id, name in self.unit_options:
            if id == unit_id:
                self.unit = units[unit_id]
                return

    def _get_user(self, db, username):
        query = db.query('users')
        query.where('lower(users.username) = %s', username.lower())
        return query.fetchone()

    def authenticate_user(self, db, username, password):
        if not username:
            raise CredentialError('Please enter a user name')
        user = self._get_user(db, username)
        if user is None:
            raise pwerror
        remain = timelock_remain(user)
        if remain:
            raise TooManyAttempts('Too many login attempts with a bad '
                                  'password - please wait %d minutes %d '
                                  'seconds' % (remain.minute, remain.second))
        try:
            pwd_check(user, password)
        except PasswordError:
            user.bad_timestamp = DateTime.now()
            user.bad_attempts += 1
            user.db_update()
            self.user_log(db, 'LOGIN FAILED - INCORRECT PASSWORD', 
                            user_id=user.user_id)
            db.commit()
            if user.bad_attempts == max_bad_passwords:
                notify.too_bad_notify(user)
            raise pwerror
        if not user.enabled:
            self.user_log(db, 'LOGIN FAILED - DISABLED', user_id=user.user_id)
            db.commit()
            raise DisabledUser('User account not activated', user)
        self.unit_options = get_user_units(db, user.user_id, 
                            ('unit_id', 'name'))
        if not self.unit_options:
            self.user_log(db, 'LOGIN FAILED - NO UNIT', user_id=user.user_id)
            db.commit()
            raise DisabledUser('User account not activated (user is not a '
                               'member of any valid units)', user)
        # All okay now - set up user credentials
        self.user = users.add(user)
        if user.bad_attempts:
            user.bad_attempts = 0
        if pwcrypt.need_upgrade(user.password):
            user.password = pwcrypt.new_crypt(password)
            self.user_log(db, 'Password upgrade', user_id=user.user_id)
        user.db_update()
        self.user_log(db, 'LOGIN OK', user_id=user.user_id)
        db.commit()
        if not user.privacy:
            self.messages.append(privacy_reminder)
        if need_check(user):
            self.messages.append(details_reminder)
        self.prefs = Preferences(user.user_id, user.preferences)
        if len(self.unit_options) == 1:
            self.set_unit(db, self.unit_options[0][0])
        else:
            current_unit = self.prefs.get('current_unit')
            if current_unit is not None:
                self.set_unit(db, current_unit)
            if not self.unit:
                raise SelectUnit

    def commit_prefs(self, db, immediate=False):
        if self.prefs is not None:
            self.prefs.commit(db, immediate)

    def auth_override(self, db, username):
        """
        Set up credentials as user without requiring authentication. This
        is used by the command line tools to do things such as exporting
        with a specified user's rights.
        """
        if not username:
            raise CredentialError('Unknown user name')
        user = self._get_user(db, username)
        if user is None:
            raise CredentialError('Unknown user name')
        self.prefs = Preferences(user.user_id, user.preferences)
        self.user = users.add(user)
        self.unit_options = get_user_units(db, user.user_id, 
                                            ('unit_id', 'name'))
        if not self.unit_options:
            raise DisabledUser('User is not a member of any valid units')
        elif len(self.unit_options) == 1:
            self.set_unit(db, self.unit_options[0][0])
        else:
            raise SelectUnit


class NewPass:
    def __init__(self):
        self.old = ''
        self.new_a = ''
        self.new_b = ''

    def has_new(self):
        return self.new_a or self.new_b

    def set(self, user):
        """
        Set a new password on the given user (without checking old password)
        """
        try:
            pwcrypt.strong_pwd(self.new_a)
        except pwcrypt.Error, e:
            raise PasswordError(str(e))
        if self.new_a != self.new_b:
            raise PasswordError("Passwords don't match - try again")
        user.password = pwcrypt.new_crypt(self.new_a)


def reset_attempts(user):
    db = user.db()
    curs = db.cursor()
    try:
        # We use an explicit update, rather than letting the dbrow do it as we
        # may not (yet) want to apply other changes that are in the dbrow.
        dbobj.execute(curs, 'UPDATE users SET bad_attempts = 0'
                            ' WHERE user_id = %s', (user.user_id,))
        user.reset_initial('bad_attempts', 0)
    finally:
        curs.close()


def revoke_invite(db, user_id):
    query = db.query('users')
    query.where('user_id=%s AND username IS NULL', user_id)
    row = query.fetchone()
    if row is None:
        return
    row.db_delete()
    return row.fullname


def mark_checked(user):
    db = user.db()
    curs = db.cursor()
    now = DateTime.now()
    try:
        dbobj.execute(curs, 'UPDATE users'
                            ' SET checked_timestamp = %s'
                            ' WHERE user_id = %s', (now, user.user_id))
        user.reset_initial('checked_timestamp', now)
    finally:
        curs.close()


def need_check(user):
    if not config.user_check_interval or user.is_new():
        return False
    days = DateTime.DateTimeDelta(config.user_check_interval)
    threshold = DateTime.now() - days
    return not user.checked_timestamp or user.checked_timestamp < threshold
