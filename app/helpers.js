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

/*global window Calendar */

var isOldIE = navigator.userAgent.search(/MSIE [56]/) >= 0;

// Monkey patch prehistoric versions of IE
if (!Array.prototype.indexOf) {
    Array.prototype.indexOf = function (obj, start) {
        for (var i = (start || 0); i < this.length; i++) {
            if (this[i] === obj) {
                return i;
            }
        }
        return -1;
    };
}


//////
// Structural helpers

function alertargs() {
    alert(Array.prototype.join.call(arguments, '/'));
}

var debug_status_win;
function debugStatus(msg) {
    if (!debug_status_win) {
        debug_status_win = document.createElement('div');
        debug_status_win.style.position = 'fixed';
        debug_status_win.style.top = '0px';
        debug_status_win.style.right = '0px';
        debug_status_win.style.height = '10ex';
        debug_status_win.style.width = '20em';
        debug_status_win.style.backgroundColor = '#cfc';
        debug_status_win.style.opacity = '0.5';
        document.body.insertBefore(debug_status_win, document.body.firstChild);
    }
    debug_status_win.innerHTML = msg;
}

function forEach(list, fn) {
    if (!list) {
        return;
    }
    if (list.length) {
        for (var i = 0; i < list.length; ++i) {
            fn(list[i]);
        }
    } else {
        fn(list);
    }
}

function distance(x1, y1, x2, y2) 
{
    return Math.sqrt(Math.pow(x1 - x2, 2) + Math.pow(y1 - y2, 2));
}


//////
// Event helpers

function addEvent(o, eventName, handler) {
    if (o.addEventListener) {
        o.addEventListener(eventName, handler, false);
    } else {
        o.attachEvent("on" + eventName, handler);
    }
}

function delEvent(o, eventName, handler) {
    if (o.removeEventListener) {
        o.removeEventListener(eventName, handler, false);
    } else {
        o.detachEvent("on" + eventName, handler);
    }
}

function cancelEvent(ev) {
    if (ev.preventDefault) {
        ev.preventDefault();
    } else {
        ev.returnValue = false;
    }
    if (ev.stopPropagation) {
        ev.stopPropagation();
    } else {
        ev.cancelBubble = true;
    }
    return false;
}

function clickOn(node) {
    if (node.dispatchEvent) {
        var ev = document.createEvent("MouseEvents");
        ev.initMouseEvent('click', true, true, window, 0, 0, 0, 0, 0, 
                            false, false, false, false, 0, null);
        node.dispatchEvent(ev);
    } else {
        node.fireEvent('onclick');
    }
}
    

//////
// DOM helpers

function isChild(node, child) {
    do {
        if (node === child.parentNode) {
            return true;
        }
    } while ((child = child.parentNode));
    return false;
}

/* iterate down the node tree looking for a node that satisfies condition() */
function findChild(node, condition, action) {
    if (condition(node) && action(node)) {
        return true;
    }
    for (var i = 0; i < node.childNodes.length; ++i) {
        if (findChild(node.childNodes[i], condition, action)) {
            return true;
        }
    }
    return false;
}

// insert /next/ after /node/
function appendAfter(next, node) {
    if (node.nextSibling) {
        node.parentNode.insertBefore(next, node.nextSibling);
    } else {
        node.parentNode.appendChild(next);
    }
}

/* iterate back up the tree looking for a parent of /node/ that is of type
 * /tagName/
 */
function parentTag(node, tagName) {
    while (node) {
        if (node.nodeType === 1 && node.tagName.toLowerCase() === tagName) {
            break;
        }
        node = node.parentNode;
    }
    return node;
}

function cancelSelection() {
    if (window.getSelection) {
        var sel = window.getSelection();
        if (sel && !sel.isCollapsed && sel.collapseToStart) {
            sel.collapseToStart();
        }
    } else if (document.selection) {
        document.selection.clear();
    }
}

function viewTopLeft() {
    return {
        left: window.scrollX || document.documentElement.scrollLeft,
        top: window.scrollY || document.documentElement.scrollTop
    };
}

function absNodePos(e)
{
    var o = {x: 0, y: 0};
    do {
        o.x += e.offsetLeft;
        o.y += e.offsetTop;
    }
    while ((e = e.offsetParent));
    return o;
}

