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

try:
    set
except NameError:
    from sets import Set as set
import sys
import os
import signal
import errno
import tempfile

from cocklebur import trafficlight
from cocklebur.exepath import exepath
from casemgr import globals, caseaccess, syndrome
from casemgr.reports.common import *

import config

vismodes = [
    ('fdp', 'Radial (fdp)'),
    ('neato', 'Radial (neato)'),
    ('twopi', 'Radial (twopi)'),
    ('circo', 'Circular (circo)'),
    ('dot', 'Hierarchial (dot)'),
]
okay_modes = set([name for name, label in vismodes])

MAX_NODES = 600
MAX_VERTICES = 1000


class Error(globals.Error): pass

_have_graphviz = None
def have_graphviz():
    global _have_graphviz
    if _have_graphviz is None:
        _have_graphviz = bool(exepath('dot') or exepath('twopi'))
    return _have_graphviz


TIMEOUT = 20

def run_graphviz(dot, vismode, outputtype, outputdir=None, filename=None):
    path = None
    if vismode in okay_modes:
        path = exepath(vismode)
    if not path:
        raise Error('Visualisation tool %r not found' % vismode)
    if filename:
        tw = os.open(filename, os.O_CREAT|os.O_WRONLY, 0666)
        fn = filename
    else:
        tw, fn = tempfile.mkstemp('.' + outputtype, 'vis', outputdir)
    pr, pw = os.pipe()
    pid = os.fork()
    if pid:
        # Parent
        os.close(pr)
        os.write(pw, dot)
        os.close(pw)
        signal.signal(signal.SIGALRM, lambda s, f: None)
        signal.alarm(TIMEOUT)
        try:
            wpid, status = os.waitpid(pid, 0)
        except OSError, (eno, estr):
            if eno == errno.EINTR:
                os.kill(pid, signal.SIGKILL)
                raise Error('Graph generation took long than %s seconds - '
                            'reduce the number of cases or try another '
                            'visualisation mode - hierarchial (dot) may work' %
                            TIMEOUT)
            raise
        if status == 0:
            return os.path.basename(fn)
        raise Error('Graphviz %r failed' % path)
    else:
        os.close(pw)
        os.dup2(pr, 0)
        os.dup2(tw, 1)
        os.close(pr)
        os.close(tw)
        try:
            os.execl(path, vismode, '-T' + outputtype)
        except OSError, (eno, estr):
            sys.exit('%s: %s' % (path, estr))


class Person:

    def __init__(self, *args):
        self.case_ids = set()
        self.statuses = set()
        self.label = ''


class Collect:

    def __init__(self, db, cred, person_cols,
                 syndrome_id=None, case_ids=None):
        self.relations = set()
        self.case_persons = {}
        self.persons = {}
        self.short_labels = not person_cols
        self.to_syndcs = {}
        self.syndcs_label = {}
        self.syndcs_color = {}
        used_syndcs = set()
        query = db.query('syndrome_case_status')
        cols = 'syndcs_id', 'syndrome_id', 'name', 'label'
        for syndcs_id, syndrome_id, name, label in query.fetchcols(cols):
            self.to_syndcs[(syndrome_id, name)] = syndcs_id
            self.syndcs_label[syndcs_id] = label
        query = db.query('cases')
        caseaccess.acl_query(query, cred)
        query.join('JOIN case_contacts USING (case_id)')
        if case_ids is not None:
            subquery = query.sub_expr('OR')
            subquery.where_in('case_id', case_ids)
            subquery.where_in('contact_id', case_ids)
        elif syndrome_id is not None:
            query.where('syndrome_id = %s', syndrome_id)
        cols = 'syndrome_id','person_id','case_id','contact_id','case_status'
        self.persons = {}
        for syndrome_id, person_id, case_id, contact_id, status in query.fetchcols(cols):
            try:
                person = self.persons[person_id]
            except KeyError:
                person = self.persons[person_id] = Person()
            person.case_ids.add(case_id)
            syndcs = self.to_syndcs.get((syndrome_id, status))
            if syndcs is not None:
                person.statuses.add(syndcs)
                used_syndcs.add(syndcs)
            self.case_persons[case_id] = person_id
            if case_id < contact_id:
                self.relations.add((case_id, contact_id))
            else:
                self.relations.add((contact_id, case_id))
        if len(self.persons) > MAX_NODES:
            raise Error('Sorry, this facility only supports < %d %s (%d required)' % (MAX_NODES, config.person_label, len(self.persons)))
        if len(self.relations) > MAX_VERTICES:
            raise Error('Sorry, this facility only supports < %d relations (%d required)' % (MAX_VERTICES, len(self.relations)))
        if self.persons:
            query = db.query('persons')
            query.where_in('person_id', self.persons.keys())
            for row in query.fetchcols(['person_id'] + list(person_cols)):
                person = self.persons[row[0]]
                person.label = '\\n'.join(map(str, row[1:]))
        used_syndcs = list(used_syndcs)
        used_syndcs.sort()
        colors = trafficlight.make_n_colors(len(used_syndcs))
        for color, syndcs in zip(colors, used_syndcs):
            self.syndcs_color[syndcs] = color
        self.syndcs_color[None] = '#dddddd';

    def generate_dot(self, vismode, title='Case %ss' % config.contact_label):
        lines = []
        lines.append('graph appname {')
        lines.append('splines=true;')
        lines.append('overlap=false;')
        lines.append('node [shape=circle, style=filled];')
        if self.short_labels:
            lines.append('node [fontsize=8, height=.8, width=.8, fixedsize=1];')
        else:
            lines.append('node [fontsize=6, height=.8, width=.8, fixedsize=1];')
        # Legend
        # Only dot and fdp seem to support clustered subgraphs - twopi and
        # neato just render the nodes in random places.
        if vismode in ('dot', 'fdp'):
            lines.append('subgraph cluster_0 {')
            lines.append('style=filled;')
            lines.append('label="Legend";')
            lines.append('bgcolor="#eeeeee";')
            for syndcs, color in self.syndcs_color.iteritems():
                lines.append('node [fillcolor="%s"];' % color)
                lines.append('  X%s [label="%s"];' % (syndcs, self.syndcs_label.get(syndcs, 'unknown')))
            lines.append('}')
        # Sort by status
        person_by_status = {}
        for person_id, person in self.persons.iteritems():
            statuses = list(person.statuses)
            if statuses:
                if len(statuses) > 1:
                    statuses.sort()
                status = statuses[-1]
            else:
                status = None
            try:
                status_persons = person_by_status[status]
            except KeyError:
                status_persons = person_by_status[status] = []
            status_persons.append((person_id, person))
        # Nodes (persons)
        for syndcs, status_persons in person_by_status.iteritems():
            lines.append('node [fillcolor="%s"];' % self.syndcs_color[syndcs])
            for person_id, person in status_persons:
                case_ids = list(person.case_ids)
                case_ids.sort()
                if len(case_ids) > 2:
                    case_ids = case_ids[:2] + ['...']
                case_ids = ','.join([str(id) for id in case_ids])
                lines.append('  %s [label="%s\\n%s"];' % (person_id, 
                                                        case_ids,
                                                        person.label))
        # Edges (contact)
        lines.append('edge [style=bold,weight=1]')
        for case_id, contact_id in self.relations:
            try:
                person_a = self.case_persons[case_id]
                person_b = self.case_persons[contact_id]
            except KeyError:
                continue
            lines.append('  %s -- %s;' % (person_a, person_b))
        lines.append('label="%s";' % title)
        lines.append('}')
        return '\n'.join(lines)


