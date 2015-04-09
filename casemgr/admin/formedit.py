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

# Standard lib
try:
    set
except NameError:
    from sets import Set as set
import sys

# App modules
from cocklebur import form_ui, dbobj
from casemgr.admin.questionedit import _boolfix, QuestionEdit, QuestionNameError

class QuestionEditInfo:

    def __init__(self, root, container, question, insert_index=None):
        self.root = root
        self.container = container
        self.question = question
        self.element = None
        if question is not None:
            self.element = question.element
        self.insert_index = insert_index
        self.other_column_names = set()
        self.other_condition_names = set()
        self.section_title = str(container.text)
        self.condition_renames = {}
        if len(self.section_title) > 30:
            self.section_title = self.section_title[:30] + '...'

    def sorted_condition_names(self):
        names = list(self.other_condition_names)
        names.sort()
        return names

    def reset_question_names(self):
        self.question_column_names = set()
        self.question_condition_names = set()

    def check_column_name(self, name):
        if name in self.other_column_names:
            raise QuestionNameError('field name %r already used by another '
                                    'question' % name)
        elif name in self.question_column_names:
            raise QuestionNameError('field name %r used more than once in '
                                    'this question' % name)
        try:
            dbobj.valid_identifier(name)
        except dbobj.DatabaseError, e:
            raise QuestionNameError('field name: %s' % e)
        self.question_column_names.add(name)

    def check_condition_name(self, name):
        if name in self.other_condition_names:
            raise QuestionNameError('condition name %r already used by another '
                                    'question' % name)
        elif name in self.question_condition_names:
            raise QuestionNameError('condition name %r used more than once in '
                                    'this question' % name)
        self.question_condition_names.add(name)

    def condition_rename(self, old, new):
        self.condition_renames[old] = new

    def _question_rename_conditions(self, question):
        question.element.triggers = [self.condition_renames.get(n, n)
                                     for n in question.element.triggers]

    def commit(self, element):
        if self.insert_index is not None:
            self.question = Question(element)
            self.container.insert(self.insert_index, self.question)
        else:
            self.question.set_element(element)
            self.question.element.label = self.question.get_label()
        self.question.changed = True
        self.root.walk_questions(self._question_rename_conditions)
        self.root.update_xlinks()
        return self.question


class SectionEdit:

    def __init__(self, parent, section=None, insert_index=None):
        self.parent = parent
        self.insert_index = insert_index
        if section is None:
            section = Container()
            self.parent.insert(insert_index, section)
        self.node = section
        self.text = self.node.text

    def commit(self):
        self.node.text = self.text

    def rollback(self):
        if self.insert_index is not None:
            self.parent.remove(self.node)


class Node(object):

    node_type = None

    def __init__(self):
        pass

    def clear_changed(self):
        pass

    def has_changed(self):
        return False

    def update_path(self, path=None):
        if path is not None:
            self.path = path

    def id(self):
        return self.node_type[0].upper() + self.path

    def get_label(self):
        # quick and dirty hack to transform path into a human readable label
        path = [str(int(pc)+1) for pc in self.path.split('_') if pc]
        return '.'.join(path)

    def to_form(self):
        pass

    def collect_edit_info(self, edit_info):
        pass

    def walk_questions(self, fn):
        pass

    def css_class(self):
        styles = [self.node_type, 'selectable']
        if getattr(self, 'disabled', False):
            styles.append('disabled')
        return ' '.join(styles)


class Question(Node):

    node_type = 'question'

    def __init__(self, element):
        Node.__init__(self)
        if element is not None:
            self.set_element(element)

    def set_element(self, element):
        self.element = element
        self.text = element.text
        self.help = element.help
        self.inputs = element.inputs
        self.disabled = element.disabled

    def update_path(self, path=None):
        Node.update_path(self, path)
        self.element.label = self.get_label()

    def skiptext(self):
        return self.element.skiptext()

    def clear_changed(self):
        self.changed = False

    def has_changed(self):
        return self.changed

    def to_form(self):
        return self.element    

    def collect_edit_info(self, edit_info):
        for input in self.element.inputs:
            edit_info.other_column_names.update(input.get_column_names())
            # Ultimately, this will be the skip name, not the column name, and
            # an input will potentially have more than on skip.
            for skip in input.skips:
                edit_info.other_condition_names.add(skip.name)

    def walk_questions(self, fn):
        fn(self)


class EndContainer(Node):

    node_type = 'end'


