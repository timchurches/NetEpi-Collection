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
import sys, os
import fnmatch
import shelve
import cPickle as pickle

from optparse import OptionParser, OptionGroup
from UserDict import UserDict

from casemgr import globals, exportselect
from casemgr.syndrome import UnitSyndromesView
from casemgr import tasks
from casemgr.cmdline import cmdcommon


ourname = os.path.basename(sys.argv[0])

def get_option_parser():
    """
    Create the option parser for the script
    """
    usage = '%prog [options] <form_id> <form_id> ... (use ? for a list)'
    optp = OptionParser(usage=usage)
    cmdcommon.opt_user(optp)

    optg = OptionGroup(optp, 'Queue options')
    optg.add_option('--queue-field', metavar='FIELD',
            help='field containing the destination task queue name')
    optg.add_option('-Q', '--queue-mapping', metavar='VALUE::QUEUE',
            help='a mapping from a queue field value to a task queue name')
    optg.add_option('-T', '--default-queue', metavar='QUEUE',
            help='the default task queue name') 
    optp.add_option_group(optg)

    optg = OptionGroup(optp, 'Cache options')
    optg.add_option('-S', '--state-file', default=None, metavar='FILENAME',
            help='keep state in FILENAME') 
    optg.add_option('-m', '--monitor-field', dest='monitored_fields',
            default=[], action='append', metavar='FIELD',
            help='field to watch (may be specified multiple times)') 
    optp.add_option_group(optg)

    optg = OptionGroup(optp, 'Export options')
    cmdcommon.opt_syndrome(optg)
    optg.add_option('--exclude-deleted', dest='include_deleted',
            action='store_false',
            help='exclude deleted records from output (default)')
    optg.add_option('--include-deleted', dest='include_deleted',
            default=False, action='store_const', const='', 
            help='include deleted records in output')
    optg.add_option('--only-deleted', dest='include_deleted',
            action='store_true',
            help='include only deleted records in output')
    optg.add_option('--scheme', dest='export_scheme',
            default='classic', metavar='SCHEME',
            help='export using SCHEME [default: %default]. Use "?" '
                 'to see a list of available schemes.') 
    optp.add_option_group(optg)

    return optp


def print_indexed_list(indexed_list, title=None):
    if title:
        print title
    maxlen = max([ len(str(i[0])) for i in indexed_list ])
    indexed_list = [ (name, label) for (label, name) in indexed_list ]
    indexed_list.sort()
    fmt = "%%%ds: %%s" % maxlen
    for name, label in indexed_list:
        print fmt % (label, name)


def dictifying_filter_gen(gen):
    """
    Return the rows of a CSV sequence as dictionaries (where the first
    row is the field names)
    """
    field_names = None
    for row in gen:
        if field_names is None:
            field_names = row
            continue
        yield dict([(field_names[n], v) for n, v in enumerate(row)])


def get_export_scheme_instance(cred, syndrome_id, optp, options, args):
    """
    Check syndrome id and form labels are valid and handle '?' to print
    a list if required.  Return an export scheme object.
    """
    es = exportselect.ExportSelect(syndrome_id)
    es.include_deleted = options.include_deleted

    # Parse export scheme specification
    schemes = [scheme for scheme, description in es.scheme_options()]
    if options.export_scheme == '?' or options.export_scheme not in schemes:
        print_indexed_list(list(es.scheme_options()), 'Export schemes:')
        sys.exit(1)
    es.export_scheme = options.export_scheme

    es.refresh(cred)
    exporter = es.exporter

    # Parse forms (if any)
    if '?' in args:
        forms = [(form.label, form.name) for form in exporter.forms]
        print_indexed_list(forms, 'Forms:')
        sys.exit(1)
    formnames = [form.label for form in exporter.forms]
    for name in args:
        if name not in formnames:
            optp.error('form %r not found (for this syndrome?)' % name)
    include_forms = args

    es.include_forms = include_forms
    return es, cred



class CacheFilter:
    """
    A class which takes an exporter and returns records which have
    changed by comparing them against cached data
    """
    def __init__(self, export_scheme, options):
        self.export_scheme = export_scheme
        self.options = options
        # Load our cached state if given
        if not options.state_file:
            # fake being a shelf
            self.cached_state = UserDict()
            self.cached_state.close = lambda: None
        else:
            self.cached_state = shelve.open(options.state_file)

    def extract_row_key(self, row):
        """
        Extract a tuple from a row to uniquely identify it
        """
        key = [row['case_id'], row['syndrome_id']]
        for form in self.export_scheme.include_forms:
            base = '%s.form_id' % form
            if base in row:
                key.append(row[base])
            else:
                n = 0
                while '%s.%d' % (base, n) in row:
                    key.append(row['%s.%d' % (base, n)])
                    n += 1
        return tuple(key)

    def __iter__(self):
        # Run over value tuples checking against cached state
        for row in dictifying_filter_gen(self.export_scheme.row_gen()):
            row_key = self.extract_row_key(row)
            row_key_repr = repr(row_key)
            current_values = [ row[f] for f in self.options.monitored_fields ]
            cached_values = self.cached_state.get(row_key_repr, [None] * len(self.options.monitored_fields))
            changed_values = [ (f, cached_values[n], row[f]) for n, f in enumerate(self.options.monitored_fields) if row[f] != cached_values[n] ]
            if changed_values:
                #print row_key, '->', changed_values
                yield (row, changed_values)

    def update_cache(self, row):
        row_key = self.extract_row_key(row)
        row_key_repr = repr(row_key)
        current_values = [ row[f] for f in self.options.monitored_fields ]
        if not self.options.dry_run:
            self.cached_state[row_key_repr] = current_values

    def commit(self):
        # Clean up
        self.cached_state.close()


def main(args):
    """
    Parse arguments and simulate the use of the export page
    """

    optp = get_option_parser()
    options, args = optp.parse_args(args)

    cred = cmdcommon.user_cred(options)

    syndrome_id = cmdcommon.get_syndrome_id(options.syndrome)

    es = get_export_scheme_instance(cred, syndrome_id, optp, options, args)

    # Some simple validity checks
    if not options.queue_field and not options.default_queue:
        optp.error('No queue field specified')
    if not options.monitored_fields:
        optp.error('No fields specified to monitor')

    cache_filter = CacheFilter(es, options)

    # Generate tasks for changed cases
    tasks.workqueues.load()
    queue_ids = {}
    for q in tasks.workqueues:
        queue_ids[q.name] = q.queue_id
    for row, changed_values in cache_filter:
        case_id = row['case_id']
        task = tasks.EditTask(globals.db, cred, case_id=case_id)
        # either queue_field or default_queue must be set
        if options.queue_field:
            queue_name = row[options.queue_field]
            if options.queue_mapping:
                queue_name = options.queue_mapping[queue_name]
            if options.default_queue and not queue_name:
                queue_name = options.default_queue
        else:
            queue_name = options.default_queue
        task.set_queue_id(globals.db, queue_ids[queue_name])
        task.action = tasks.ACTION_UPDATE_CASE
        task.task_description = "Case %s has changed fields: %s" % (case_id, ", ".join([v[0] for v in changed_values]))
        task.update(globals.db)
        cache_filter.update_cache(row)

    # Commit the changes to the database
    if not options.dry_run:
        globals.db.commit()

    # Clean up
    cache_filter.commit()


if __name__ == '__main__':
    main(sys.argv[1:])

# vim:ts=4:sw=4:et:ai
