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
from time import time
from casemgr import globals

class Cached(object):
    """
    Cache a set of objects, periodically reloading.

    Subclasses call the .refresh() method on each access, and implement
    a .load() method, which will be called by .refresh() when the cache
    has expired.
    """
    load_time = 0
    time_to_live = 120

    def refresh(self):
        now = time()
        if self.load_time + self.time_to_live < now:
            self.load()
            self.load_time = now

    def cache_invalidate(self, *a):
        # Force a reload on next refresh
        self.load_time = 0


class NotifyCache(Cached):
    """
    Cache of objects with optional refresh on change notification.

    This elaborates on the Cached class - if a notification event arrives, the
    object is scheduled for refresh on next access (by zeroing the load time).

    If change notifications are available, the cache time-to-live is
    increased ten-fold.

    Note that this class is only suitable for objects cached in the
    application, not objects in the client context.
    """
    notification_target = None

    def __init__(self):
        if (self.notification_target and
            globals.notify.subscribe(self.notification_target, 
                                     self.cache_invalidate)):
            self.time_to_live *= 10
