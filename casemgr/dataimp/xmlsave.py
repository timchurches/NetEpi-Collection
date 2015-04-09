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
#

from cocklebur.xmlwriter import XMLwriter
import elements

translation_type_to_xml = {}

def date(x, node):
    e = x.push('date')
    e.attr('format', node.format)
    x.pop()

translation_type_to_xml[elements.Date] = date

def translate(x, node):
    e = x.push('translate')
    e.attr('match', node.match)
    e.attr('to', node.to)
    if node.ignorecase:
        e.attr('ignorecase', 'yes')
    x.pop()

translation_type_to_xml[elements.Translate] = translate

def regexp(x, node):
    e = x.push('regexp')
    e.attr('match', node.match)
    e.attr('to', node.to)
    if node.ignorecase:
        e.attr('ignorecase', 'yes')
    x.pop()

translation_type_to_xml[elements.RegExp] = regexp

def case(x, node):
    e = x.push('case')
    e.attr('mode', node.mode)
    x.pop()

translation_type_to_xml[elements.Case] = case

def translations(x, node):
    for child in node.translations:
        assert isinstance(child, elements.TranslationBase)
        translation_type_to_xml[child.__class__](x, child)

import_type_to_xml = {}

def source(x, node):
    e = x.push('source')
    e.attr('field', node.field)
    e.attr('src', node.src)
    translations(x, node)
    x.pop()

import_type_to_xml[elements.ImportSource] = source

def agesource(x, node):
    e = x.push('agesource')
    e.attr('field', node.field)
    e.attr('src', node.src)
    if node.age:
        e.attr('age', node.age)
    translations(x, node)
    x.pop()

import_type_to_xml[elements.ImportAgeSource] = agesource

def multivalue(x, node):
    e = x.push('multivalue')
    e.attr('field', node.field)
    e.attr('src', node.src)
    e.attr('delimiter', node.delimiter or '')
    translations(x, node)
    x.pop()

import_type_to_xml[elements.ImportMultiValue] = multivalue


def fixed(x, node):
    e = x.push('fixed')
    e.attr('field', node.field)
    e.attr('value', node.value)
    translations(x, node)
    x.pop()

import_type_to_xml[elements.ImportFixed] = fixed
    

def ignore(x, node):
    e = x.push('ignore')
    e.attr('field', node.field)
    x.pop()

import_type_to_xml[elements.ImportIgnore] = ignore


def form(x, node):
    if node:
        e = x.push('form')
        e.attr('name', node.name)
        e.attr('version', node.version)
        for child in node:
            assert isinstance(child, elements.ImportColumnBase)
            import_type_to_xml[child.__class__](x, child)
        x.pop()

import_type_to_xml[elements.ImportForm] = form


def xmlsave(f, node):
    x = XMLwriter(f)
    e = x.push('importrules')
    e.attr('name', node.name)
    e.attr('mode', node.mode)
    e.attr('encoding', node.encoding)
    e.attr('fieldsep', node.fieldsep)
    e.attr('srclabel', node.srclabel)
    e.attr('conflicts', node.conflicts)
    for child in node:
        import_type_to_xml[child.__class__](x, child)
    for child in node.forms():
        import_type_to_xml[child.__class__](x, child)
    x.pop()
