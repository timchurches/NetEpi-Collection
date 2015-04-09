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

from casemgr import globals

from pages import page_common

import config

class PageOps(page_common.PageOpsBase):
    pass

page_process = PageOps().page_process

def page_enter(ctx, rpt):
    ctx.locals.imagefile = rpt.imagefile
    ctx.add_session_vars('imagefile')

def page_leave(ctx):
    imagefile = getattr(ctx.locals, 'imagefile', None)
    if imagefile and not os.path.dirname(imagefile):
        try:
            os.unlink(os.path.join(config.scratchdir, imagefile))
        except OSError:
            pass
        ctx.locals.imagefile = None
    ctx.del_session_vars('imagefile')

def page_display(ctx):
    ctx.run_template('report_image.html')
