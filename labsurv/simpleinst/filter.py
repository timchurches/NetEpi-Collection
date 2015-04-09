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

class _InstanceAsDict:
    def __init__(self, inst):
        self.inst = inst

    def __getitem__(self, a):
        try:
            return getattr(self.inst, a)
        except AttributeError:
            raise KeyError(a)

class Filter:
    def __init__(self, config, pattern, subst, count = 0):
        self.config = _InstanceAsDict(config)
        self.pattern = re.compile(pattern, re.MULTILINE)
        self.subst = subst
        self.count = count

    def filter(self, data):
        return self.pattern.sub(self.subst % self.config, data, self.count)
