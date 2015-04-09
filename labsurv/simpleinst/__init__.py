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
import simpleinst.defaults
import simpleinst.platform
import simpleinst.config_register
import simpleinst.install_files
import simpleinst.pyinstaller
import simpleinst.utils
from simpleinst.filter import Filter
from simpleinst.utils import secret, getpass, collect, rm_pyc
from simpleinst.usergroup import user_lookup

# Config priority:
#    10. command line
#    20. config.py
#    30. install.py (includes any explicitly set config attributes)
#    40. platform defaults (from simpleinst.platform)
#    50. defaults (from simpleinst.defaults)
# Note that we add these in reverse order, as later, more complex configs
# can depend on earlier ones
config = simpleinst.config_register.Config()
config.source(50, simpleinst.defaults.Defaults())
config.source(40, simpleinst.platform.get_platform())
config.source_attrs(30)
config.source_file(20, 'config')
config.source_cmdline(10)

import os
joinpath = os.path.join
basename = os.path.basename
dirname = os.path.dirname
abspath = os.path.abspath
normpath = os.path.normpath
del os

from py_compile import compile as _py_compile
def py_compile(fn):
    _py_compile(fn, doraise=True)

def make_dirs(*args, **kwargs):
    kwargs['config'] = config
    return simpleinst.utils.make_dirs(*args, **kwargs)

def install(**kwargs):
    return simpleinst.install_files.install(config=config, **kwargs)

def on_install(*args, **kwargs):
    simpleinst.install_files.on_install(config, *args, **kwargs)

def py_installer(name, *args, **kwargs):
    return simpleinst.pyinstaller.py_installer(config, name, *args, **kwargs)

python_bang_path_filter = Filter(config, pattern = '^#!.*',
                                 subst = '#!%(python)s', count = 1)

copy = simpleinst.install_files.copy
