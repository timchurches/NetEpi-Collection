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

from casemgr import globals

sharing_tags = ['last', 'private', 'unit', 'public', 'quick']

class Error(globals.Error): pass
class ReportParamError(Error): pass
class ReportParseError(Error): pass
class ReportLoadError(Error): pass

class ImageReport:

    render = 'image'

    def __init__(self, filename):
        self.imagefile = filename


def boolstr(value):
    return str(value).lower() in ('true', 'yes')
