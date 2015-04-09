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

from optparse import OptionParser

from cocklebur import datetime
from casemgr import globals

from casemgr.cmdline import cmdcommon

def main(args):
    optp = OptionParser()
    cmdcommon.opt_syndrome(optp)
    cmdcommon.opt_verbose(optp)
    optp.add_option('--type',
            help='Restrict to reports of TYPE')
    optp.add_option('--user',
            help='Show USER reports')
    optp.add_option('--unit',
            help='Show UNIT reports')
    optp.add_option('--all', action='store_true',
            help='Show all reports (ignore "sharing")')
    optp.add_option('--csv', action='store_true',
            help='Use CSV format')
    options, args = optp.parse_args(args)
    if options.user and options.unit:
        optp.error('Only specify one of --user and --unit')


    query = globals.db.query('report_params', order_by='sharing,type,label')

    if options.syndrome:
        synd_id = cmdcommon.get_syndrome_id(options.syndrome)
        query.where('syndrome_id = %s', synd_id)

    if options.type:
        query.where_in('type', options.type.split(','))
    if options.user:
        user_id = cmdcommon.get_user_id(options.user)
        query.where('user_id = %s', user_id)
        query.where_in('sharing', ('private', 'last'))
    elif options.unit:
        unit_id = cmdcommon.get_unit_id(options.unit)
        query.where('unit_id = %s', unit_id)
        query.where('sharing = %s', 'unit')
    elif not options.all:
        query.where_in('sharing', ('public', 'quick'))

    rows = query.fetchall()
    unit_ids = set([r.unit_id for r in rows])
    user_ids = set([r.user_id for r in rows])
    if unit_ids:
        from casemgr.unituser import units
        units.load(*unit_ids)
    if user_ids:
        from casemgr.unituser import users
        users.load(*user_ids)
    if options.csv:
        import csv
        writer = csv.writer(sys.stdout)
        writer.writerow(['id','label','type','sharing','user','unit','syndrome'])
        for row in rows:
            cols = [row.report_params_id, row.label, row.type, row.sharing]
            if row.user_id and len(user_ids) > 1:
                try:
                    cols.append(users[row.user_id].username)
                except KeyError:
                    cols.append(row.user_id)
            else:
                cols.append(None)
            if row.unit_id and len(unit_ids) > 1:
                try:
                    cols.append(units[row.unit_id].name)
                except KeyError:
                    cols.append(row.unit_id)
            else:
                cols.append(None)
            cols.append(row.syndrome_id)
            writer.writerow(cols)
    else:
        for row in rows:
            label = row.label or ''
            extra = [str(row.type)]
            if not options.syndrome:
                extra.append('syndrome_id %s' % row.syndrome_id)
            if options.all:
                extra.append('sharing %s' % row.sharing)
            if row.user_id and len(user_ids) > 1:
                try:
                    extra.append('user %s' % users[row.user_id].username)
                except KeyError:
                    extra.append('user_id %s' % row.user_id)
            if row.unit_id and len(unit_ids) > 1:
                try:
                    extra.append('unit %s' % units[row.unit_id].name)
                except KeyError:
                    extra.append('unit_id %s' % row.unit_id)
            if extra:
                label += ' [%s]' % ', '.join(extra)
            print '%s: %s' % (row.report_params_id, label)
