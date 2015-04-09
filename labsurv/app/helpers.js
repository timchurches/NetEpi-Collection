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
 *  Copyright (C) 2004-2011 Health Administration Corporation and others. 
 *  All Rights Reserved.
 *
 *  Contributors: See the CONTRIBUTORS file for details of contributions.
 */

function addEvent (o, eventName, handler) {
    if (o.addEventListener)
        o.addEventListener(eventName, handler, false);
    else
        o.attachEvent("on" + eventName, handler);
}

/* If the current input is null, set it's value from the row before 
 * if possible.
 */
function from_prev(input)
{
    if (input.value) return;
    var td = input.parentNode;
    if (td.cellIndex === undefined) return;
    var tr = td.parentNode;
    if (tr.sectionRowIndex === undefined || tr.sectionRowIndex < 1) return;
    var section = tr.parentNode;
    var prev_tr = section.rows[tr.sectionRowIndex-1];
    if (prev_tr === undefined) return;
    var prev_td = prev_tr.cells[td.cellIndex];
    var prev_input = prev_td.firstChild;
    if (!prev_input.value) return;
    input.value = prev_input.value;
}

function evalJSONRequest(req) {
    return eval("(" + req.responseText + ")");
}
    
function gotPostcode(input, req)
{
    if (input.value) return;
    input.value = evalJSONRequest(req);
}


function asyncReadyClosure (req, ctx, successCallback) 
{
    var nullFn = function () {};

    return function () {
        if (req.readyState == 4) {
            var status = req.status;
            req.onreadystatechange = nullFn;
            if (status == 200 || status == 304)
                successCallback(ctx, req);
        }
    }
}

function getXMLHttpRequest()
{
    return window.XMLHttpRequest
        ? new XMLHttpRequest()
        : new ActiveXObject("MSXML2.XMLHTTP.3.0");
}

function lookup_postcode(input)
{
    if (input.value) return;
    var td = input.parentNode;
    if (td.cellIndex === undefined || td.cellIndex < 1) return;
    var tr = td.parentNode;
    var prev_td = tr.cells[td.cellIndex - 1];
    if (prev_td === undefined) return;
    var prev_input = prev_td.firstChild;
    if (!prev_input.value) return;
    var url = input.form.action;
    var req = getXMLHttpRequest();
    req.open('POST', url, true);
    req.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
    req.onreadystatechange = asyncReadyClosure(req, input, gotPostcode);
    req.send('lookup_suburb=' + prev_input.value);
}

/* Modern browsers typically synthesize a click on the next "submit" input when
 * the user presses <enter> in a field. This is often undesireable in complex
 * applications. This function attempts to intercept the <enter> key event and
 * turn it into a click on a submit button of our choosing */
function enterSubmit(form_name, input_name) {
    function entersub(event) {
        if (!event) event = window.event;
        var inp = document.forms[form_name][input_name];
        if (inp.length) inp = inp[0];
        if (event && inp) {
            var target = event.target ? event.target : event.srcElement;
            var code = event.keyCode ? event.keyCode : event.which;
//            if (code == 13) 
//                alertargs(target.nodeName,target.type,inp);
            if (code == 13 && !event.shiftKey 
                    && target.type != 'submit' 
                    && target.type != 'textarea' 
                    && target.type != 'select-one') {
                inp.focus();
//                inp.click();
                if (event.preventDefault)
                    event.preventDefault();
                else
                    event.returnValue = false;
                return false;
            }
        }
        return true;
    }
    addEvent(document.body, 'keypress', entersub);
}

/* JS target to pop help in a new window
 */
function pophelp (path, target) {
    var helpurl = path + '#' + target;
    var height = screen.height / 2;
    var width = screen.width / 2;
    if (height < 400) height = 400;
    if (width < 600) width = 600;
    var features = "height=" + height + ",width=" + width +
                ",resizeable=yes,scrollbars=yes,dependent=yes";
    var w = window.open(helpurl, "Help", features);
    w.focus();
}
