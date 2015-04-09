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

import sys

from cocklebur.form_ui.common import *
from cocklebur.form_ui import elements, inputbase, inputs
from cocklebur import xmlparse

class FormXMLParse(xmlparse.XMLParse):

    root_tag = 'form'

    # Input text attrs
    class Label(xmlparse.SetAttrNode):
        attr = 'label'

    class Summary(xmlparse.SetAttrNode):
        # Deprecated, use <label> instead
        attr = 'summary'

    class Pre_Text(xmlparse.SetAttrNode):
        attr = 'pre_text'

    class Post_Text(xmlparse.SetAttrNode):
        attr = 'post_text'

    class SkipValue(xmlparse.Node):
        subtags = ()
        permit_attrs = ('value',)

        def end_element(self, parent):
            value = self.attrs.get('value', '')
            parent.values.append(value)

    class Skip(xmlparse.Node):
        __slots__ = 'values',
        subtags = ('skipvalue')
        permit_attrs = (
            'mode', 'name', 'values', 'showmsg', 'show_msg', 'skipremaining'
        )

        def start_element(self, parent):
            self.values = []

        def end_element(self, parent):
            not_selected = self.attrs.get('mode') == 'ifnotselected'
            name = self.attrs.get('name')
            if name is None:
                parent.attrs['skip_mode'] = not_selected
            else:
                show_msg = (self.attrs.get('showmsg') or self.attrs.get('show_msg')) != 'no'
                skip_remaining = self.attrs.get('skipremaining') != 'no'
                skip = inputbase.Skip(name, self.values, not_selected,
                                    show_msg=show_msg, 
                                    skip_remaining=skip_remaining)
                parent.skips.append(skip)

    class Choice(xmlparse.Node):
        subtags = ()
        permit_attrs = ('name', 'skipon')

        def end_element(self, parent):
            value = self.attrs.get('name', '')
            label = self.get_text()
            if self.attrs.get('skipon') == 'yes':
                parent.skipon.append(value)
            parent.choices.append((value, label))

    class Choices(xmlparse.Node):
        __slots__ = 'choices', 'skipon'
        subtags = ('choice',)

        def start_element(self, parent):
            self.choices = []
            self.skipon = []

        def end_element(self, parent):
            parent.attrs['choices'] = self.choices
            if self.skipon:
                parent.attrs['skipon'] = tuple(self.skipon)

    class Input(xmlparse.Node):
        __slots__ = 'skips',
        subtags = (
            'choices', 'summary', 'label', 'pre_text', 'post_text', 'skip',
        )
        permit_attrs = (
            'default', 'direction', 'maximum:float', 'maxsize:int', 
            'minimum:float', 'name', 'required:bool', 'skips', 
            'summarise:bool', 'type', 
        )

        def start_element(self, parent):
            self.skips = []

        def end_element(self, parent):
            name = self.attrs.pop('name', None)
            if not name:
                raise xmlparse.ParseError('<input> tag requires a "name" attribute')
            input_type = self.attrs.pop('type', None)
            if not input_type:
                raise xmlparse.ParseError('<input> tag requires a "type" attribute')
            input_cls = getattr(inputs, input_type, None)
            if input_cls is None or input_type not in inputs.__all__:
                raise xmlparse.ParseError('Unknown <input> type %r' % input_type)
            direction = self.attrs.pop('direction', None)
            if direction:
                self.attrs['direction'] = direction
            skip_values = self.attrs.pop('skipon', None)
            if skip_values:
                skip_mode = self.attrs.pop('skip_mode', None)
                self.skips = [inputbase.Skip(name, skip_values, skip_mode)]
            if self.skips:
                self.attrs['skips'] = self.skips
            if 'summary' in self.attrs:
                summary = self.attrs.pop('summary')
                self.attrs['label'] = summary
                self.attrs['summarise'] = bool(summary)
            input = input_cls(name, **self.attrs)
            parent.inputs.append(input)

    class Label(xmlparse.SetAttrNode):
        # Used by question, section and form
        attr = 'label'

    class Help(xmlparse.SetAttrNode):
        # Used by question
        attr = 'help'

    class ExcludeIf(xmlparse.Node):
        # Legacy
        subtags = ()
        permit_attrs = ('name',)

        def end_element(self, parent):
            name = self.attrs.get('name')
            if name:
                parent.triggers.append(name)

    class IncludeIf(xmlparse.Node):
        # Legacy
        subtags = ()
        permit_attrs = ('name',)

        def end_element(self, parent):
            name = self.attrs.get('name')
            if name:
                parent.triggers.append(name)
                parent.attrs['trigger_mode'] = 'enable'

    class Trigger(xmlparse.Node):
        subtags = ()
        permit_attrs = ('name',)

        def end_element(self, parent):
            name = self.attrs.get('name')
            if name:
                parent.triggers.append(name)

    class Question(xmlparse.Node):
        subtags = ('input', 'label', 'help', 'trigger') + \
                    ('excludeif', 'includeif')      # Legacy
        __slots__ = 'inputs', 'triggers'
        permit_attrs = ('disabled:bool', 'trigger_mode')

        def start_element(self, parent):
            self.inputs = []
            self.triggers = []

        def end_element(self, parent):
            label = self.attrs.pop('label', None)
            if self.triggers:
                self.attrs['triggers'] = self.triggers
            question = elements.Question(label, inputs=self.inputs, 
                                         **self.attrs)
            parent.children.append(question)


    class _Section(xmlparse.Node):
        __slots__ = 'children', 
        subtags = ('section', 'label', 'question')

        def start_element(self, parent):
            self.children = []


    class Section(_Section):

        def end_element(self, parent):
            label = self.attrs.pop('label', None)
            section = elements.Section(text=label, **self.attrs)
            for child in self.children:
                section.append(child)
            parent.children.append(section)


    class Form(_Section):
        __slots__ = 'form', 
        permit_attrs = (
            'name', 'form_type', 'allow_multiple:bool', 'update_time', 
            'author', 'username', 
        )

        def end_element(self, parent):
            label = self.attrs.pop('label', None)
            self.form = elements.Form(text=label, **self.attrs)
            for child in self.children:
                self.form.append(child)


def xmlload(f):
    try:
        return FormXMLParse().parse(f).form
    except xmlparse.ParseError, e:
        raise FormParseError, e, sys.exc_info()[2]
