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

from casemgr import globals, cached

class NickCache(cached.NotifyCache):
    notification_target = 'nicknames'

    def load(self):
        query = globals.db.query('nicknames')
        nickmap = {}
        for nick, alt in query.fetchcols(('nick', 'alt')):
            nickmap.setdefault(nick, []).append(alt)
        self.nickmap = nickmap

    def get_nicks(self, words):
        self.refresh()
        wordnicks = []
        for word in words:
            wordnicks.append([word] + self.nickmap.get(word, []))
        return wordnicks

get_nicks = NickCache().get_nicks
