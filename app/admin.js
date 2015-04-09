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


/* depends on helpers.js */

/*global window 
    absNodePos addClass addEvent appendAfter cancelEvent cancelSelection
    classApply clickOn delEvent distance elementHasClass mouseIsNear parentTag
    rmClass syntheticSubmit viewTopLeft */

var jsselect = function (topNodeName, selectCallback, clickCallback, 
                         pathSnapping) {
    var topNode = document.getElementById(topNodeName),
        selectableMap = {},
        selectableOrder = [],
        startSelection, endSelection,
        initialX, initialY, initialNode,
        floater = document.createElement('div');
    var box = function (a, b) {
        // Adjust size of "floater" to enclose nodes "a" and "b"
        var aPos = absNodePos(a),
            bPos = absNodePos(b),
            x1 = Math.min(aPos.x, bPos.x),
            y1 = Math.min(aPos.y, bPos.y),
            x2 = Math.max(aPos.x + a.clientWidth, bPos.x + b.clientWidth),
            y2 = Math.max(aPos.y + a.clientHeight, bPos.y + b.clientHeight);
        floater.style.left = x1 + 'px';
        floater.style.top = y1 + 'px';
        floater.style.width = (x2 - x1) + 'px';
        floater.style.height = (y2 - y1) + 'px';
    };
    var findSelectable = function (node) {
        // Recurse back up the tree looking for a "selectable" node, stopping
        // if we see a node with "noselect" in CSS class, or hit top.
        while (node) {
            if (elementHasClass(node, 'noselect')) {
                return null;
            }
            if (node.id && node.id in selectableMap) {
                break;
            }
            node = node.parentNode;
        }
        return node;
    };
    var pathSnap = function (includeChildren) {
        // If selectable identifiers are in a heirachy, ensure selection only
        // selects nodes at the same level.
        var i = Math.min(startSelection, endSelection),
            ll = Math.max(startSelection, endSelection),
            selected = [], prefixes = {},
            minlen = 999, node, nodeName;
        for (;i <= ll; i++) {
            node = selectableOrder[i];
            selected.push(node.id);
            if (node.id.length < minlen) {
                minlen = node.id.length;
            }
        }
        for (i = 0, ll = selected.length; i < ll; ++i) {
            prefixes[selected[i].substr(0, minlen)] = undefined;
        }
        selected = [];
        for (i = 0, ll = selectableOrder.length; i < ll; ++i) {
            node = selectableOrder[i];
            nodeName = includeChildren ? node.id.substr(0, minlen) : node.id;
            if (node.id && nodeName in prefixes) {
                selected.push(node);
            }
        }
        return selected;
    };
    var getSelection = function () {
        var lower, upper;
        if (pathSnapping) {
            return pathSnap();
        } else {
            lower = Math.min(startSelection, endSelection);
            upper = Math.max(startSelection, endSelection);
            return selectableOrder.slice(lower, upper + 1);
        }
    };
    var clearSelection = function () {
        startSelection = endSelection = undefined;
        initialX = initialY = initialNode = undefined;
    };
    var clearHighlight = function () {
        document.body.removeChild(floater);
    };
    var scrollIfNeeded = function (mouseY) {
        var threshold = 50,
            viewTop = window.scrollY || document.documentElement.scrollTop,
            viewLeft = window.scrollX || document.documentElement.scrollLeft,
            viewHeight = (window.innerHeight || 
                                  document.documentElement.clientHeight);
        if (mouseY < threshold) {
            window.scrollTo(viewLeft, viewTop - threshold / 2);
        } else if (mouseY > viewHeight - threshold) {
            window.scrollTo(viewLeft, viewTop + threshold / 2);
        }
    };
    var doMouseMove = function (e) {
        var ev = e || event,
            target = ev.target || ev.srcElement,
            selected;
        if (startSelection === undefined) {
            if (distance(ev.screenX, ev.screenY, initialX, initialY) < 20) {
                return true;
            }
            startSelection = selectableMap[findSelectable(initialNode).id];
            document.body.insertBefore(floater, document.body.firstChild);
        }
        cancelSelection();
        target = findSelectable(target);
        if (!target) {
            return true;
        }
        endSelection = selectableMap[target.id];
        scrollIfNeeded(ev.clientY);
        if (pathSnapping) {
            selected = pathSnap(true);
            box(selected[0], selected[selected.length - 1]);
        } else {
            box(selectableOrder[startSelection], target);
        }
    };
    var doMouseUp = function (e) {
        var ev = e || event,
            selected;
        delEvent(document.body, 'mouseup', doMouseUp);
        delEvent(document.body, 'mousemove', doMouseMove);
        if (startSelection === undefined) {
            if (clickCallback) {
                clickCallback(initialNode, ev);
            } else {
                clickOn(initialNode);
            }
        } else {
            if (selectCallback) {
                selected = getSelection();
                clearSelection();
                selectCallback(selected, clearHighlight, ev);
            } else {
                clearSelection();
                clearHighlight();
            }
        }
    };
    var doMouseDown = function (e) {
        var ev = e || event,
            target = ev.target || ev.srcElement,
            is_oldIE = !ev.preventDefault;
        if ((is_oldIE && ev.button !== 1) ||
            (!is_oldIE && ev.button !== 0)) {
            return;
        }
        if (!findSelectable(target)) {
            return true;
        }
        initialX = ev.screenX;
        initialY = ev.screenY;
        initialNode = target;
        addEvent(document.body, 'mouseup', doMouseUp);
        addEvent(document.body, 'mousemove', doMouseMove);
        return cancelEvent(ev);
    };
    floater.style.position = 'absolute';
    floater.style.filter = 'progid:DXImageTransform.Microsoft.Alpha(Opacity=30)';
    floater.style.opacity = '0.3';
    floater.style.zIndex = -1;
    floater.className = 'selector';
    classApply(topNode, 'selectable', 
        function (node) {
            if (node.id) {
                selectableMap[node.id] = selectableOrder.length;
                selectableOrder.push(node);
                node.style.cursor = 'pointer';
                addEvent(node, 'mousedown', doMouseDown);
                addEvent(node, 'selectstart', function () { 
                    return false;
                });
            }
        });
};

