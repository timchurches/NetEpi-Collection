#!/usr/bin/python
#
#   The contents of this file are subject to the HACOS License Version 1.2
#   (the "License"); you may not use this file except in compliance with
#   the License.  Software distributed under the License is distributed
#   on an "AS IS" basis, WITHOUT WARRANTY OF ANY KIND, either express or
#   implied. See the LICENSE file for the specific language governing
#   rights and limitations under the License.  The Original Software
#   is "NetEpi Case Manager". The Initial Developer of the Original
#   Software is the Health Administration Corporation, incorporated in
#   the State of New South Wales, Australia.
#
#   Copyright (C) 2006 Health Administration Corporation.
#   All Rights Reserved.
#

"""
Load httpinteract timings into SOOM
"""

# Standard Python
import os
from optparse import OptionParser

# 3rd Party Modules
import mx.DateTime

# SOOM modules
from SOOMv0 import *

sitemap = None
def load_sitemap(filename):
    import csv
    return dict(csv.reader(open(filename, 'rb')))

def make_httptimings(options):
    httptimings = makedataset(options.dsname, label=options.dslabel)
    httptimings.addcolumn("started", label="Start time", 
                          coltype="ordinal", datatype="datetime")
    httptimings.addcolumn("siteinfo", label="Site", 
                          coltype="categorical", datatype='recode')
    httptimings.addcolumn("status", label="Transaction status", 
                          coltype="categorical", datatype='recode')
    httptimings.addcolumn("elapsed", label="Elapsed time", 
                          coltype="scalar", datatype=float)
    httptimings.addcolumn("srcaddr", label="Source IP address", 
                          coltype="categorical", datatype='recode')
    httptimings.addcolumn("fwdaddr", label="Forwarded IP address", 
                          coltype="categorical", datatype='recode')
    httptimings.addcolumn("useragent", label="Type of browser", 
                          coltype="categorical", datatype='recode')
    if options.verbose:
        print httptimings
    return httptimings

# started,siteinfo,status,elapsed,received,srcaddr,forwarded,useragent

def httptimings_CSV_source(options, **kwargs):
    httptimings_columns = [
        DataSourceColumn("started",ordinalpos=0,format="yyyy-mm-dd HH:MM:SS"),
        DataSourceColumn("siteinfo",ordinalpos=1),
        DataSourceColumn("status",ordinalpos=2),
        DataSourceColumn("elapsed",ordinalpos=3),
        DataSourceColumn("srcaddr",ordinalpos=5),
        DataSourceColumn("fwdaddr",ordinalpos=6),
        DataSourceColumn("useragent",ordinalpos=7),
    ]

    from SOOMv0.Sources.CSV import CSVDataSource
    return CSVDataSource("httptimings_data", httptimings_columns, 
                         filename=options.filename, header_rows=1, 
                         delimiter="|", **kwargs)

def httptimings_DB_source(options, **kwargs):
    httptimings_columns = [
        DataSourceColumn("started"),
        DataSourceColumn("siteinfo"),
        DataSourceColumn("status"),
        DataSourceColumn("elapsed"),
        DataSourceColumn("srcaddr"),
        DataSourceColumn("fwdaddr", dbname='forwarded'),
        DataSourceColumn("useragent"),
    ]

    try:
        import psycopg2 as dbapi
        import psycopg2.extensions
        import _psycopg
        psycopg2.extensions.new_type((1114, 1184, 704, 1186),
                                      'DATETIME', _psycopg.MXDATETIME)
        psycopg2.extensions.new_type((1083, 1266),
                                      'TIME', _psycopg.MXTIME)
        psycopg2.extensions.new_type((1082,),
                                      'DATE', _psycopg.MXDATE)
        psycopg2.extensions.new_type((704, 1186),
                                      'INTERVAL', _psycopg.MXINTERVAL)
    except ImportError:
        from pyPgSQL import PgSQL as dbapi
    from SOOMv0.Sources.DB import DBDataSource

    db = dbapi.connect(database=options.database)
    return DBDataSource("httptimings_data", httptimings_columns, db,
                        options.table, **kwargs)

def der_dt(start_date_time):
    data = [None] * len(start_date_time)
    rel = mx.DateTime.RelativeDateTime(minute=0, second=0)
    for i in xrange(len(start_date_time)):
        if start_date_time[i]:
            data[i] = start_date_time[i] + rel
    return data, None


def http_xform(row_dict):
    siteinfo = row_dict['siteinfo'].strip()
    row_dict['siteinfo'] = sitemap.get(siteinfo, siteinfo)
    return row_dict


def load_httptimings(ds, options):
    source_args = {}
    if options.sitemap:
        global sitemap
        sitemap = load_sitemap(options.sitemap)
        source_args['xformpre'] = http_xform
    httpdata = httptimings_DB_source(options)
    if options.verbose:
        print httpdata
    ds.initialise()
    ds.loaddata(httpdata, rowlimit=None)
    ds.finalise()

def load(options):
    soom.setpath(options.path)
    soom.writepath = soom.searchpath[0]
    httptimings = make_httptimings(options)
    load_httptimings(httptimings, options)
    httptimings.derivedcolumn(dername='start_hour',
                   dercols=('started',), derfunc=der_dt,
                   datatype='datetime', coltype='ordinal', label='Start hour')
    httptimings.save()
    # httptimings = make_httptimings(dsname='HTTPvariola',dslabel="PHU http round-trip timings (internet)")
    # load_httptimings(httptimings,'variola_http.csv')
    # httptimings.derivedcolumn(dername='start_hour',
    #               dercols=('started',), derfunc=der_dt,
    #               datatype='datetime', coltype='ordinal', label='Start hour')
    # httptimings.save()


if __name__ == '__main__':
    optp = OptionParser()
    optp.add_option('-P', '--path',
                    type='string', dest='path', default=None,
                    help='SOOM dataset path')
    optp.add_option('--database',
                    type='string', dest='database', 
                    default='httpinteract', help='database name')
    optp.add_option('--table',
                    type='string', dest='table', 
                    default='reports', help='database table')
    optp.add_option('--dsname',
                    type='string', dest='dsname', 
                    default='httpinteract', help='SOOM dataset name')
    optp.add_option('--dslabel',
                    type='string', dest='dslabel', 
                    default='http round-trip timings', 
                    help='SOOM dataset label')
    optp.add_option('--sitemap',
                    type='string', dest='sitemap', 
                    help='CSV file mapping site names')
    optp.add_option('-v', '--verbose',
                    action='store_true', dest='verbose', default=False,
                    help='Enable vebosity')
    options, args = optp.parse_args()
    if args:
        optp.error('Use --help for usage info')
    load(options)
