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
import sys, os
import pwd

class PlatformBase:
    def __init__(self):
        self.config_source = '%s platform' % self.platform

class RedHatLinux(PlatformBase):
    platform = "RedHat Linux"
    html_dir = '/var/www/html'
    cgi_dir = '/var/www/cgi-bin'
    web_user = 'apache'

    def is_platform(self):
        return sys.platform == 'linux2' \
            and os.path.exists('/etc/redhat-release')

class DebianLinux(PlatformBase):
    platform = "Debian Linux"
    html_dir = '/var/www'
    cgi_dir = '/usr/lib/cgi-bin'
    web_user = 'www-data'

    def is_platform(self):
        return sys.platform == 'linux2' \
            and os.path.exists('/etc/debian_version')

class OSX(PlatformBase):
    platform = "Apple OS X"
    html_dir = '/Library/WebServer/Documents'
    cgi_dir = '/Library/WebServer/CGI-Executables'
    web_user = 'www'

    def is_platform(self):
        if sys.platform != 'darwin':
            return False
        # Leopard returns _www for this:
        self.web_user = pwd.getpwnam('www').pw_name
        return True

def get_platform():
    platforms = []
    for name, var in globals().items():
        if hasattr(var, 'is_platform'):
            platform = var()
            if platform.is_platform():
                platforms.append(platform)
    if not platforms:
        sys.exit('Unrecognised playform')
    if len(platforms) > 1:
        sys.exit('Ambiguous platform detection: %s' % \
                 ', '.join([p.platform for p in platforms]))
    return platforms[0]
