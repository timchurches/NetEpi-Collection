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
#   Copyright (C) 2004-2011 Health Administration Corporation and others. 
#   All Rights Reserved.
#
#   Contributors: See the CONTRIBUTORS file for details of contributions.
#
import sys, os
topdir = os.path.normpath(os.path.dirname(__file__))
sys.path.insert(0, topdir)
from simpleinst import *

# The simpleinst "config" object maintains a layered view of configuration
# sources. On attribute access, the layers are searched for the named
# attribute, and the topmost match returned.
#
# The layers are:
#
#    10. command line
#    20. config.py (distibution defaults, local customisation)
#    30. install.py (includes any explicitly set config attributes)
#    40. platform defaults (from simpleinst.platform)
#    50. defaults (from simpleinst.defaults)
#
# We add an import of the cgi_target config.py (run-time config) at priority 15
# so that previous configuration directives are honoured.

# Installer derived configuration (essentially defaults):
config.appname = 'labsurv'
assert config.appname == os.path.basename(config.appname),\
    "appname must not contain pathname components"
config.apptitle = 'NSW Health weekly respiratory virus laboratory surveillance'
config.cgi_target = joinpath(config.cgi_dir, config.appname)
config.html_target = joinpath(config.html_dir, config.appname)
config.tracedb = False

config.install_owner = 'root'
config.session_secret = secret()
config.dsn = '::%s:' % config.appname
config.compile_py = True

# Load any existing run-time config file
config.source_file(15, 'config', config.cgi_target,
                   exclude=['cgi_target', 'html_target'])

config.write_file(joinpath(config.cgi_target, 'config.py'),
                  exclude=[], 
                  owner=config.web_user, 
                  mode=0640)

# Configure install hooks - delete (stale?) pyc files, optionally compile
on_install('*.py', rm_pyc)
if config.compile_py:
    on_install('*.py', py_compile)

appname_filter = Filter(config, pattern=r'{{APPNAME}}',
                            subst=config.appname)

# Sundry static content
install(target = config.html_target, 
        filter = appname_filter,
        base = 'app', files = ['*.css', '*.js', '*.html'])
install(target = joinpath(config.html_target, 'images'), 
        base = 'app/images', files = ['*.jpg', '*.png', '*.ico'])


# Applications
install(target = config.cgi_target, 
        filter = python_bang_path_filter,
        base = 'app', files = ['app.py'], mode = 0755)

# App modules and pages
install(target = config.cgi_target, 
        base = '.', files = ['pages'], 
        include = ['*.py', '*.html'])

# libraries
install(target = config.cgi_target, 
        base = '.', files = ['labsurv'], include='*.py')

print """\
*******************************************************************************
Reminder - if you are using a deployment scheme that utilises a persistent
application, such as mod_fastcgi or mod_python, you will now need to
restart the application (how this is performed depends on the scheme -
if running under apache, reloading it may suffice).
"""
