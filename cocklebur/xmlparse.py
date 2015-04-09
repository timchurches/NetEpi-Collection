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

"""
This lightweight expat-based XML parser acts as a facilitator for
building trees of external objects, rather than producing a tree of it's
own objects.

For each element found, a (user supplied) Node subclass is
instantiated. Subclasses are expected to override one or more of the
event methods to achieve their ends:

    start_element(parent)
    end_child(child)
    end_element(parent)

Element attributes appear on the Node instance in the .attrs property.

Text contained in an element can be retrieved with the .get_text() method.

A ContainerNode class if provided as a basis for elements that collect
up their children (nodes).

A SetAttrNode class is provided for elements that simply set an attr on
their parent. The attr name should be set in your subclass with the /attr/
class property.

Node instances are slotted for performance - if you need to add extra
attributes, you will need to register extra __slots__.

Examples of use include:

    cocklebur/form_ui/xmlload.py
    casemgr/dataimp/xmlload.py
    casemgr/reports/xmlload.py
"""

import sys
try:
    set
except NameError:
    from sets import Set as set
from xml.parsers import expat

__all__ = (
    'Node', 'ContainerNode' 'SetAttrNode', 
    'XMLParse', 'ParseError', 
)

class ParseError(expat.ExpatError): pass

bool_values = {
    'yes': True,
    'true': True,
    'no': False,
    'false': False,
    '': False,
}

def bool_cvt(v):
    try:
        return bool_values[v.lower()]
    except KeyError:
        raise ParseError('invalid boolean value: %r' % v)

attr_cvt = {
    'int': int,
    'long': int,
    'float': float,
    'bool': bool_cvt,
    'str': str,
    'unicode': unicode,
}

class NodeMeta(type):

    def __new__(meta, name, bases, vars):
        vars.setdefault('__slots__', ())
        cls = type.__new__(meta, name, bases, vars)
        cls.name = name.lower()
        cls.subtabs = set(cls.subtags)
        cls.attr_cvt = {}
        for attr in (cls.required_attrs + cls.permit_attrs):
            try:
                attr, attr_type = attr.split(':', 1)
            except ValueError:
                cvt = None
            else:
                try:
                    cvt = attr_cvt[attr_type]
                except KeyError:
                    raise TypeError('unknown type conversion for %s '
                                    'attribute: %s' % (attr, attr_type))
            cls.attr_cvt[attr] = cvt
        cls.required_attrs = tuple([a.split(':')[0] 
                                    for a in cls.required_attrs])
        return cls


class Node(object):

    __metaclass__ = NodeMeta
    __slots__ = 'attrs', 'text'
    required_attrs = ()
    permit_attrs = ()
    subtags = ()

    def __init__(self, attrs):
        self.attrs = {}
        for attr in self.required_attrs:
            if attr not in attrs:
                raise ParseError('<%s> tag requires %r attribute' %
                                    (self.name, attr))
        for attr, value in attrs.items():
            try:
                attr_cvt = self.attr_cvt[attr]
            except KeyError:
                raise ParseError('unknown attribute %r on <%s> tag' % 
                                    (attr, self.name))
            if attr_cvt is not None:
                try:
                    value = attr_cvt(value)
                except Exception, e:
                    raise ParseError('<%s>, %s=%r: %s' % 
                                     (self.name, attr, value, e))
            self.attrs[str(attr)] = value
        self.text = []

    def start_element(self, parent):
        pass

    def end_element(self, parent):
        pass

    def end_child(self, child):
        pass

    def cdata(self, data):
        self.text.append(data)

    def get_text(self):
        return ''.join(self.text)


class SetAttrNode(Node):
    subtags = ()
    attr = None

    def end_element(self, parent):
        text = self.get_text()
        if text:
            parent.attrs[self.attr] = text


class ContainerNode(Node):
    __slots__ = 'children', 

    def start_element(self, parent):
        self.children = []
    
    def end_child(self, child):
        self.children.append(child)


class XMLParseMeta(type):
    def __init__(cls, name, bases, dict):
        if name != 'XMLParse':
            # Collect up the names of the contained nodes
            cls.handlers = {}
            for base in bases:
                base_handlers = getattr(base, 'handlers', None)
                if base_handlers:
                    cls.handlers.update(base_handlers)
            for k, v in dict.iteritems():
                try:
                    if not k.startswith('_') and issubclass(v, Node):
                        cls.handlers[v.name] = v
                except TypeError:
                    pass


class XMLParse(object):
    __metaclass__ = XMLParseMeta
    root_tag = None

    def __init__(self):
        self.parser = expat.ParserCreate()
        # too hard for now - all returns are unicode
        self.parser.returns_unicode = False
        self.parser.StartElementHandler = self.start_element
        self.parser.EndElementHandler = self.end_element
        self.parser.CharacterDataHandler = self.cdata
        self.stack = []
        self.root = None

    def parse(self, f):
        try:
            self.parser.ParseFile(f)
        except expat.ExpatError, e:
            e = str(e)
            if ': line ' not in e:
                e = '%s: line %s' % (e, self.parser.ErrorLineNumber)
            if len(self.stack) > 1:
                e += ', in %s' % self.stack[-1].name
            raise ParseError, e, sys.exc_info()[2]
        # expat catches both of these, but it's better to be safe...
        if self.root is None:
            raise ParseError('No top level tag seen')
        if self.stack:
            raise ParseError('Stack unbalanced')
        return self.root

    def start_element(self, name, attrs):
        try:
            tag_class = self.handlers[name]
        except KeyError:
            raise ParseError('unknown tag: <%s>' % name)
        tag = tag_class(attrs)
        if self.stack:
            parent = self.stack[-1]
            if name not in parent.subtags:
                raise ParseError('<%s> not allowed within <%s>' % 
                                    (name, parent.name))
        else:
            if self.root_tag is not None and name != self.root_tag:
                raise ParseError('<%s> not allowed at top level' % name)
            parent = None
            if self.root is not None:
                raise ParseError('already seen top level <%s>' % name)
            self.root = tag
        tag.start_element(parent)
        self.stack.append(tag)

    def end_element(self, name):
        child = self.stack.pop(-1)
        parent = None
        if self.stack:
            parent = self.stack[-1]
        child.end_element(parent)
        if parent is not None:
            parent.end_child(child)

    def cdata(self, data):
        element = self.stack[-1]
        if element:
            element.cdata(data)
