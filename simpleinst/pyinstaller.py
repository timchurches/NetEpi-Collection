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
"""
Import and run a user-defined python installer
"""

import os
import imp

def py_installer(config, name, *args, **kwargs):
    print 'executing installer', name
    path = os.path.join(config.base_dir, name)
    gbals = {
        '__name__': '__install__',
        'config': config,
        'args': args,
        'kwargs': kwargs
    }
    return execfile(path, gbals)

