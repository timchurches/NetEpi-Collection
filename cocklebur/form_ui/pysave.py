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

__all__ = 'pysave', 

def input(f, node, indent):
    cls = node.__class__
    clsname = cls.__name__
    attr_list = [repr(node.column)]
    ignore = 'column', 'error', 'table', 'choices'
    attrs = vars(node)
    for a, v in attrs.items():
        if a not in ignore and v is not None:
            if hasattr(cls, a) and getattr(cls, a) == v:
                continue
            attr_list.append('%s = %r' % (a, v))
    choices = attrs.get('choices')
    if choices:
        choice_str = ['    %r,\n' % (c,) for c in node.choices]
        choice_str.insert(0, 'choices = [\n')
        choice_str.append(']')
        attr_list.append(''.join(choice_str))
    lines = ',\n'.join(attr_list).replace('\n', '\n' + ' ' * indent)
    f.write('%s(%s),\n' % (clsname, lines))

def question(f, node, parentvarname):
    f.write('%s.question(\n' % parentvarname)
    f.write('    text = %r,\n' % node.text)
    if hasattr(node, 'help') and node.help:
        f.write('    help = %r,\n' % node.help)
    if hasattr(node, 'disabled') and node.disabled:
        f.write('    disabled = True,\n')
    if hasattr(node, 'triggers') and node.triggers:
        if hasattr(node, 'trigger_mode'):
            f.write('    trigger_mode = %r,\n' % node.trigger_mode)
        f.write('    triggers = %r,\n' % list(node.triggers))
    if len(node.inputs) == 1:
        f.write('    input = ')
        input(f, node.inputs[0], 8)
    else:
        f.write('    inputs = [\n')
        for inp in node.inputs:
            f.write(' ' * 8)
            input(f, inp, 12)
        f.write('    ],\n')
    f.write(')\n')

def section(f, node, clsname):
    varname = clsname.lower()
    args = [repr(node.text)]
    if clsname == 'Form':
        if node.form_type:
            args.append('form_type=%r' % node.form_type)
        if node.allow_multiple:
            args.append('allow_multiple=%r' % node.allow_multiple)
        if node.update_time:
            args.append('update_time=%r' % node.update_time.strftime('%F %T'))
        if node.username:
            args.append('username=%r' % node.username)
        if node.author:
            args.append('author=%r' % node.author)
    f.write('%s = %s(%s)\n' % (varname, clsname, ', '.join(args)))
    for child in node.children:
        if hasattr(child, 'children'):
            if clsname == 'Form':
                childclsname = 'Section'
            else:
                childclsname = 'Section'
            section(f, child, childclsname)
            f.write('%s.append(%s)\n' % (varname, childclsname.lower()))
        elif hasattr(child, 'inputs'):
            question(f, child, varname)

def form(f, node):
#    form_extra_cols[form_type].save(f, node.columns)
    attrs = vars(node)
    f.write('from cocklebur.form_ui import *\n')
    f.write('from cocklebur import dbobj\n')
    section(f, node, 'Form')

def pysave(f, node):
    form(f, node)