// Is the mouse "near" a node?
function mouseIsNear(node, ev) {
    var o = absNodePos(node),
        near = 20,
        left = o.x - near, 
        top = o.y - near,
        right = o.x + node.clientWidth + near, 
        bottom = o.y + node.clientHeight + near,
        viewTop = window.scrollY || document.documentElement.scrollTop,
        viewLeft = window.scrollX || document.documentElement.scrollLeft,
        mouseX = ev.clientX + viewLeft,
        mouseY = ev.clientY + viewTop;
//    debug([viewLeft, ev.clientX, left, mouseX, right].join(' ') + '<br>' +
//          [viewTop, ev.clientY, top, mouseY, bottom].join(' '));
    return (mouseX >= left && mouseX < right &&
            mouseY >= top && mouseY < bottom);
}

// cross platform way to fetch contained text
function getText(node) {
    return node.innerText || node.textContent || '';
}

/* Scroll the window so /element/ is visible.
 * We'd rather use element.scrollIntoView, but it's not always available.
 */
function scrollToElement(e)
{
    var o = absNodePos(e);
    window.scrollTo(o.x, o.y);
}


//////
// CSS/className helpers

/* return whether /element/ is a member of CSS /className/ 
 * NOTE: does not honour the cascade
 */
function elementHasClass(element, className) {
    if (!element.className) {
        return false;
    }
    if (element.className === className) {
        return true;
    }
    return element.className.split(' ').indexOf(className) >= 0;
}

function addClass(element, className) {
    if (element.className) {
        var classes = element.className.split(' ');
        if (classes.indexOf(className) < 0) {
            classes.unshift(className);
            element.className = classes.join(' ');
        }
    } else {
        element.className = className;
    }
}
    
function rmClass(element, className) {
    if (!element.className) {
        return;
    }
    if (element.className === className) {
        element.className = '';
        return;
    }
    var classes = element.className.split(' ');
    var i = classes.indexOf(className);
    if (i >= 0) {
        classes.splice(i, 1);
        element.className = classes.join(' ');
    }
}

// apply a function to all elements with specified /className/
function classApply(root, className, action)
{
    var condition = function (node) {
        return elementHasClass(node, className);
    };
    findChild(root, condition, action);
}


//////
// Cookie helpers

// Create a R/O map view of the document cookies (at document load time)
var cookiemap = null;
function makeCookieMap() {
    cookiemap = {};
    var cookies = document.cookie.split(/\s*;\s*/);
    for (var i = 0; i < cookies.length; ++i) {
        var kv = cookies[i].split('=');
        if (kv.length === 2) {
            cookiemap[kv[0]] = kv[1];
        }
    }
}
makeCookieMap();

// Warning: IE can ignore persistent cookies (cookies with expiry)
function setCookie(name, value) {
    document.cookie = name + '=' + value;
    cookiemap[name] = value;
}


//////
// More complex DOM stuff

function scrollRemember(formName, pageName) {
    var form = document.forms[formName];
    addEvent(form, 'submit', function () {
        var viewTop = window.scrollY || document.documentElement.scrollTop;
        setCookie('scrollInfo', pageName + ',' + viewTop);
        return true;
    });
    addEvent(window, 'load', function () {
        if (cookiemap.scrollInfo) {
            var fields = cookiemap.scrollInfo.split(',');
            if (fields[0] === pageName) {
                window.scrollTo(0, fields[1]);
            }
        }
    });
}

// JS target to pop help in a new window
function pophelp(path, target) {
    var helpurl = path + '#' + target;
    var height = screen.height / 2;
    var width = screen.width / 2;
    if (height < 400) {
        height = 400;
    }
    if (width < 600) {
        width = 600;
    }
    var features = "height=" + height + ",width=" + width +
                ",resizeable=yes,scrollbars=yes,dependent=yes";
    window.open(helpurl, "Help", features).focus();
}

function syntheticSubmit(formName, submitName) {
    var form = document[formName];
    if (!form) {
        return;
    }
    var input = document.createElement('input');
    input.type = 'submit';
    input.value = 'Submit';
    input.style.display = 'none';
    input.name = Array.prototype.slice.call(arguments, 1).join(':');
    form.appendChild(input);
    input.click();
}

// JS anchor target to submit on click
function linksubmit(formName, action)
{
    var submitName = Array.prototype.slice.call(arguments, 1).join(':');
    syntheticSubmit(formName, submitName);
}


