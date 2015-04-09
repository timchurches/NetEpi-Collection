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

from casemgr import globals, casedupe
from pages import page_common
import config

class PageOps(page_common.PageOpsBase):
    def do_scan(self, ctx, ignore):
        #window = ctx.locals.notification_window
        #if window:
        #    window = window.strip()
        #if window:
        #    window = int(window)
        #else:
        #    window = None
        window = None
        ctx.set_page('dupecases', int(ctx.locals.syndrome_id), window)

pageops = PageOps()

def page_enter(ctx):
    if not ctx.locals.syndromes:
        raise page_common.PageError('No %s' % config.syndrome_label)

def page_display(ctx):
    ctx.run_template('dupecases_config.html')

def page_process(ctx):
    pageops.page_process(ctx)