class Container(Node):

    node_type = 'section'

    def __init__(self, container_element=None, text=''):
        Node.__init__(self)
        self.path = None
        self.children = []
        self.text = text
        if container_element is not None:
            self.text = container_element.text
            for element in container_element.children:
                if hasattr(element, 'children'):
                    node = Container(element)
                else:
                    node = Question(element)
                self.children.append(node)
        self.children.append(EndContainer())

    def has_changed(self):
        if self.initial_text != self.text or self.changed:
            return True
        for child in self.children:
            if child.has_changed():
                return True
        return False

    def clear_changed(self):
        self.initial_text = self.text
        self.changed = False
        for child in self.children:
            child.clear_changed()

    def to_form(self, cls=form_ui.Section):
        section = cls(self.text)
        for content in self.children:
            child = content.to_form()
            if child is not None:
                section.append(child)
        return section

    def update_path(self, path=None):
        Node.update_path(self, path)
        for i, child in enumerate(self.children):
            if self.path:
                path = '%s_%d' % (self.path, i)
            else:
                path = '%d' % i
            child.update_path(path)

    def remove(self, child):
        i = self.children.index(child)
        del self.children[i]
        self.changed = True
        self.update_path()

    def replace(self, index, node):
        self.children[index] = node
        self.changed = True
        self.update_path()

    def insert(self, index, node):
        self.children.insert(index, node)
        self.changed = True
        self.update_path()

    def collect_edit_info(self, edit_info):
        for child in self.children:
            if child is not edit_info.question:
                child.collect_edit_info(edit_info)

    def walk_questions(self, fn):
        for child in self.children:
            child.walk_questions(fn)


class Root(Container):

    form_types = 'case', 'contact'

    def __init__(self, root):
        Container.__init__(self, root) 
        self.allow_multiple = root.allow_multiple
        self.form_type = root.form_type
        self.update_time = root.update_time
        self.update_path('')
        self.update_xlinks()    # Not strictly necessary, but good for testing
        self.clear_changed()
        self.changed = True

    def clear_changed(self):
        Container.clear_changed(self)
        self.changed = False
        self.allow_multiple_orig = _boolfix(self.allow_multiple)
        self.form_type_orig = self.form_type

    def has_changed(self):
#        print >> sys.stderr, repr(self.allow_multiple_orig), repr(_boolfix(self.allow_multiple)), repr(self.form_type_orig), repr(self.form_type)
        if (self.allow_multiple_orig != _boolfix(self.allow_multiple) or
            self.form_type_orig != self.form_type or self.changed):
            return True
        return Container.has_changed(self)

    def to_form(self, name=None):
        form = Container.to_form(self, cls=form_ui.Form)
        if _boolfix(self.allow_multiple):
            form.allow_multiple = True
        if self.form_type:
            form.form_type = self.form_type
        if name:
            form.name = name
        return form

    def find_node(self, path):
        path = path[1:]
        if path:
            nodes = [self]
            for index in path.split('_'):
                nodes.append(nodes[-1].children[int(index)])
            return nodes[-2:]
        else:
            return None, self

    def update_xlinks(self):
        helper = form_ui.XlinkHelper()
        self.walk_questions(lambda q: q.element.update_xlinks(helper))

    def new_question(self, path):
        parent, insert_node = self.find_node(path)
        insert_index = parent.children.index(insert_node)
        edit_info = QuestionEditInfo(self, parent, None, insert_index)
        self.collect_edit_info(edit_info)
        return QuestionEdit(edit_info)

    def edit_question(self, path):
        parent, question = self.find_node(path)
        edit_info = QuestionEditInfo(self, parent, question)
        self.collect_edit_info(edit_info)
        return QuestionEdit(edit_info)

    def new_section(self, path):
        parent, insert_node = self.find_node(path)
        insert_index = parent.children.index(insert_node)
        return SectionEdit(parent, None, insert_index)

    def edit_section(self, path):
        parent, section = self.find_node(path)
        return SectionEdit(parent, section)

    def copy(self, paths):
        if paths == 'S':
            cut_buffer = self.to_form()
        else:
            cut_buffer = form_ui.Form(None)
            for pathname in paths.split(','):
                parent, node = self.find_node(pathname)
                formnode = node.to_form()
                if formnode is not None:
                    cut_buffer.append(formnode)
        return cut_buffer

    def cut(self, paths):
        cut_buffer = self.copy(paths)
        if paths == 'S':
            del self.children[:-1]
            self.changed = True
        else:
            for pathname in paths.split(',')[::-1]:
                parent, node = self.find_node(pathname)
                parent.remove(node)
        return cut_buffer

    def paste(self, pathname, cut_buffer):
        fragment = Container(cut_buffer)
        parent, insert_before = self.find_node(pathname)
        insert_index = parent.children.index(insert_before)
        parent.children[insert_index:insert_index] = fragment.children[:-1]
        parent.changed = True
        parent.update_path()
