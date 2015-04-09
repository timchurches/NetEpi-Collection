#
#   The contents of this file are subject to the HACOS License Version 1.2
#   (the "License"); you may not use this file except in compliance with
#   the License.  Software distributed under the License is distributed
#   on an "AS IS" basis, WITHOUT WARRANTY OF ANY KIND, either express or
#   implied. See the LICENSE file for the specific language governing
#   rights and limitations under the License.  The Original Software
#   is "SimpleInst". The Initial Developer of the Original
#   Software is the Health Administration Corporation, incorporated in
#   the State of New South Wales, Australia.  Copyright (C) 2004 Health
#   Administration Corporation. All Rights Reserved.
#
import re
import os
import errno
from simpleinst.usergroup import user_lookup

__all__ = 'chown', 'chmod', 'normjoin', 'make_dirs'

def normjoin(*args):
    return os.path.normpath(os.path.join(*args))

def chown(filename, owner):
    if type(owner) in (unicode, str):
        owner = user_lookup(owner)
    os.chown(filename, *owner)

chmod_re = re.compile('^([ugoa]*)([+-=])([rwxs]+)$')
def chmod(filename, mode):
    if type(mode) in (unicode, str):
        if mode.startswith('0'):
            mode = int(mode, 8)
        else:
            num_mode = 0400
            for field in mode.split(','):
                mask = 0
                modes = 0
                pre, mask_str, op, mode_str, post = chmod_re.split(field)
                if mask_str:
                    for m in mask_str:
                        if m is 'u':
                            mask |= 04700
                        elif m is 'g':
                            mask |= 02070
                        elif m is 'o':
                            mask |= 00007
                        elif m is 'a':
                            mask |= 06777
                else:
                    mask |= 06777
                for m in mode_str:
                    if m is 'r':
                        modes |= 00444
                    elif m is 'w':
                        modes |= 00222
                    elif m is 'x':
                        modes |= 00111
                    elif m is 's':
                        modes |= 06000
                if op is '+':
                    num_mode |= modes & mask
                elif op is '=':
                    num_mode = modes & mask
                elif op is '-':
                    num_mode &= ~(modes & mask)
            mode = num_mode
    os.chmod(filename, mode)

def make_dirs(dir, owner=None, config=None):
    if config and config.install_prefix:
        dir = config.install_prefix + dir
    if type(owner) in (unicode, str):
        owner = user_lookup(owner)
    if not os.path.exists(dir):
        par_dir = os.path.dirname(dir)
        make_dirs(par_dir, owner)
        os.mkdir(dir, 0755)
        if owner is not None:
            chown(dir, owner)

def secret(nbits=256):
    import binascii
    f = open('/dev/urandom', 'rb')
    try:
        data = f.read(nbits / 8)
    finally:
        f.close()
    return binascii.b2a_base64(data).rstrip()

def getpass(prompt):
    import getpass
    return getpass.getpass(prompt)

def collect(cmd):
    f = os.popen(cmd, 'r')
    try:
        return ' '.join([l.rstrip() for l in f])
    finally:
        f.close()

def rm_pyc(fn):
    if fn.endswith('.py'):
        try:
            os.unlink(fn + 'c')
        except OSError, (eno, estr):
            if eno != errno.ENOENT:
                raise
        try:
            os.unlink(fn + 'o')
        except OSError, (eno, estr):
            if eno != errno.ENOENT:
                raise
