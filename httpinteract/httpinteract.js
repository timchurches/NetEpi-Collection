//
//   The contents of this file are subject to the HACOS License Version 1.2
//   (the "License"); you may not use this file except in compliance with
//   the License.  Software distributed under the License is distributed
//   on an "AS IS" basis, WITHOUT WARRANTY OF ANY KIND, either express or
//   implied. See the LICENSE file for the specific language governing
//   rights and limitations under the License.  The Original Software
//   is "NetEpi Case Manager". The Initial Developer of the Original
//   Software is the Health Administration Corporation, incorporated in
//   the State of New South Wales, Australia.
//
//   Copyright (C) 2006 Health Administration Corporation.
//   All Rights Reserved.
//
// $Source: /usr/local/cvsroot/NSWDoH/httpinteract/httpinteract.js,v $
// $Id: httpinteract.js,v 1.7 2006/04/21 07:48:46 andrewm Exp $

running = null;
refresh = null;
flasher = null;
results = [];
histCount = 10;
requestCount = 0;
responseCount = 0;
// Logger.maxSize is broken in MochiKit 1.2
// logger.maxSize = 100;
cumTime = 0;
minTime = undefined;
maxTime = undefined;
junk = "X";

var updateCell = function (elem, text, className)
{
    if (typeof(elem) == 'string')
        elem = getElement(elem);
    if (elem && text) {
        if (!elem.firstChild || elem.firstChild.textNode != text)
            replaceChildNodes(elem, text);
        if (elem.className != className)
            elem.className = className ? className : '';
    }
}

tableRows = [];
var initResultsTable = function () {
    var elem = getElement('results');
    if (elem) {
        tableRows.push(TR(null,
            TH(null, 'Initiated'),
            TH(null, 'Status'),
            TH(null, 'Elapsed'),
            TH(null, 'Received')))
        for (var i = 0; i < histCount; ++i)
            tableRows.push(TR(null, 
                TD(null, 'n/a'), TD(null, 'n/a'), 
                TD(null, 'n/a'), TD(null, 'n/a')))
        replaceChildNodes(elem, TABLE(null, TBODY(null, tableRows)));
    }
}

var prettyMS = function (t)
{
    if (t)
        return (t / 1000.0).toFixed(2) + ' secs';
}

var updateResults = function () {
    var now = new Date();
    var rowCount = 1;
    if (refresh)
        refresh.cancel();
    for (var i = results.length - 1; i >= 0; --i) {
        var info = results[i];
        var row = tableRows[rowCount++];
        var status_class;
        var elapsed = '';
        switch (info.status) {
        case 'pending':
            status_class = 'notice';
            elapsed = prettyMS(now.getTime() - info.started.getTime());
            break;
        case 'failed':
            status_class = 'error';
            break;
        case 'completed':
            status_class = '';
            elapsed = prettyMS(info.elapsed);
            break;
        }
        updateCell(row.cells[0], toISOTimestamp(info.started));
        updateCell(row.cells[1], info.status, status_class);
        updateCell(row.cells[2], elapsed);
        updateCell(row.cells[3], info.received ? info.received : '');
    }
    updateCell("stat_requests", requestCount);
    updateCell("stat_responses", responseCount);
    if (requestCount > 0)
        updateCell("stat_rate", (responseCount * 100.0 / requestCount).toFixed(2) + '%');
    updateCell("stat_minimum", prettyMS(minTime));
    updateCell("stat_maximum", prettyMS(maxTime));
    if (responseCount)
        updateCell("stat_average", prettyMS(cumTime / responseCount));
    refresh = callLater(10, updateResults);
}

