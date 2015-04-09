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
import os
import re
import time
import optparse

try:
    from lxml.etree import iterparse, dump
except ImportError, e:
    sys.exit('required python module "lxml" not found\n   see http://codespeak.net/lxml/\n    %s' % e)

from cocklebur import dbobj
from casemgr import cases, globals, syndrome, form_summary
from casemgr.cmdline import cmdcommon

class TagError(Exception): pass

datasrc = 'lab_hl7'

def copy_node(node, ns):
    for tag in node.getchildren():
        value = tag.text
        if value:
            value = value.strip()
        if value and hasattr(ns, tag.tag):
            setattr(ns, tag.tag, value)


class FormDataImpCache(dict):

    def get(self, syndrome_id, name, data_src):
        key = syndrome_id, name
        try:
            return self[key]
        except KeyError:
            formdataimp = form_summary.FormDataImp(syndrome_id, name, data_src)
            self[key] = formdataimp
            return formdataimp
            
formdataimpcache = FormDataImpCache()


class SyndromeCache(dict):

    def __init__(self, default_syndrome=None):
        if default_syndrome:
            self[None] = self.find_syndrome(default_syndrome)

    def find_syndrome(self, pattern):
        try:
            return self[pattern]
        except KeyError:
            if pattern is None:
                cmdcommon.abort('No default syndrome specified')
            patre = re.compile(pattern, re.I)
            matches = [synd for synd in syndrome.syndromes
                       if patre.match(synd.name) is not None]
            if not matches:
                cmdcommon.abort('No syndromes match %r' % pattern)
            if len(matches) > 1:
                names = [synd.name for synd in matches]
                cmdcommon.abort('More than one syndrome name match %r: %s' % 
                         (pattern, ', '.join(names)))
            self[pattern] = matches[0]
            return matches[0]


class Ticker:

    tick_interval = 10

    def __init__(self, entity='records'):
        self.t0 = time.time()
        self.n = 0
        self.entity = entity
        self.next = 10

    def report(self):
        el = time.time() - self.t0
        self.per_second = self.n / el
        print 'Processed %d %s, %.1f per minute' %\
            (self.n, self.entity, self.per_second * 60)
        self.next = self.n + self.per_second * self.tick_interval

    def tick(self):
        self.n += 1
        if self.n >= self.next:
            self.report()

    def __del__(self):
        try:
            self.report()
        except Exception:
            pass


def assert_tag(node, name):
    if node.tag != name:
        raise TagError('Expected a <%s> tag, not <%s>' % (name, node.tag))

def want_elem(node, name):
    subnode = node.find(name)
    if subnode is None:
        raise TagError('No <%s> tag found' % (name))
    return subnode


def proc_forms(options, synd, case, case_elem):
    forms_elem = want_elem(case_elem, 'Forms')
    assert_tag(forms_elem, 'Forms')
    for form_elem in forms_elem.getchildren():
        assert_tag(form_elem, 'Form')
        form_name = form_elem.get('name')
        try:
            formdataimp = formdataimpcache.get(synd.syndrome_id, form_name, 
                                               options.data_src)
        except form_summary.form_ui.FormError:
            raise TagError('Can\'t find %r form for syndrome %d: %s' % (form_name, synd.syndrome_id, synd.name))
        edit_form, form_data = formdataimp.edit(case.case_row.case_id)
        copy_node(form_elem, form_data)
        edit_form.update()


def proc_cases(options, cred, cases):
    """
    Case-based import - single <Person> element contained within each <Case>
    """
    ticker = Ticker('cases')
    for case_elem in cases:
        try:
            assert_tag(case_elem, 'Case')
            person_elem = want_elem(case_elem, 'Person')
            synd = find_syndrome(case_elem.get('syndrome'))
            case = cases.new_case(cred, synd.syndrome_id)
            copy_node(person_elem, case.person)
            case.person.data_src = options.data_src
            case.update()
            proc_forms(options, synd, case, case_elem)
        except Exception, e:
            dump(case_elem)
            raise
            cmdcommon.abort(e)
        ticker.tick()
    globals.db.commit()


def proc_persons(options, cred, persons):
    """
    Person-based import - one or more <Case> elements inside a <Cases>
    element inside each <Person>
    """
    ticker = Ticker('cases')
    for person_elem in persons:
        try:
            assert_tag(person_elem, 'Person')
            cases_elem = want_elem(person_elem, 'Cases')
            person_id = None
            for case_elem in cases_elem.getchildren():
                assert_tag(case_elem, 'Case')
                synd = find_syndrome(case_elem.get('syndrome'))
                case = cases.new_case(cred, synd.syndrome_id, 
                                      use_person_id=person_id)
                if person_id is None:
                    copy_node(person_elem, case.person)
                    case.person.data_src = options.data_src
                case.update()
                if person_id is None:
                    person_id = case.case_row.person_id
                proc_forms(options, synd, case, case_elem)
                ticker.tick()
        except Exception, e:
            dump(person_elem)
            raise
            cmdcommon.abort(e)
    globals.db.commit()


def main(args):
    global find_syndrome

    optp = optparse.OptionParser(
        usage='usage: %prog xmlimport [options] <xmlfile>')
    cmdcommon.opt_syndrome(optp)
    cmdcommon.opt_user(optp)
    optp.add_option('-d', '--data-src', default='xmlimport',
                    help='Set data source to DATA_SRC')
    options, args = optp.parse_args(args)

    try:
        xmlfile, = args
    except ValueError:
        optp.error('exactly 1 argument needed')

    cred = cmdcommon.user_cred(options)

    find_syndrome = SyndromeCache(options.syndrome).find_syndrome

    context = iter(iterparse(open(xmlfile), events=('start','end')))
    event, root = context.next()

    def yield_nodes(nodename):
        for event, elem in context:
            if event == 'end' and elem.tag == nodename:
                yield elem
                root.clear()

    if root.tag == 'Cases':
        proc_cases(options, cred, yield_nodes('Case'))
    elif root.tag == 'Persons':
        proc_persons(options, cred, yield_nodes('Person'))
    else:
        cmdcommon.abort('Root of XML tree is not a <Cases> tag nor <Persons> tag')


if __name__ == '__main__':
    main(sys.argv[1:])
