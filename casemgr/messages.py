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

lvlmap = {
    'error': 'err',
    'err': 'err',
    'warning': 'warn',
    'warn': 'warn',
    'information': 'info',
    'info': 'info',
}

class Messages(Exception):

    def __init__(self):
        self.clear_messages()

    def clear_messages(self):
        self.__have_errors = False
        self.__messages = []

    def msg(self, lvl, msg):
        lvl = lvlmap.get(lvl, 'warn')
        self.__messages.append((lvl, str(msg)))
        if lvl == 'err':
            self.__have_errors = True

    message = msg

    def add_messages(self, msgobj):
        for lvl, msg in msgobj.get_messages():
            self.msg(lvl, msg)

    def have_errors(self):
        return self.__have_errors

    def get_messages(self):
        try:
            return self.__messages
        finally:
            self.clear_messages()


class MessageMixin(object):
    
    def clear_messages(self):
        self.__messages = Messages()

    def add_error(self, msg):
#        import traceback, sys
#        print >> sys.stderr, 'ERR: %s' % msg
#        traceback.print_exc()
        self.__messages.msg('error', msg)

    def add_message(self, msg):
        self.__messages.msg('info', msg)

    def msg(self, lvl, msg):
        self.__messages.msg(lvl, msg)

    def add_messages(self, msgobj):
        self.__messages.add_messages(msgobj)

    def have_errors(self):
        return self.__messages.have_errors()

    def get_messages(self):
        return self.__messages.get_messages()