class ContactVisParamsMixin:

    show_contactvis = True

    vismode = 'fdp'
    outputtype = 'png'
    labelwith = 'surname,given_names'

    _vismodes = None
    def vismode_options(self):
        if self._vismodes is None:
            # Cache these on the class
            ContactVisParamsMixin._vismodes = [(name, label)
                                               for name, label in vismodes
                                               if exepath(name)]
        return self._vismodes

    def labelwith_options(self):
        return [
            ('surname,given_names', 'System ID, Surname, Given Names'),
            ('', 'System ID'),
            ('locality,state', 'System ID, Locality, State'),
        ]

    def outputtype_options(self):
        return [
            ('png', 'PNG'),
            ('svg', 'SVG'),
            ('pdf', 'PDF'),
            ('ps', 'Postscript'),
        ]

    def get_prefs(self, credentials):
        params = credentials.prefs.get('contact_viz')
        if params and isinstance(params, dict):
            # params was briefly a tuple, hence the isinstance check
            self.__dict__.update(params)

    def update_prefs(self, credentials):
        params = dict(vismode=self.vismode, 
                      outputtype=self.outputtype, 
                      labelwith=self.labelwith)
        credentials.prefs.set('contact_viz', params)

    def _defaults(self, msgs):
        if not have_graphviz():
            msgs.msg('err', '%s not available on this system (GraphViz not '
                            'installed?)' % self.type_label)

    def _check(self, msgs):
        okay_modes = set([name for name, label in self.vismode_options()])
        if self.vismode not in okay_modes:
            msgs.msg('err', 'Visualisation tool %r not available (GraphViz not '
                            'installed?)' % self.vismode)

    def report(self, creds, msgs, filename=None):
        self.check(msgs)
        if msgs.have_errors():
            return
        labelwith = ()
        if self.labelwith:
            labelwith = self.labelwith.split(',')
        if not self.vismode:
            self.vismode = self.vismode_options()[0][0]
        case_ids = self.get_case_ids(creds)
        data = Collect(globals.db, creds, labelwith, case_ids=case_ids)
        dot_script = data.generate_dot(self.vismode, title=self.title(creds)) 
        if filename:
            outputtype = os.path.splitext(filename)[1][1:] or self.outputtype
        else:
            outputtype = self.outputtype
        return ImageReport(run_graphviz(dot_script, self.vismode, 
                                        outputtype, config.scratchdir,
                                        filename=filename))

    def _to_xml(self, xmlgen, curnode):
        e = xmlgen.push('contactvis')
        e.attr('format', self.outputtype)
        e.attr('labelwith', self.labelwith)
        e.attr('vismode', self.vismode)
        xmlgen.pop()