// Record how long a form submission takes, store result in a hidden form field
addEvent(window, "load", function () {
    var form;
    for (var i = 0; i < document.forms.length; ++i) {
        if (document.forms[i]['response_time']) {
            form = document.forms[i];
            break;
        }
    }
    if (!form) {
        return;
    }
    addEvent(form, 'submit', function () {
        var now = new Date();
        setCookie('submit_time', now.getTime());
        return true;
    });
    var submit_time = cookiemap['submit_time'];
    if (submit_time) {
        setCookie('submit_time', '');
        var now = new Date();
        var elapsed = (now.getTime() - submit_time) / 1000;
        if (elapsed > 0 && elapsed < 60) {
            form['response_time'].value = elapsed;
        }
    }
});


// Allow rows in a table to be clicked through to view full record
function clicktab(tableName, formName)
{
    var table = document.getElementById(tableName),
        form = document.forms[formName];
    if (!table || !form) {
        return;
    }
    addEvent(table, 'click', function (e) {
        var ev = e || event,
            target = ev.target || ev.srcElement;
        while (target && target !== table) {
            if (target.id) {
                syntheticSubmit(formName, target.id);
                return false;
            }
            target = target.parentNode;
        }
        return true;
    });
}


//////
// Stuff to support the pop-up calendar

function calendar_pop(elem) {
    var date = null,
        showtime = true,
        params = {
            'inputField': elem,
            'showsOtherMonths': true
        };
    var calendar_select = function (cal) {
        var p = cal.params;
        if (p.inputField && cal.dateClicked) {
            p.inputField.value = cal.date.print(p.dateFormat);
        }
        if (cal.dateClicked) {
            cal.callCloseHandler();
        }
    };
    var calendar_close = function (cal) {
        cal.hide();
    };
    if (elem.disabled) {
        return;
    }
    if (elem.attributes.calendarformat) {
        params.dateFormat = elem.attributes.calendarformat.value;
        if (params.dateFormat.indexOf('%H') < 0) {
            showtime = false;
        }
    } else {
        params.dateFormat = '%Y-%m-%d %H:%M';
    }
    if (elem.value) {
        date = Date.parseDate(elem.value, params.dateFormat);
    }
    var cal = new Calendar(0, date, calendar_select, calendar_close);
    cal.params = params;
    cal.showsTime = showtime;
    cal.setRange(1900, 2999);
    cal.setDateFormat(cal.params.dateFormat);
    cal.create();
    cal.showAtElement(elem.parentNode.parentNode.parentNode);
    cal.show();
}

var done_calendar_init = false;

function calendar_init() {
    function calendar_connect(field) {
        if (!field.disabled) {
            // Create a button to pop the calendar and wrap the associated 
            // text field in divs to make space for it - gruesome.
            var frag = document.createDocumentFragment();
            var wrapper = document.createElement('div');
            wrapper.style.position = 'relative';
            if (field.size || field.style.width) {
                wrapper.style.width = (field.clientWidth + 
                                       2 * field.clientLeft + 'px');
            }
            frag.appendChild(wrapper);
            var button_wrap = document.createElement('div');
            button_wrap.style.width = '1.5em';
            button_wrap.style.position = 'absolute';
            button_wrap.style.right = '0px';
            wrapper.appendChild(button_wrap);
            var button = document.createElement('input');
            button.name = field.name + 'calendar';
            button.type = 'button';
            button.value = '..';
            button.style.width = '100%';
            button_wrap.appendChild(button);
            var field_clone = field.cloneNode(true);
            field_clone.style.width = '100%';
            var field_wrap = document.createElement('div');
            field_wrap.style.marginRight = '1.5em';
            field_wrap.style.paddingRight = '4px';
            field_wrap.style.width = 'auto';
            field_wrap.appendChild(field_clone);
            wrapper.appendChild(field_wrap);
            field.parentNode.replaceChild(frag, field);
            addEvent(button, "click", function () {
                calendar_pop(field_clone);
            });
        }
    }
    if (Calendar && !done_calendar_init) {
        var i, il, cal_inputs = [];
        for (i = 0, il = document.forms.length; i < il; ++i) {
            var form = document.forms[i];
            for (var j = 0, jl = form.length; j < jl; ++j) {
                var input = form[j];
                if (input.attributes.calendarformat) {
                    cal_inputs.push(input);
                }
            }
        }
        for (i = 0, il = cal_inputs.length; i < il; ++i) {
            calendar_connect(cal_inputs[i]);
        }
        done_calendar_init = true;
    }
}

