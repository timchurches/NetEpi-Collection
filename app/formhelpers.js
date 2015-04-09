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

/* REQUIRES:
 *  casemgr/helpers.js
 */

var form_prefix = 'form_data.';
var no_disable_index = 99999;
var skips_by_input = {};

// Scan all questions on the form, and update their styling to reflect their
// "want_disable" status.
function disable_input(input) {
    input.disabled = true;
    addClass(input, 'disabledq');
}
function enable_input(input) {
    input.disabled = false;
    rmClass(input, 'disabledq');
}

// Where multiple inputs share a name, we get some sort of container object,
// and need to iterate over the members...
function applyinput(fn, node) {
    if (!node) return;
    if (node.disabled === undefined)
        for (var i = 0; i < node.length; ++i)
            fn(node[i]);
    else {
        fn(node);
        // Some inputs have a button dynamically added after the input - we
        // want it's state to reflect the state of the main input.
        var next = node.nextSibling;
        if (next && next.type == 'button')
            fn(next);
    }
}

function do_disables() {
    for (var name in form_questions) {
        var question = form_questions[name];
        if (question.disable_index != question.want_disable_index) {
            // alert('disable ' + question.name + ' index ' + question.want_disable_index);
            if (question.want_disable_index == 0)
                addClass(question.node, 'disabledq');
            else
                rmClass(question.node, 'disabledq');
            for (var i = 0; i < question.inputs.length; ++i) {
                var disable = (i >= question.want_disable_index);
                var fields = question.inputs[i];
                for (var j = 0; j < fields.length; ++j)
                    applyinput(disable ? disable_input : enable_input, 
                               question.form[form_prefix + fields[j]]);
            }
            question.disable_index = question.want_disable_index;
        }
    }
}

function _get_input_value(input) {
    switch (input.nodeName) {
    case 'INPUT':
        switch (input.type) {
        case 'radio':
        case 'checkbox':
            return input.checked ? input.value : null;
        default:
            return input.value;
        }
        break;
    case 'OPTION':
        if (input.selected)
            return input.value ? input.value : input.text;
        return null;
    }
}
function get_input_values (input) {
    if (!input) return;
    if (input.length) {
        var values = [];
        for (var i = 0; i < input.length; ++i) {
            var v = _get_input_value(input[i]);
            if (v != null) values.push(v);
        }
        return values;
    }
    else 
        return [_get_input_value(input)];
}

// Clear all question's "want_disable" status.
function clear_want_disable() {
    for (var name in form_questions) {
        var question = form_questions[name];
        if (question.trigger_mode == 'enable')
            question.want_disable_index = 0;
        else
            question.want_disable_index = no_disable_index;
    }
}

// Scan all "skips" and update input-disables to reflect
function skips_update_disables () {
    clear_want_disable();
    for (var j = 0; j < form_skips.length; ++j) {
        var skip = form_skips[j];
        if (skip.fired)
            for (var i = 0; i < skip.targets.length; ++i) {
                var question = form_questions[skip.targets[i]];
                var index = (question === skip.question) ? skip.next_input : 0;
                // alert([skip.name, question.name, question.trigger_mode, skip.question.name, question === skip.question, index, question.want_disable_index].join(' '));
                if (index == 0 && question.trigger_mode == 'enable')
                    question.want_disable_index = no_disable_index;
                else if (index < question.want_disable_index)
                    question.want_disable_index = index;
            }
    }
}

// An input associated with "skip" has fired - scan all the skips associated
// with this skip to determine it's status.
function skip_event (skip) {
    if (!skip) return;
    skip.fired = skip.inverted;
    for (var j = 0; j < skip.inputs.length; ++j) {
        var input = skip.inputs[j];
        var input_values = get_input_values(input.elements);
        // alert('input pending ' + input.name + ' value ' + input_values);
        if (input_values)
            for (var i = 0; i < input_values.length; ++i) {
                var value = input_values[i];
                if (input.has_value[value]) {
                    skip.fired = !skip.inverted;
                    return;
                }
            }
    }

}

var inputs_pending = {};
var inputs_pending_timer = false;

// At least one input event has been received - update the effecticed skip's
// state, then recalculate input-disables. 
function check_pending_inputs () {
    inputs_pending_timer = false;
    for (var name in inputs_pending) {
        var name = name.substr(form_prefix.length);
        var skips_for_input = skips_by_input[name];
        for (var i = 0; i < skips_for_input.length; ++i)
            skip_event(skips_for_input[i]);
    }
    inputs_pending = {};
    skips_update_disables();
    do_disables();
}

// An input has fired - make a note, check noted inputs later. We monitor a
// number of events from every input to ensure we're reliably woken up, so this
// logic effectively merges the multiple events back into a single per-input
// event.
function input_event(ev) {
    var src = ev.target ? ev.target : ev.srcElement;
    //alert([src, src.parentNode.name, src.name, src.type].join());
    if (!src.name) return;
    inputs_pending[src.name] = true;
    if (!inputs_pending_timer) {
        inputs_pending_timer = true;
        setTimeout(check_pending_inputs, 100);
    }
}

function form_question_init () {
    try {var ignored=form_data_version} catch (e) {form_data_version=0};
    if (form_data_version != 1) {
        alert('Your web browser has used an incorrect version of ' +
              'formhelpers.js - form skips and error jumps are unavailable!');
        return;
    }
    var form = document['appform'];
    var q_count = 0;
    var first_error;
    calendar_init();    // onLoad handlers run in undefined order
    for (var name in form_questions) {
        var question = form_questions[name];
        question.disable_index = no_disable_index;
        question.form = form;
        question.node = document.getElementById('Q_' + question.name);
        question.input_index = {};
        for (var i = 0; i < question.inputs.length; ++i) {
            var fields = question.inputs[i];
            for (var j = 0; j < fields.length; ++j)
                question.input_index[fields[j]] = i;
        }
        if (question.node) {
            ++q_count;
            if (!first_error && question.error) first_error = question;
        }
    }
    var w_count = 0;
    for (var i = 0; i < form_skips.length; ++i) {
        var skip = form_skips[i];
        if (!form_questions[skip.question])
            alert('skip question not found ' + skip.question);
        skip.question = form_questions[skip.question];
        skip.next_input = 0;
        for (var j = 0; j < skip.inputs.length; ++j) {
            var input = skip.inputs[j];
            var input_skip_list = skips_by_input[input.name];
            if (input_skip_list)
                input_skip_list.push(skip);
            else
                skips_by_input[input.name] = [skip];
            input.elements = form[form_prefix + input.name];
            input.has_value = {};
            if (input.elements) {
                var input_index = skip.question.input_index[input.name];
//                if (input_index == undefined)
//                    alert('Input index not found, input ' + input.name);
                if (skip.next_input < input_index + 1)
                    skip.next_input = input_index + 1;
                var binder = function (input) {
                    if (!input.name) input = input.parentNode;
                    addEvent(input, 'focus', input_event);
                    addEvent(input, 'blur', input_event);
                    addEvent(input, 'change', input_event);
                    addEvent(input, 'click', input_event);
                }
                forEach(input.elements, binder);
                for (var k = 0; k < input.values.length; ++k)
                    input.has_value[input.values[k]] = true;
                ++w_count;
            }
//            else
//                alert('Input elements not found: ' + form_prefix + input.name);
        }
        skip_event(skip);
    }
    skips_update_disables();
    do_disables();
    if (first_error)
        scrollToElement(first_error.node);
    //alert('Bound ' + q_count + ' questions, ' + w_count + ' widgets for ' + form_skips.length + ' skips');
}
addEvent(window, "load", form_question_init);
