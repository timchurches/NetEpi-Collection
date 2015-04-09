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

# From inputs subdir, load all python (input) modules
import os, imp

__all__ = []

input_dir = os.path.dirname(__file__)
for filename in os.listdir(input_dir):
    if not filename.startswith('_') and filename.endswith('.py'):
        modname = filename[:-3]
        file, path, desc = imp.find_module(modname, [input_dir])
        try:
            module = imp.load_module(__name__ + '.' + modname, file, path, desc)
        finally:
            file.close()
        ns = globals()
        for name, sym in vars(module).items():
            if hasattr(sym, 'type_name'):
                ns[name] = sym
                __all__.append(name)
