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
import sys
from os.path import dirname, abspath, normpath
from distutils.sysconfig import get_config_var


class Defaults:
    config_source = 'Defaults'
    install_mode = 0444
    install_verbose = False
    install_prefix = ''
    base_dir = normpath(dirname(sys.modules['__main__'].__file__))
    python = abspath(sys.executable)
    bin_dir = get_config_var('BINDIR')