var toggleLog = function (id, button) {
    var elem = getElement(id);
    if (elem) {
        if (hasElementClass(elem, "hidden")) {
            removeElementClass(elem, "hidden");
            button.value = button.value.replace('View', 'Hide');
        } else {
            addElementClass(elem, "hidden");
            button.value = button.value.replace('Hide', 'View');
        }
    }
}
var stopStartTester = function (button) {
    if (running && running.fired == -1) {
        stop();
        button.value = 'Start';
    } else {
        start();
        button.value = 'Stop';
    }

}
var requestSuccess = function (info, req) {
    var now = new Date()
    info.elapsed = now.getTime() - info.started.getTime();
    info.status = 'completed';
    cumTime += info.elapsed;
    ++responseCount;
    if (minTime === undefined || info.elapsed < minTime)
        minTime = info.elapsed;
    if (maxTime === undefined || info.elapsed > maxTime)
        maxTime = info.elapsed;
    var form = document.forms.params_form;
    var data = evalJSONRequest(req);
    if (form) {
        if (data.url)
            form.server.value = data.url;
        if (data.sendcount)
            form.sendcount.value = data.sendcount;
        if (data.interval)
            form.interval.value = (data.interval / 60.0).toFixed(3);
        if (data.motd)
            updateCell("motd", data.motd, "motd");
        else
            updateCell("motd", "", "hidden");
        if (data.junk)
            info.received = data.junk.length;
    }
    updateResults();
}
var requestFailure = function (info, err) {
    log(Date(), "async request failed", err);
    info.status = 'failed';
    updateResults();
}
var makeClientReport = function () {
    var lines = [];
    var form = document.forms.params_form;
    if (!form) return;
    lines.push(form.siteinfo.value);
    // Skip the current one as it will always be "pending"
    for (var i = results.length - 2; i >= 0; --i) {
        var info = results[i];
        lines.push([
            info.started.getTime(), 
            info.status,
            info.elapsed,
            info.received
        ].join(','));
    }
    lines.push('-- ');
    return lines;
}
var nullFn = function () {};

var getOnReadyStateChangeClosure = function (req, ctx) {
    return function () {
        if (req.readyState == 4) {
            var status = req.status;
            req.onreadystatechange = nullFn;
            if (status == 200 || status == 304)
                requestSuccess(ctx, req);
            else
                requestFailure(ctx, req.status);
        }
    }
}

var makeAsyncReq = function () {
    var form = document.forms.params_form;
    if (!form) return;
    var url = form.server.value;
    var interval = form.interval.value * 60.0;
    running = callLater(interval, makeAsyncReq);
    if (junk.length != form.sendcount.value) {
        while (junk.length < form.sendcount.value)
            junk = junk + junk;
        junk = junk.slice(0, form.sendcount.value);
    }
    var now = new Date();
    var info = {
        'started': now, 
        'status': 'pending',
        'elapsed': undefined,
        'received': undefined
    };
    results.push(info);
    if (results.length > histCount)
        results = results.slice(results.length - histCount);
    var report = makeClientReport();
    report.push(junk);
    var req = getXMLHttpRequest();
    req.open('POST', url, true);
    req.onreadystatechange = getOnReadyStateChangeClosure(req, info);
    req.send(report.join('\n'));
    /* 
     * sendXMLHttpRequest appears to be leaking references under IE - suspect
     * it's use of continuations (sendContent certainly lives longer than it
     * needs to) - disabled for now.
    var d = sendXMLHttpRequest(req,report.join('\n')); 
    d.addCallback(requestSuccess, info);
    d.addErrback(requestFailure, info);
    */
    ++requestCount;
    updateResults();
}
var flashSiteInfo = function () {
    elem = getElement('siteinfo');
    if (!elem.value) {
        if (!flasher || flasher.fired != -1) {
            toggleElementClass('notice', elem);
            elem.focus();
            flasher = callLater(2, flashSiteInfo);
        }
    } else {
        removeElementClass(elem, "notice");
    }
}
var stop = function () {
    if (running) {
        running.cancel();
        log(Date(), "Tester stopped");
    }
    if (refresh)
        refresh.cancel();
    updateCell("stat_running", 'STOPPED', 'notice');
}
var start = function () {
    var form = document.forms.params_form;
    if (form.siteinfo.value) {
        log(Date(), "Tester starting");
        makeAsyncReq();
        updateCell("stat_running", 'Yes');
    } else {
        stop();
        flashSiteInfo();
    }
}

var interactTesterOnLoad = function () {
    createLoggingPane(true);
    initResultsTable();
    start();
}
addLoadEvent(interactTesterOnLoad);
