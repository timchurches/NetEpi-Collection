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
This logic collects metadata about questions to enable client-side skips
(and potentially verification, etc).
"""

class JSSkip:
    def __init__(self, name):
        self.name = name
        self.question = None
        self.inverted = False
        self.targets = []
        self.inputs = []

    def set_params(self, question, inverted):
        self.question = question
        self.inverted = inverted

    def add_input(self, input, values):
        assert isinstance(input, basestring)
        self.inputs.append((input, list(values)))

    def to_js(self, indent):
        inputs_text = ['%s{name: %r, values: %r}' % (indent * 3, name, values)
                       for name, values in self.inputs]
        skip_text = []
        skip_text.append('name: %r' % self.name)
        skip_text.append('question: %r' % self.question)
        skip_text.append('targets: %r' % self.targets)
        skip_text.append('inverted: %s' % str(bool(self.inverted)).lower())
        skip_text.append('inputs: [\n%s\n%s]' % 
                            (',\n'.join(inputs_text), indent * 2))
        skip_text = ['%s%s' % (indent * 2, l) for l in skip_text]
        return '{\n%s}' % (',\n'.join(skip_text))

    def add_target(self, name):
        self.targets.append(name)


class JSSkips:
    def __init__(self):
        self.skips = []
        self.skips_by_name = {}

    def get(self, name):
        try:
            skip = self.skips_by_name[name]
        except KeyError:
            skip = self.skips_by_name[name] = JSSkip(name)
            self.skips.append(skip)
        return skip

    def to_js(self, indent='  '):
        s_text = []
        for skip in self.skips:
            if skip.question:
                s_text.append('%s%s' % (indent, skip.to_js(indent)))
        return 'form_skips = [\n%s\n];\n' % (',\n'.join(s_text))


class JSQuestion:
    def __init__(self, label, trigger_mode, skips):
        self.label = label
        self.trigger_mode = trigger_mode
        self.skips = skips
        self.inputs = []
        self.has_error = False
        self.has_triggers = False

    def add_inputs(self, inputs):
        self.inputs.append(inputs)

    def input_skip(self, name, input, values, inverted, skip_remaining):
        """ One input with potentially multiple values """
        skip = self.skips.get(name)
        skip.set_params(self.label, inverted)
        if skip_remaining:
            skip.add_target(self.label)
        self.has_triggers = True
        skip.add_input(input, values)

    def inputs_skip(self, name, inputs, inverted, skip_remaining):
        """ Multiple inputs with boolean values (checkbox) """
        skip = self.skips.get(name)
        skip.set_params(self.label, inverted)
        if skip_remaining:
            skip.add_target(self.label)
        self.has_triggers = True
        for input in inputs:
            skip.add_input(input, ['True'])

    def trigger(self, name):
        self.skips.get(name).add_target(self.label)
        self.has_triggers = True

    def to_js(self, indent):
        if not self.has_triggers and not self.has_error:
            return None
        q_fields = [
            'name: %r' % self.label,
            'trigger_mode: %r' % self.trigger_mode,
            'inputs: %r' % self.inputs,
        ]
        if self.has_error:
            q_fields.append('error: true')
        q_fields = [indent * 2 + f for f in q_fields] 
        return '%s%r: {\n%s\n%s}' % \
                    (indent, self.label, ',\n'.join(q_fields), indent)
    

class JSMeta:
    def __init__(self):
        self.questions = []
        self.skips = JSSkips()

    def question(self, label, trigger_mode):
        question = JSQuestion(label, trigger_mode, self.skips)
        self.questions.append(question)
        return question

    def to_js(self):
        indent = '  '
        output = ['\n']
        q_text = []
        for question in self.questions:
            js = question.to_js(indent)
            if js:
                q_text.append(js)
        output.append('form_data_version = 1\n')
        output.append('form_questions = {\n%s\n};\n' % (',\n'.join(q_text)))
        output.append(self.skips.to_js(indent))
        return ''.join(output)
