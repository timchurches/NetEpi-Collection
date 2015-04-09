#
# Copyright (C) 2005, Object Craft P/L, Melbourne, Australia.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
# 
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
# 
#     * Neither the name of Object Craft nor the names of its contributors
#       may be used to endorse or promote products derived from this
#       software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
# TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
"""
A crude HTML parser that attempts to filter unsafe elements

We build a parse tree, and chop off any nodes that correspond to unsafe
tags, such as applet, frame, script, style.

We also ignore any unsafe attributes on otherwise safe tags, such as any
of the on* attributes, src, etc.

This isn't 100% safe - in particular, I may have overlooked some way
of sneaking hostile content through, or the parsing engine may get out
of sync and not recognise as HTML something the browser does recognise.

$Id: safehtml.py 1804 2006-05-29 06:15:19Z andrewm $
$Source$
"""
import re

debug = 0

_sre_dblquote_nogrp = r'"(?:[^"\\]*(?:\\.[^"\\]*)*)"'   # eg, "hello \"bill\""
_sre_sglquote_nogrp = r"'(?:[^'\\]*(?:\\.[^'\\]*)*)'"   # eg, 'sam\'s ball'
_sre_attr = r'(?:' + \
    r'\s+\w+=' + _sre_dblquote_nogrp + '|' + \
    r'\s+\w+=' + _sre_sglquote_nogrp + '|' + \
    r'\s+\w+=[^ >]+|' + \
    r'\s+\w+' + ')'                                     # eg, attr="value"
_sre_attrs = r'(' + _sre_attr + r'*)'                   # eg, a1="v1" a2="v2"
_sre_tag = r'<(/?\w+)' + _sre_attrs + r'\s*(/?>)'       # a full tag
_re_tag = re.compile(_sre_tag, re.I|re.M|re.S)

_sre_attr_grp = r'(\w+)=('+_sre_dblquote_nogrp+'|'+_sre_sglquote_nogrp+'|(?:[^ >]+))|(\w+)'
_re_attrib = re.compile(_sre_attr_grp, re.I|re.M)

_re_dequote = re.compile(r'\\(.)')

class Node:
    name = ''
    def __init__(self):
        self.content = []

    def add_content(self, n):
        self.content.append(n)

    def is_empty(self):
        return 0

    def is_named(self, name):
        return self.name == name


class Text(Node):
    bad_entity_re = re.compile(r'&(?!#?[a-zA-Z0-9]{2,7};)|[<>]')

    def __init__(self, text):
        self.text = text

    def to_html(self, out):
        def replace(match):
            return {'&': '&amp;', '<': '&lt;', '>': '&gt;'}[match.group(0)] 
        out(self.bad_entity_re.sub(replace, self.text))

class Root(Node):
    def to_html(self, out):
        for c in self.content:
            c.to_html(out)

    def is_block(self):
        return 1

