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
import sys, os, csv, re
from optparse import OptionParser
try:
    set
except NameError:
    from sets import Set as set

from notifychangedfields import add_export_options, get_export_scheme_instance
from notifychangedfields import add_cache_options, CacheFilter


ourname = os.path.basename(sys.argv[0])

configurable_options = {
        'url': 'http://localhost/~febrl/submit_job.cgi',
        'queue': 'general',
        'priority': 100,
        'password': 'halibut',
        'neighbour_match_level': 2,
        'email': None,
        'id_field': None,
        'target': None,
        'address_fields': [],
        'input_file': None,
    }

def get_option_parser():
    """
    Create the option parser for the script
    """
    usage = '%prog [options] <syndrome_id> <form_id> <form_id> ... (use ? for a list)'
    parser = OptionParser(usage=usage)
    add_export_options(parser)
    add_cache_options(parser)
    parser.set_defaults(**configurable_options)
    parser.add_option("-i", "--input-file",
            help="read csv input from FILENAME [default: %default]", metavar="FILENAME")
    parser.add_option("--url",
            help="connect to geocoder at URL [default: %default]", metavar="FILENAME")
    parser.add_option("-q", "--queue",
            help="submit jobs to QUEUE [default: %default]", metavar="QUEUE")
    parser.add_option("-p", "--priority",
            type="int",
            help="submit jobs with priority INT [default: %default]", metavar="INT")
    parser.add_option("-P", "--password",
            help="password used to set higher priority geocoder jobs", metavar="PASSWORD")
    parser.add_option("-N", "--neighbour-match-level",
            type="int",
            help="geocoder neighbour match level [default: %default]", metavar="INT")
    parser.add_option("-e", "--email",
            help="mail completed jobs to this address [default: %default]", metavar="ADDRESS")
    parser.add_option("-I", "--id-field",
            help="source id field [default: %default]", metavar="FIELD")
    parser.add_option("-T", "--target",
            help="target for geocoder results [default: %default]", metavar="TARGET")
    parser.add_option("-A", "--address-field", dest="address_fields",
            action="append",
            help="target field and source components [default: %default]", metavar="TARGET,SOURCE[,SOURCE,...]")
    return parser


class DummyExporter:
    FORM_ID_RE = re.compile(r"^(?P<form_name>.*?)\.form_id(\.\d+)$")

    def __init__(self, csv_reader):
        self.__reader = csv_reader
        # we need to determine the forms in the file
        # look for fields of the form name.form_id[.number]
        self.header_row = self.__reader.next()
        self.include_forms = []
        for column in self.header_row:
            m = self.FORM_ID_RE.match(column)
            if m and m.group('form_name') not in self.include_forms:
                self.include_forms.append(m.group('form_name'))

    def row_gen(self):
        yield self.header_row
        for r in self.__reader:
            yield r


def main(args):
    """
    Parse arguments and simulate the use of the export page
    """

    parser = get_option_parser()
    options, args = parser.parse_args(args)
    if options.input_file:
        if options.input_file == "-":
            input = sys.stdin
        else:
            input = file(options.input_file)
        es = DummyExporter(csv.reader(input))
        cred = None
    else:
        es, cred = get_export_scheme_instance(parser, options, args)

    # Some simple validity checks
    if not options.address_fields:
        parser.error('No composed address fields specified')
    if not options.id_field:
        parser.error('No id field specified')
    if not options.target:
        parser.error('No target specified')

    # Build some list of which components constitute which target fields
    monitored_fields = set()
    address_components = {}
    target_field = {}
    for address_field in options.address_fields:
        parts = address_field.split(',')
        target = parts.pop(0)
        if not parts:
            parser.error('Address specifier must have a non-empty component list')
        address_components[target] = parts
        monitored_fields.update(parts)
        for part in parts:
            target_field[part] = target
    options.monitored_fields = monitored_fields | set(options.monitored_fields)

    cache_filter = CacheFilter(es, options)

    # Generate geocoder data for changed data
    input_addresses = []
    for row, changed_values in cache_filter:
        required_targets = set()
        for changed_field, old_value, new_value in changed_values:
            try:
                required_targets.add(target_field[changed_field])
            except KeyError:
                # really shouldn't happen because why would we be monitoring
                # a field and not using it?
                pass
        # we're going to misuse the geocoder id field slightly
        # each row is going to be id,target_field<space>address
        for target in required_targets:
            id = "%s,%s" % (row[options.id_field], target)
            address = " ".join([ row[f] for f in address_components[target] ])
            input_addresses.append(" ".join([id, address]))

    # Send any data to the geocoder
    if not options.dry_run:
        print "\n".join(input_addresses)

    # Clean up
    cache_filter.commit()


if __name__ == '__main__':
    main(sys.argv[1:])

# vim:ts=4:sw=4:et:ai
