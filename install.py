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
import sys, os
sys.path.insert(0, os.path.normpath(os.path.dirname(__file__)))
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

assert config.appname == os.path.basename(config.appname),\
    "appname must not contain pathname components"

# Installer derived configuration (essentially defaults):
config.cgi_target = joinpath(config.cgi_dir, config.appname)
config.html_target = joinpath(config.html_dir, config.appname)
config.scratchdir = os.path.join(config.html_target, 'scratch')

config.install_owner = 'root'
config.session_secret = secret()
config.registration_notify = ''
config.exception_notify = ''
config.dsn = '::%s:' % config.appname
config.install_logo = ''
config.install_logo_small = ''

# If this is a developer build, update SVN revision:
svnrev = collect('svnversion %s 2> /dev/null' % config.base_dir)
if svnrev and svnrev != 'exported':
    f = open(os.path.join(config.base_dir, 'casemgr', 'svnrev.py'), 'w')
    f.write('__svnrev__ = %r\n' % svnrev)
    f.close()

# Load any existing run-time config file
config.source_file(15, 'config', config.cgi_target,
                   exclude=['cgi_target', 'html_target', 'scratchdir'])

# Write run-time config, excluding installer-specific vars
config_exclude = [
    'base_dir',
    'bin_dir',
    'cgi_dir',
    'compile_py',
    'create_db',
    'html_dir',
    'install_*',
    'platform',
    'python',
    'web_user',
] 

config_owner = '%s:%s' % (config.install_owner, 
                          user_lookup(config.web_user)[1])
config.write_file(joinpath(config.cgi_target, 'config.py'),
                  exclude=config_exclude, 
                  owner=config_owner, 
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
        base = 'app', files = ['*.css', '*.js', '*.html',
                                   'lang/*.js', 'help/*.html'])

images = joinpath(config.html_target, 'images')
image_exclude = []
if config.install_logo:
    image_exclude.append('netepi-bb.png')
    copy(config.install_logo, joinpath(images, 'netepi-bb.png'), mode=0755)
if config.install_logo_small:
    image_exclude.append('netepi.png')
    copy(config.install_logo_small, joinpath(images, 'netepi.png'), mode=0755)
install(target = images, base = 'images', files = ['*.png', '*.ico'],
        exclude = image_exclude)

make_dirs(joinpath(config.html_target, 'scratch'), config.web_user)


# Applications
install(target = config.cgi_target, 
        filter = python_bang_path_filter,
        base = 'app', files = ['app.py', 'menu.py'], mode = 0755)

# Command line tool
cgitarget_filter = Filter(config, pattern=r'{{CGITARGET}}',
                            subst=config.cgi_target)

copy('app/cmdline.py', joinpath(config.bin_dir, 'netepi-' + config.appname),
        filter=[python_bang_path_filter, cgitarget_filter],
        mode = 0755)

# App modules and pages
install(target = config.cgi_target, 
        base = '.', files = ['pages'], 
        include = ['*.py', '*.html'])

# libraries
install(target = config.cgi_target, 
        base = '.', files = ['cocklebur', 'casemgr', 'wiki'], include='*.py')

# e-mail templates
install(target = config.cgi_target, 
        base = '.', files = ['mail'])

# Compile database describer, create form tables if need be
if config.create_db:
    py_installer('tools/compile_db.py')

print """\
*******************************************************************************
Reminder - if you are using a deployment scheme that utilises a persistent
application, such as mod_fastcgi or mod_python, you will now need to
restart the application (how this is performed depends on the scheme -
if running under apache, reloading it may suffice).
"""
