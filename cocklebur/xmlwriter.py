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

from cocklebur import introspect

def quoteattr(data):
    # We'd really rather use a stdlib function, but the only one I can find is
    # xml.sax.saxutils.quoteattr, and importing that module pulls in other
    # modules which cause us problems.
    data = data.replace("&", "&amp;")
    data = data.replace(">", "&gt;")
    data = data.replace("<", "&lt;")
    data = data.replace("\n", "&#10;")
    data = data.replace("\r", "&#13;")
    data = data.replace("\t", "&#9;")
    if '"' in data:
        if "'" in data:
            data = '"%s"' % data.replace('"', "&quot;")
        else:
            data = "'%s'" % data
    else:
        data = '"%s"' % data
    return data


class XMLelement(object):

    indent = ' '

    def __init__(self, name, f, level):
        self.name = name
        self.f = f
        self.level = level
        self.opened = False
        self.attributes = []
        self.savedtext = []

    def attr(self, attr, value):
        self.attributes.append((attr, value))

    def boolattr(self, attr, value):
        if str(value).lower() in ('true', 'yes'):
            self.attr(attr, 'yes')
        else:
            self.attr(attr, 'no')

    def optattr(self, node, attr):
        value = getattr(node, attr, None) 
        if value != introspect.getclassattr(node.__class__, attr):
            self.attr(attr, value)

    def _attr_str(self):
        return ''.join([' %s=%s' % (a, quoteattr(str(v))) 
                        for a, v in self.attributes])

    def _write(self, s):
        print >> self.f, '%s%s' % (self.indent * self.level, s)
        
    def opentag(self):
        if not self.opened:
            self._write('<%s%s>' % (self.name, self._attr_str()))
            self.opened = True

    def closetag(self):
        if not self.opened and not self.savedtext:
            self._write('<%s%s />' % (self.name, self._attr_str()))
            return
        text = None
        if self.savedtext:
            text = ''.join(self.savedtext)
            if '<' in text or '>' in text or '&' in text:
                text = '<![CDATA[' + text.replace(']]>', ']]&gt;') + ']]>'
        if not self.opened and text:
            self._write('<%s%s>%s</%s>' % (self.name, self._attr_str(), 
                                            text, self.name))
            return
        else:
            self.opentag()
            if text:
                # This will result in spurious leading and trailing NL, but
                # this case only occurs for tags with mixed subtags and text.
                print >> self.f, text
            self._write('</%s>' % self.name)

    def text(self, s):
        self.savedtext.append(str(s))


class XMLwriter(object):

    def __init__(self, f):
        self.f = f
        self.stack = []
        print >> self.f, '<?xml version="1.0"?>'

    def push(self, name):
        if self.stack:
            self.stack[-1].opentag()
        e = XMLelement(name, self.f, len(self.stack))
        self.stack.append(e)
        return e

    def pop(self):
        self.stack.pop(-1).closetag()

    def pushtext(self, name, value):
        if value:
            e = self.push(name)
            e.text(value)
            self.pop()
