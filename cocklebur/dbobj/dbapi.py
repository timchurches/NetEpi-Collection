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

# What database prefers for boolean columns
TRUE = True
FALSE = False
# Extra arguments to pass to connect()
connect_extra = dict()

try:
    from ocpgdb import *
    connect_extra = dict(use_mx_datetime=True)
except ImportError:
    from pyPgSQL import PgSQL
    PgSQL.useUTCtimeValue = True       # Works around brokeness in some vers
    PgSQL.fetchReturnsList = True      # faster, and duplicates dbobj work
    from pyPgSQL.PgSQL import *
    Binary = PgBytea
    # pyPgSQL predates python True and False
    TRUE = PG_True
    FALSE = PG_False

# Some fine-grained exceptions. Not part of the API, but this is a convenient
# place to define them.
class IdentifierError(DatabaseError): pass
class ValidationError(DatabaseError): pass
class DuplicateKeyError(OperationalError): pass
class ConstraintError(OperationalError): pass
class TooManyRecords(OperationalError): pass
class RecordDeleted(OperationalError): pass
