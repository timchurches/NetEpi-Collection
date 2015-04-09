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

/* Sort a table that has been prepared by sorttable_init using the column
 * specified by /index/
 */

function sorttable (context, index) {
    function order (a, b) {
        if (isNaN(a.num) || isNaN(b.num)) {
            return a.text < b.text ? -context.direction : 
                        (a.text > b.text ? context.direction : 0);
        } else
            return (a.num - b.num) * context.direction;
    }
    if (context.lastIndex == index)
        context.direction = -context.direction;
    context.lastIndex = index;
    /* Create a new tBody list, sort it, and reattach */
    for (var tbi = 0; tbi < context.table.tBodies.length; ++tbi) {
        var tbody = context.table.tBodies[tbi];
        var rows = new Array();
        var classNames = new Array();
        for (var i = 0; i < tbody.rows.length; ++i) {
            var row = tbody.rows[i];
            if (row.cells.length != context.ncols) continue;
            var text = getText(row.cells[index]).toLowerCase();
            rows[i] = {
                row: row, 
                text: text,
                num: Number(text)
            }
            classNames[i] = row.className;
        }
        if (!rows.length) continue;
        rows.sort(order);
        for (var ri = 0; ri < rows.length; ++ri) {
            var row = rows[ri].row;
            row.className = classNames[ri];
            tbody.appendChild(row);
        }
    }
    /* Update sort column and direction indicating arrows */
    for (var thi=0, ll=context.table.tHead.rows.length; thi < ll; ++thi) {
        var row = context.table.tHead.rows[thi];
        for (var i = 0; i < row.cells.length; ++i) {
            var header = row.cells[i];
            if (elementHasClass(header, 'sortable')) {
                var arrows = header.firstChild;
                if (index == i) {
                    if (context.direction < 0)
                        arrows.innerHTML = '&#9650;';
                    else
                        arrows.innerHTML = '&#9660;';
                }
                else
                    arrows.innerHTML = '';
            }
        }
    }
}

/* finds all the tables of class /sorttable/ in the document, and makes any
 * <thead> cells that are class /sortable/ clickable. When clicked, the table
 * is sorted by that column. The table must be regular with no spans or missing
 * cells.
 */
function sorttable_init () {
    function get_click_closure (context, i) { 
        return function (event) { return sorttable(context, i); }
    }
    var context;
    var defaultsort;
    var tables = document.getElementsByTagName("table");
    for (var i = 0; i < tables.length; ++i) {
        if (elementHasClass(tables[i], 'sorttable')) {
            context = {lastIndex: -1, direction: 1, table: tables[i]}
            defaultsort = undefined;
            for (var thi = 0; thi < context.table.tHead.rows.length; ++thi) {
                var row = context.table.tHead.rows[thi];
                context.ncols = row.cells.length;
                for (var i = 0; i < row.cells.length; ++i) {
                    var header = row.cells[i];
                    if (elementHasClass(header, 'sortable')) {
                        var click = get_click_closure(context, i);
                        addEvent(header, "click", click);
                        var div = document.createElement('div');
                        div.style.width = '1.4em';
                        div.style.fontSize = '90%';
                        div.style.textAlign = 'center';
                        div.style.cssFloat = div.style.styleFloat = 'right';
                        header.insertBefore(div, header.firstChild);
                        if (elementHasClass(header, 'defaultsort'))
                            defaultsort = i;
                    }
                }
            }
            if (defaultsort != undefined)
                sorttable(context, defaultsort);
        }
    }
}
addEvent(window, "load", sorttable_init);