class Tag(Node):
    # Any tags other than these, we junk them and their contents
    tag_allow_list = [
        # Some of these are particular badies (style, exe content):
        # 'applet', 'button', 'frame', 'iframe', 'link', 'frameset', 'object',
        # 'param', 'script', 'style', 'title', 'meta'
        #
        # No need for forms in this context
        # 'form', 'input', 'select', 'map',

        'a', 'abbr', 'acronym', 'address', 'area', 'b', 'base', 'bdo', 'big',
        'br', 'caption', 'center', 'cite', 'code', 'col', 'dd', 'del',
        'dfn', 'dir', 'div', 'dl', 'dt', 'em', 'font', 'h1', 'h2',
        'h3', 'h4', 'h5', 'h6', 'head', 'hr', 'i', 'img', 
        'ins', 'kbd', 'label', 'legend', 'li', 
        'menu', 'ol', 'option', 'p', 'pre', 'q', 's', 'samp', 
        'small', 'span', 'strike', 'strong', 'sub', 'sup', 'table', 'tbody',
        'td', 'tfoot', 'th', 'thead', 'tr', 'tt', 'u', 'ul', 'var'
    ]
    tag_allow = dict([(v, None) for v in tag_allow_list])

    # For these tags, we ignore the tag, but generate contents
    tag_ignore_list = [
        'html', 'head', 'body',
    ]
    tag_ignore = dict([(v, None) for v in tag_ignore_list])

    # These are the attributes we allow - mainly we're screening attrs that
    # automatically follow URL's, or have executable content.
    attrs_allow_list = [
        # 'target',
        'abbr', 'accept-charset', 'accept', 'accesskey', 'action', 'align',
        'alink', 'alt', 'axis', 'bgcolor', 'border', 'cellpadding',
        'cellspacing', 'char', 'charoff', 'charset', 'checked', 'clear',
        'color', 'cols', 'compact', 'coords', 'datetime', 'dir', 'disabled',
        'enctype', 'face', 'for', 'headers', 'height', 'href', 'hspace',
        'http-equiv', 'id', 'ismap', 'label', 'lang', 'link', 'longdesc',
        'marginheight', 'marginwidth', 'maxlength', 'method', 'multiple',
        'name', 'nohref', 'noshade', 'nowrap', 'prompt', 'readonly', 'rows',
        'rowspan', 'rules', 'scope', 'selected', 'shape', 'size', 'span',
        'src', 'start', 'summary', 'tabindex', 'text', 'title', 'type',
        'valign', 'value', 'version', 'vlink', 'width',
    ]
    attrs_allow  = dict([(v, None) for v in attrs_allow_list])

    # Block level tags
    block_tag_list = [
        'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'dl', 'dir',
        'menu', 'pre', 'listing', 'xmp', 'plaintext', 'address', 'blockquote',
        'form', 'isindex', 'fieldset', 'table', 'hr', 'div', 'multicol',
        'nosave', 'layer', 'align', 'center', 'noframes', 'area',
        'html', 'head', 'title', 'body',
    ]
    block_tag  = dict([(v, None) for v in block_tag_list])

    # These attrs don't have any contents, so we can assume them to be
    # complete immediately.
    empty_list = [
        'area', 'base', 'basefont', 'br', 'col', 'frame', 'hr', 'img',
        'input', 'isindex', 'link', 'meta', 'param',
    ]
    empty  = dict([(v, None) for v in empty_list])

    def __init__(self, name):
        Node.__init__(self)
        self.name = name
        self.attrs = []
        self.bad = not self.tag_allow.has_key(self.name)
        self.ignore = self.tag_ignore.has_key(self.name)
        self.is_complete = 0

    def is_named(self, name):
        return self.name == name

    def is_empty(self):
        return self.empty.has_key(self.name)

    def is_block(self):
        return self.block_tag.has_key(self.name)

    def set_attrs(self, attrs):
        self.attrs = []
        if self.bad:
            return
        bits = _re_attrib.split(attrs)
        offset = 0
        while 1:
            attrbits = bits[offset: offset + 4]
            if len(attrbits) < 4:
                break
            offset = offset + 4
            white, name1, value, name2 = attrbits
            if name1:
                name = name1.lower()
            else:
                name = name2.lower()
                value = None
            if self.attrs_allow.has_key(name):
                self.attrs.append((name, value))
        if self.name == 'a':
            self.attrs.append(('target', '"_blank"'))

    def complete(self):
        self.is_complete = 1

    def to_html(self, out):
        if self.bad:
            return
        if self.ignore:
            for c in self.content:
                c.to_html(out)
        else:
            out('<' + self.name)
            for name, value in self.attrs:
                if value != None:
                    out( ' ' + name + '=' + value)
                else:
                    out( ' ' + name)
            if not self.content:
                out( ' />')
            else:
                out( '>')
                for c in self.content:
                    c.to_html(out)
                if self.is_complete:
                    out( '</' + self.name + '>')

def parse(src_html):
    TEXT, TAG, ATTR, CLOSE = range(4)
    state = TEXT
    root = Root()
    node_stack = [root]
    for part in _re_tag.split(src_html):
        if debug: print state, part, node_stack[0].name
        if state == TEXT:
            if part:
                node_stack[0].add_content(Text(part))
            state = TAG
        elif state == TAG:
            tag_name = part.lower()
            closing = (tag_name[0] == '/')
            if not closing:
                tag = Tag(tag_name)
                if tag.is_block():
                    if debug: print "  block tag"
                    if node_stack[0].is_named(tag_name):
                        # Block tag can't contain itself
                        node_stack.pop(0).complete()
                    while not node_stack[0].is_block():
                        if debug: print "   pop inline", node_stack[0].name
                        node_stack.pop(0).complete()
                node_stack.insert(0, tag)
                node_stack[1].add_content(tag)
            else:
                tag_name = tag_name[1:]
                complete = []
                while node_stack:
                    complete.append(node_stack.pop(0))
                    if complete[-1].is_named(tag_name):
                        break
                if not node_stack:
                    node_stack = complete
                elif complete:
                    complete[-1].complete()
            state = ATTR
        elif state == ATTR:
            if part and not closing:
                node_stack[0].set_attrs(part)
            state = CLOSE
        elif state == CLOSE:
            if part[0] == '/' or node_stack[0].is_empty():
                node_stack.pop(0).complete()
            state = TEXT
    return root


def safehtml(src_html):
    class Output:
        def __init__(self):
            self.output = []

        def add(self, s):
            self.output.append(s)

        def flush(self):
            return ''.join(self.output)
            self.output = []

    output = Output()
    tree = parse(src_html)
    tree.to_html(output.add)
    return output.flush()
