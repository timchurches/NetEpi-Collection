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
import pwd, grp
import os

cache = {}

def user_lookup(name):
    try:
        return cache[name]
    except KeyError:
        if name:
            try:
                user, group = name.split(':')
            except ValueError:
                user, group = name, None
        else:
            name = str(os.geteuid())
        try:
            uid = int(user)
        except ValueError:
            pw_ent = pwd.getpwnam(user)
            uid, gid = pw_ent.pw_uid, pw_ent.pw_gid
        else:
            pw_ent = pwd.getpwuid(uid)
            uid, gid = pw_ent.pw_uid, pw_ent.pw_gid

        if group:
            try:
                gid = int(group)
            except ValueError:
                gid = grp.getgrnam(group).gr_gid
            else:
                gid = grp.getgrgid(gid).gr_gid

        cache[name] = uid, gid
        return uid, gid
