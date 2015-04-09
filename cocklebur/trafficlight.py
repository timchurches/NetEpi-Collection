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

from cocklebur import hsv

_colmap = ['#c6d2ff', '#c6ddff', '#c6e8ff', '#c6f3ff', '#c6ffff', 
           '#c6fff3', '#c6ffe8', '#c6ffdd', '#c6ffd2', '#c6ffc6', 
           '#d2ffc6', '#ddffc6', '#e8ffc6', '#f3ffc6', '#ffffc6', 
           '#fff3c6', '#ffe8c6', '#ffddc6', '#ffd2c6', '#ffc6c6']
 

def web_trafficlight(n, limit=100):
    scale = len(_colmap) / float(limit)
    return _colmap[max(0, min(int(n * scale), len(_colmap) - 1))]

def make_n_colors(n, sat=0.3):
    return ['#%02x%02x%02x' % hsv.HSVtoRGB(float(i) / n, sat, 255.0) 
            for i in range(n)]
