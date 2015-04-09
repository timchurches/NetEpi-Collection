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
import random

def commalist(fields, conjunction='or'):
    """
    Return the iterable /fields/ as a comma separated list, with the
    last elements joined by "and/or" if appropriate.
    """
    if not fields:
        return 'n/a'
    fields = [str(f) for f in fields]
    if len(fields) == 1:
        return fields[0]
    return '%s %s %s' % (', '.join(fields[:-1]), conjunction, fields[-1])


comma_re = re.compile('\s*,\s*')
def commasplit(buf):
    return comma_re.split(buf.strip())


safeprint_map = []
for i in range(0, 256):
    if 32 <= i < 127:
        safeprint_map.append(chr(i))
    else:
        safeprint_map.append('?')
safeprint_map = ''.join(safeprint_map)


def safeprint(s):
    return s.translate(safeprint_map)


def randfn(base, ext):
    chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    noise = ''.join([random.choice(chars) for i in range(8)])
    return '%s%s.%s' % (base, noise, ext)


def nssetattr(ns, attr, value):
    names = attr.split('.')
    for name in names[:-1]:
        ns = getattr(ns, name)
    setattr(ns, names[-1], value)


def nsgetattr(ns, attr):
    for name in attr.split('.'):
        ns = getattr(ns, name)
    return ns


def secret(nbits=256):
    fd = os.open('/dev/urandom', os.O_RDONLY)
    try:
        return os.read(fd, nbits / 8)
    finally:
        os.close(fd)

#addr_re = re.compile(r'^\s*([a-z0-9._%+-]+)@((?:[a-z0-9-])+(?:\.(?:[a-z0-9-])+)+)\s*$', re.I)

rfc822_comment_re = re.compile(r'"[^"]*"|\([^)]*\)')
rfc822_user_part = r'([a-z0-9._%+-]+)'
rfc822_domain_part = r'((?:[a-z0-9-])+(?:\.(?:[a-z0-9-])+)+)\.?'
rfc822_user_at_domain = rfc822_user_part + '@' + rfc822_domain_part
rfc822_delim_addr = r'^[^<>]*<' + rfc822_user_at_domain + r'>[^<>]*$'
rfc822_delim_addr_re = re.compile(rfc822_delim_addr, re.I)
rfc822_bare_addr = r'^\s*' + rfc822_user_at_domain + r'\s*$'
rfc822_bare_addr_re = re.compile(rfc822_bare_addr, re.I)

def parse_addr(addr):
    """
    Attempt to parse an RFC822 e-mail address (optionally including
    comments, which are striped). Returns a tuple of (user, domain)
    or raises ValueError.
    """
    match = rfc822_delim_addr_re.match(addr)
    if match:
        return match.group(1).lower(), match.group(2).lower()
    addr_no_comments = ''.join(rfc822_comment_re.split(addr))
    match = rfc822_bare_addr_re.match(addr_no_comments)
    if match:
        return match.group(1).lower(), match.group(2).lower()
    raise ValueError('Invalid e-mail address: %r' % addr)