addEvent(window, "load", calendar_init);

function enterEvent(callback) {
    function entersub(e) {
        var ev = e || event,
            target = ev.target || ev.srcElement,
            code = ev.keyCode || ev.which;
//      if (code == 13) 
//          alertargs(target.nodeName,target.type,inp);
        /* ignoring select-one ENTER events is undesirable, but FF generates
         * two of these, and we can't distinguish between them */
        if (code === 13 && !ev.shiftKey && target.type !== 'submit' && 
                target.type !== 'textarea' && target.type !== 'select-one') {
            callback(target);
            if (ev.preventDefault) {
                ev.preventDefault();
            } else {
                ev.returnValue = false;
            }
            return false;
        }
    }
    addEvent(document.body, 'keypress', entersub);
    return entersub;
}

/* Modern browsers typically synthesize a click on the next "submit" input when
 * the user presses <enter> in a field. This is often undesireable in complex
 * applications. This function attempts to intercept the <enter> key event and
 * turn it into a click on a submit button of our choosing */
function enterSubmit(form_name, input_name) {
    function entersub(target) {
        var inp = document.forms[form_name][input_name];
        if (!inp) {
            return;
        }
        if (inp.length) {
            inp = inp[0];
        }
        if (inp) {
            inp.focus();
        }
        if (target.attributes.entersubmit) {
            inp.click();
        }
    }
    enterEvent(entersub);
}

/* When the user hits <enter> in a text field within a tbody, find the "submit"
 * button within the body and click it */
function enterBodySubmit(form_name) {
    var issubmit = function (n) {
        return (n.tagName === 'INPUT' && n.type.toLowerCase() === 'submit');
    };
    var form = document.forms[form_name];
    if (form) {
        enterEvent(function (target) {
            var body = parentTag(target, 'tbody');
            if (!body) {
                return;
            }
            findChild(body, issubmit, function (submit) {
                submit.click();
                return true;
            });
        });
    }
}

/* Text input showing disappearing prompt within text area */
function inputHint(fieldId, inputPrompt)
{
    addEvent(window, 'load', function () {
        var node = document.getElementById(fieldId);
        if (!node) {
            return;
        }
        var hint = document.createElement('div');
        hint.style.position = 'absolute';
        hint.style.overflow = 'hidden';
        hint.style.whiteSpace = 'nowrap';
        hint.className = 'input-hint';
        hint.innerHTML = inputPrompt;
        var setPosition = function () {
            var o = absNodePos(node);
            hint.style.left = o.x + node.clientLeft + 2 + 'px';
            hint.style.top = o.y + 'px';
            hint.style.lineHeight = node.offsetHeight + 'px';
        };
        setPosition();
        node.parentNode.appendChild(hint);
        var state = {focus: false, mouse: false};
        var refresh = function () {
            if (state.mouse || state.focus || node.value) {
                hint.style.display = 'none';
            } else {
                hint.style.display = 'block';
            }
        };
        refresh();
        addEvent(hint, 'mouseover', function () {
            state.mouse = true;
            refresh();
        });
        addEvent(node, 'mouseout', function () {
            state.mouse = false;
            refresh();
        });
        addEvent(node, 'focus', function () {
            state.focus = true;
            refresh();
        });
        addEvent(node, 'blur', function () {
            state.focus = false;
            refresh();
        });
        addEvent(window, 'resize', setPosition);
        enterEvent(function () {
            node.form.submit();
        });
    });
}

function radio_skip(srcname, srcvalue, dstname) {
    var dsts = document.getElementsByName(dstname);
    var srcs = document.getElementsByName(srcname);
    var check = function (ev) {
        var src = ev.target ? ev.target : ev.srcElement;
        var disable = src.value === srcvalue;
        for (var i = 0; i < dsts.length; ++i) {
            dsts[i].disabled = disable;
        }
    };
    for (var i = 0; i < srcs.length; ++i) {
        var src = srcs[i];
        addEvent(src, "change", check);
        if (src.checked && src.value === srcvalue) {
            for (var j = 0; j < dsts.length; ++j) {
                dsts[j].disabled = true;
            }
        }
    }
}

