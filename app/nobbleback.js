/*
 *  The contents of this file are subject to the HACOS License Version 1.2
 *  (the "License"); you may not use this file except in compliance with
 *  the License.  Software distributed under the License is distributed
 *  on an "AS IS" basis, WITHOUT WARRANTY OF ANY KIND, either express or
 *  implied. See the LICENSE file for the specific language governing
 *  rights and limitations under the License.  The Original Software
 *  is "NetEpi Collection". The Initial Developer of the Original
 *  Software is the Health Administration Corporation, incorporated in
 *  the State of New South Wales, Australia.
 *  
 *  Copyright (C) 2004-2011 Health Administration Corporation, Australian
 *  Government Department of Health and Ageing, and others.
 *  All Rights Reserved.
 *
 *  Contributors: See the CONTRIBUTORS file for details of contributions.
 */
_nbb_debug = false;

/* Nobble Back Button via a hidden iframe */
function _nbb_clickBack(win) {
//    alert('intercepted back click ' + win.document.title);
    if (_nbb_debug) alert('synth << Back click');
    for (var i = 0; i < win.document.forms.length; ++i) {
        var back = win.document.forms[i]['back'];
        if (back) {
            if (back.length)
                back = back[0];
            back.click();
            return true;
        }
    }
    return false;
}

function _nbb_frame_redir (frame) {
//    alert('_nbb_frame_redir frame ' + frame);
    frame._nbb_redir = function () {
        var t = (new Date()).getTime();
        //var e = window.parent.backiFrame;
        //e.src = e.src + '?t=' + t;
        frame.location = frame.location + '?t=' + t;
        if (_nbb_debug) alert('frame redir ' + frame.parent._nbb_window_loaded);
    }
    // Firefox doesn't update history if redirect is done immediately
    frame.setTimeout("_nbb_redir()", 1);
}

function _nbb_frame_load (frame) {
    var win = frame.parent;
    var loc = frame.location;
    var query = loc.search;
    if (!frame || !win)
        alert('oops ' + frame + win);
    if (query.charAt(0) != '?') {
        win._nbb_frame_loaded = true;
        if (win._nbb_frame_redirected) {
            if (_nbb_debug) alert('frame load (back)');
            if (!_nbb_clickBack(win))
                _nbb_frame_redir(frame);
        } else if (win._nbb_window_loaded) {
            if (_nbb_debug) alert('frame load');
            _nbb_frame_redir(frame);
        }
    } else {
        if (_nbb_debug) alert('frame load (setting redirected)');
        win._nbb_frame_redirected = true;
    }
}

function _nbb_window_load() {
    if (_nbb_debug) alert('window load ' + window._nbb_window_loaded);
    window._nbb_window_loaded = true;
    window.backiFrame = document.getElementById("bif");
    if (!window.backiFrame)
        alert('window.backiFrame is null');
    if (window._nbb_frame_loaded)
        _nbb_frame_redir(frames["bif"]);
}

_nbb_frame_redirected = false;
_nbb_window_loaded = false;
_nbb_frame_loaded = false;
if (window.addEventListener)
    window.addEventListener("load", _nbb_window_load, false);
else
    window.attachEvent("onload", _nbb_window_load);
