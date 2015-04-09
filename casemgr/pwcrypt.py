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

import os
import re
try:
    from hashlib import sha1 as sha
except ImportError:
    from sha import new as sha
import binascii

SALT_LEN = 8

RANDOM_DEV = '/dev/urandom'

PWCHARS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789./'
N_PWCHARS = len(PWCHARS)

def poor_salt():
    salt = ''.join([random.choice(PWCHARS) for i in range(SALT_LEN)])
    return '$S$%s$' % salt


def good_salt():
    fd = os.open(RANDOM_DEV, os.O_RDONLY)
    try:
        data = os.read(fd, 16)
    finally:
        os.close(fd)
    salt = ''.join([PWCHARS[ord(data[i]) % N_PWCHARS]
                    for i in range(SALT_LEN)])
    return '$S$%s$' % salt


if os.path.exists(RANDOM_DEV):
    salt = good_salt
else:
    salt = poor_salt


def crypt(password, salt):
    # We do this ourselves, because platform crypt() implementations vary too
    # much, and we'd like our data to be portable.
    fields = salt.split('$', 3)
    try:
        method, salt = fields[1:3]
        if method != 'S':
            raise ValueError
    except ValueError:
        raise ValueError('Invalid password format')
    hash = binascii.b2a_base64(sha(salt + password).digest())[:-1]
    return '$S$%s$%s' % (salt, hash)


def flawed_pwd_check(crypt_pwd, pwd):
    """
    Old, flawed password checking scheme - two-character salt not saved
    with password, so check requires a search of salt space. This makes a hash
    collision 2704 times more likely.
    """
    import string
    import md5
    for letter1 in string.letters:
         for letter2 in string.letters:
              if crypt_pwd == md5.new(letter1+letter2+pwd).hexdigest():
                   return True
    return False


def need_upgrade(crypt_pwd):
    return '$' not in crypt_pwd


def pwd_check(crypt_pwd, pwd):
    if need_upgrade(crypt_pwd):
        return flawed_pwd_check(crypt_pwd, pwd)
    return crypt(pwd, crypt_pwd) == crypt_pwd


def new_crypt(pwd):
    return crypt(pwd, salt())

class Error(Exception): pass

bad_pwd_msg = (
    'Passwords be at least 8 characters long, and must contain a mix of upper '
    'and lower case letters and digits. They may also contain punctuation. '
    'Upper case letters must not only be at the beginning of the password and'
    'digits must not only be at the end of the password.'
)

def strong_pwd(pwd):
    if not pwd:
        raise Error(bad_pwd_msg)
    upper = re.sub('[^A-Z]', '', pwd)
    lower = re.sub('[^a-z]', '', pwd)
    digits = re.sub('[^0-9]', '', pwd)
    nonleadingupper = re.sub('[^A-Z]', '', pwd[1:])
    nontrailingdigits = re.sub('[^0-9]', '', pwd[:-1])
    if len(pwd) < 8 or not lower or not upper or not digits or not (nonleadingupper or nontrailingdigits):
        raise Error(bad_pwd_msg)