var fe_click = function (node) {
    while (node && !node.id) {
        node = node.parentNode;
    }
    if (node) {
        syntheticSubmit('appform', 'edit', node.id);
    }
};

var fe_select = function (formName, selectField, actions) {
    var fe_select_handler = function (selectedNodes, clearSelection, ev) {
        var i, ll, node, kill,
            nodeNames = [],
            div = document.createElement('div'),
            form = document.forms[formName],
            viewTop = window.scrollY || document.documentElement.scrollTop,
            viewLeft = window.scrollX || document.documentElement.scrollLeft;
        var detectOut = function (e) {
            var ev = e || event,
                target = ev.target || ev.srcElement;
            while (target) {
                if (target === div) {
                    return;
                }
                target = target.parentNode;
            }
            kill();
        };
        kill = function () {
            if (div) {
                delEvent(document.body, 'mousemove', detectOut);
                form.removeChild(div);
                div = undefined;
                clearSelection();
            }
        };
        var cancel = function (e) {
            var ev = e || event;
            kill();
            cancelEvent(ev);
        };
        div.style.position = 'absolute';
        div.style.width = '6em';
        div.style.background = 'white';
        div.style.zIndex = '1000';
        div.style.top = (viewTop + ev.clientY - 10) + 'px';
        div.style.left = (viewLeft + ev.clientX - 10) + 'px';
        for (i = 0, ll = actions.length; i < ll; ++i) {
            node = document.createElement('input');
            node.type = 'submit';
            node.name = actions[i].toLowerCase();
            node.value = actions[i];
            node.style.width = '100%';
            node.style.margin = '0';
            node.className = "butt";
            div.appendChild(node);
            if (node.name === 'cancel') {
                addEvent(node, 'click', cancel);
            }
        }
        form.insertBefore(div, form.firstChild);
        addEvent(document.body, 'mousemove', detectOut);
        for (i = 0, ll = selectedNodes.length; i < ll; ++i) {
            node = selectedNodes[i];
            nodeNames.push(node.id);
        }
        form[selectField].value = nodeNames.join(',');
    };
    return fe_select_handler;
};

var expandOnHover = function (container, opener, openee) {
    var close = function () {
        opener.style.display = 'inline';
        openee.style.display = 'none';
    };
    var moveClose = function (e) {
        var ev = e || event;
        if (!mouseIsNear(container, ev)) {
            delEvent(document.body, 'mousemove', moveClose);
            close();
        }
    };
    close();
    addEvent(opener, 'mouseover', function () {
        opener.style.display = 'none';
        openee.style.display = 'inline';
        addEvent(document.body, 'mousemove', moveClose);
    });
};

var attachExpandOnHover = function (topNodeId) {
    classApply(document.getElementById(topNodeId), 'hover-expand', 
        function (node) {
            var i, ll, child, opener, openee;
            for (i = 0, ll = node.childNodes.length; i < ll; ++i) {
                child = node.childNodes[i];
                if (elementHasClass(child, 'he-opener')) {
                    opener = child;
                }
                if (elementHasClass(child, 'he-open')) {
                    openee = child;
                }
            }
            if (opener && openee) {
                expandOnHover(node, opener, openee);
            }
        });
};

