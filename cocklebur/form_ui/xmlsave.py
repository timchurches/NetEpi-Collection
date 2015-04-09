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

### TODO - encode output as UTF-8

from cocklebur.xmlwriter import XMLwriter

__all__ = 'xmlsave',

def text(x, tag, text):
    e = x.push(tag)
    e.text(text)
    x.pop()

def choice(x, name, value):
    e = x.push('choice')
    e.attr('name', name)
    if value is not None:
        e.text(value)
    x.pop()

def skip(x, skip):
    if skip.values:
        e = x.push('skip')
        e.attr('name', skip.name)
        if skip.not_selected:
            e.attr('mode', 'ifnotselected')
        if not skip.show_msg:
            e.attr('showmsg', 'no')
        if not skip.skip_remaining:
            e.attr('skipremaining', 'no')
        for value in skip.values:
            e = x.push('skipvalue')
            e.attr('value', value)
            x.pop()
        x.pop()

def input(x, node):
    def opttext(a):
        v = attrs.get(a)
        if v:
            text(x, a, v)

    attrs = vars(node)
    e = x.push('input')
    e.attr('name', node.column)
    e.attr('type', node.__class__.__name__)
    e.optattr(node, 'required')
    e.optattr(node, 'summarise')
    e.optattr(node, 'default')
    e.optattr(node, 'minimum')
    e.optattr(node, 'maximum')
    e.optattr(node, 'maxsize')
    if hasattr(node, 'direction'):
        e.optattr(node, 'direction')
    opttext('label')
    opttext('pre_text')
    opttext('post_text')
    choices = attrs.get('choices')
    if choices:
        x.push('choices')
        for value, label in choices:
            choice(x, value, label)
        x.pop()
    skips = attrs.get('skips', ())
    if skips:
        for s in skips:
            skip(x, s)
    x.pop()

def trigger(x, trigger):
    e = x.push('trigger')
    e.attr('name', trigger)
    x.pop()

def question(x, node):
    e = x.push('question')
    e.optattr(node, 'disabled')
    if node.triggers:
        e.optattr(node, 'trigger_mode')
    text(x, 'label', node.text or '')
    if node.help:
        text(x, 'help', node.help)
    if node.triggers:
        for name in node.triggers:
            trigger(x, name)
    for child in node.inputs:
        input(x, child)
    x.pop()

def _section(x, node):
    text(x, 'label', node.text)
    for child in node.children:
        if hasattr(child, 'children'):
            section(x, child)
        elif hasattr(child, 'inputs'):
            question(x, child)

def section(x, node):
    x.push('section')
    _section(x, node)
    x.pop()

def xmlsave(f, node):
    x = XMLwriter(f)
    e = x.push('form')
    e.attr('name', node.name)
    e.attr('form_type', getattr(node, 'form_type', 'case'))
    e.attr('allow_multiple', getattr(node, 'allow_multiple', False))
    e.optattr(node, 'author')
    e.optattr(node, 'username')
    if node.update_time:
        e.attr('update_time', node.update_time.strftime('%F %T'))
    _section(x, node)
    x.pop()
