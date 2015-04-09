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

class TemporaryFile(file):
    def __init__(self, filename, mode = 'wb'):
        self.__filename = filename
        self.__tmpname = filename + '.tmp.%d' % os.getpid()
        file.__init__(self, self.__tmpname, mode)

    def close(self):
        file.close(self)
        os.rename(self.__tmpname, self.__filename)

    def abort(self):
        if not self.closed:
            try:
                file.close(self)
                os.unlink(self.__tmpname)
            except (IOError, OSError):
                pass

    def __del__(self):
        self.abort()