var attachClickOpenOne = function (topNodeId, formName, selectField) {
    var selected;
    var open = function (select) {
        var selectNode, foldNode;
        selectNode = document.getElementById('select:' + select);
        foldNode = document.getElementById('fold:' + select);
        if (!selectNode && !foldNode) {
            alert(select + ' fold or select not found');
            return;
        }
        addClass(selectNode, 'active');
        foldNode.style.display = 'block';
        if (selected && select !== selected) {
            selectNode = document.getElementById('select:' + selected);
            foldNode = document.getElementById('fold:' + selected);
            rmClass(selectNode, 'active');
            foldNode.style.display = 'none';
        }
        selected = select;
        if (formName && selectField) {
            document.forms[formName][selectField].value = select; 
        }
    };
    var scan = function (node) {
        var i, ll, fields, fold;
        if (node.id) {
            fields = node.id.split(':');
            if (fields[0] === 'select') {
                fold = document.getElementById('fold:' + fields[1]);
                if (fold) {
                    fold.style.display = 'none';
                    node.style.cursor = 'pointer';
                    addEvent(node, 'click', function () {
                        open(fields[1]);
                    });
                }
            }
        }
        for (i = 0, ll = node.childNodes.length; i < ll; ++i) {
            scan(node.childNodes[i]);
        }
    };
    scan(document.getElementById(topNodeId));
    if (formName && selectField) {
        open(document.forms[formName][selectField].value);
    }
};

var rowMover = function (tableName, orderField) {
    var idMap = {}, nMoveableRows = 0,
        theTable = document.getElementById(tableName);
    var startMove = function (targetRow, mouseX, mouseY) {
        var dTable, offsetX, offsetY;
        var detachedRowClone = function (tr) {
            var table = tr.offsetParent,
                dTable = table.cloneNode(false),
                dBody = tr.parentNode.cloneNode(false),
                dRow = tr.cloneNode(true),
                padding = 1,
                i, ll;
            dTable.removeAttribute("id");
            dTable.style.position = "absolute";
            dBody.appendChild(dRow);
            dTable.appendChild(dBody);
            for (i = 0, ll = tr.cells.length; i < ll; ++i) {
                var cell = tr.cells[i];
                dRow.cells[i].width = (cell.clientWidth - 2 * padding) + "px";
            }
            return dTable;
        };
        var nearestRow = function () {
            var i, ll, row, rowPos,
                detachedPos = absNodePos(dTable.rows[0]);
            for (i = 0, ll = theTable.rows.length; i < ll; ++i) {
                row = theTable.rows[i];
                rowPos = absNodePos(row);
                if (row.id && 
                        distance(rowPos.x, rowPos.y, 
                                 detachedPos.x, detachedPos.y) < 20) {
                    return row;
                }
            }
        };
        var moveDetached = function (x, y) {
            var tBody, landingRow;
            dTable.style.left = (x - offsetX) + "px";
            dTable.style.top = (y - offsetY) + "px";
            landingRow = nearestRow();
            if (landingRow && landingRow !== targetRow) {
                tBody = targetRow.parentNode;
                if (targetRow.sectionRowIndex < landingRow.sectionRowIndex) {
                    tBody.removeChild(targetRow);
                    appendAfter(targetRow, landingRow);
                } else {
                    tBody.removeChild(targetRow);
                    tBody.insertBefore(targetRow, landingRow);
                }
            }
        };
        var mouseMove = function (e) {
            var ev = e || event,
                view = viewTopLeft();
            cancelSelection();
            moveDetached(view.left + ev.screenX, view.top + ev.screenY);
        };
        var setOrderField = function () {
            var i, ll, row, fields, ids = []; 
            if (orderField) {
                for (i = 0, ll = theTable.rows.length; i < ll; ++i) {
                    row = theTable.rows[i];
                    if (row.id && row.id in idMap) {
                        ids.push(idMap[row.id]);
                    }
                }
                fields = document.getElementsByName(orderField);
                for (i = 0, ll = fields.length; i < ll; ++i) {
                    fields[i].value = ids.join(',');
                }
            }
        };
        var mouseUp = function (e) {
            setOrderField();
            document.body.removeChild(dTable);
            delEvent(document.body, "mouseup", mouseUp);
            delEvent(document.body, "mousemove", mouseMove);
        };
        var rowPos = absNodePos(targetRow);
        dTable = detachedRowClone(targetRow);
        document.body.insertBefore(dTable, document.body.firstChild);
        offsetX = mouseX - (rowPos.x - dTable.rows[0].offsetLeft);
        offsetY = mouseY - (rowPos.y - dTable.rows[0].offsetTop);
        moveDetached(mouseX, mouseY);
        addEvent(document.body, "mouseup", mouseUp);
        addEvent(document.body, "mousemove", mouseMove);
    };
    var mouseDown = function (e) {
        var ev = e || event,
            view = viewTopLeft(),
            targetRow;
        targetRow = parentTag(ev.target || ev.srcElement, 'tr');
        if (targetRow) {
            startMove(targetRow, view.left + ev.screenX, view.top + ev.screenY);
        }
        return cancelEvent(ev);
    };
    classApply(theTable, "move-handle", 
        function (handleNode) {
            var rowNode = parentTag(handleNode, 'tr');
            if (rowNode) {
                if (!rowNode.id) {
                    rowNode.id = tableName + ':' + nMoveableRows;
                }
                idMap[rowNode.id] = nMoveableRows++;
                handleNode.style.cursor = 'pointer';
                addEvent(handleNode, 'mousedown', mouseDown);
            }
        }
    );
};