function linkfold(name, initially_closed) {
    var label = document.getElementById('label_' + name);
    var node = document.getElementById('fold_' + name);
    var icon = document.getElementById('icon_' + name);
    if (!label || !node) {
        return;
    }

    var fold_state = function () {
        var folds = cookiemap['folds'] ? cookiemap['folds'].split(',') : [];
        for (var i = 0; i < folds.length; i++) {
            var state = folds[i];
            if (state.substr(0, state.length - 1) === name) {
                return (state.charAt(state.length - 1) === '+');
            }
        }
        return initially_closed;
    };

    var fold_set_state = function (want_state) {
        var folds = cookiemap['folds'] ? cookiemap['folds'].split(',') : [];
        for (var i = 0; i < folds.length; i++) {
            var state = folds[i];
            if (state.substr(0, state.length - 1) === name) {
                if (want_state !== (state.charAt(state.length - 1) === '+')) {
                    folds[i] = name + (want_state ? '+' : '-');
                    setCookie('folds', folds.join(','));
                }
                return;
            }
        }
        folds.unshift(name + (want_state ? '+' : '-'));
        setCookie('folds', folds.join(','));
    };

    var fold_open = function () {
        node.style.display = '';
        if (icon) {
            icon.innerHTML = '-';
        }
        fold_set_state(false);
    };

    var fold_close = function () {
        node.style.display = 'none';
        if (icon) {
            icon.innerHTML = '+';
        }
        fold_set_state(true);
    };
    var fold_toggle = function () {
        if (node.style.display === 'none') {
            fold_open();
        } else {
            fold_close();
        }
    };
    if (icon) {
        icon.style.display = 'block';
        icon.innerHTML = '-';
        icon.style.cursor = 'pointer';
        if (!isChild(label, icon)) {
            addEvent(icon, 'click', fold_toggle);
        }
    }
    addEvent(label, 'click', fold_toggle);
    label.style.cursor = 'pointer';
    if (cookiemap === null) {
        makeCookieMap();
    }
    if (fold_state()) {
        fold_close(node, icon);
    }
}

function droplist(name) {
    var label = document.getElementById('label_' + name);
    var list = document.getElementById('list_' + name);
    var icon = document.getElementById('icon_' + name);

    var showList = function () {
        list.style.display = 'block';
        list.style.left = '0px'; 
        list.style.top = label.offsetHeight + 'px';
        label.style.zIndex = 3000; // IE: makes list.style.zIndex work
        list.style.zIndex = 1000;
        list.setAttribute('tabIndex', -1);
        list.focus();
    };
    var hideList = function () {
        list.style.display = 'none';
        label.style.zIndex = 0;
        list.style.zIndex = 0;
    };
    var listClick = function (e) {
        var ev = e || event,
            target = ev.target || ev.srcElement;
        if (target.id) {
            syntheticSubmit('appform', target.id);
        }
    };
    icon.setAttribute('tabIndex', 0);
    addEvent(icon, 'mousedown', showList);
    addEvent(icon, 'focus', showList);
    addEvent(list, 'blur', hideList);
    addEvent(list, 'click', listClick);
    icon.style.cursor = 'pointer';
    list.style.position = 'absolute';
}


if (isOldIE) {
    addEvent(window, 'load', function () {
        // Expensive workaround for IE's limited :hover support
        var fixNode = function (node) {
            var orig_bg = node.currentStyle.backgroundColor;
            addEvent(node, 'mouseover', function () {
                node.style.backgroundColor = '#fffae7';
            });
            addEvent(node, 'mouseout', function () {
                node.style.backgroundColor = orig_bg;
            });
            node.style.cursor = 'pointer';
        };
        var walkNode = function (node) {
            var nrows, rownum, row, cell, i, l;
            if (node.className.search('clicktab') >= 0) {
                nrows = node.rows.length < 1000 ? node.rows.length : 1000;
                for (rownum = 0; rownum < nrows; ++rownum) {
                    row = node.rows[rownum];
                    if (row.id) {
                        fixNode(row);
                    } else {
                        for (i = 0, l = row.cells.length; i < l; ++i) {
                            cell = row.cells[i];
                            if (cell.id) {
                                fixNode(cell);
                            }
                        }
                    }
                }
                return;
            }
            if (node.className.search('clickable') >= 0) {
                fixNode(node);
            }
            if (node.children.length) {
                for (i = 0, l = node.children.length; i < l; ++i) {
                    walkNode(node.children[i]);
                }
            }
        };
        walkNode(document.body);
    });
}
/*jslint white: true, browser: true, devel: true, sub: true, undef: true, nomen: true, eqeqeq: true, bitwise: true, regexp: true, newcap: true, immed: true */
