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
from casemgr import globals

def exclusiveop(fn):
    def _exclusiveop(name, *args, **kwargs):
        """
        Obtain a row-locked copy of the current row, and pass it
        to the supplied callback for processing. If the callback
        returns, the row will be committed. If it raises an
        exception, the transaction will be rolled back.
        """
        query = globals.db.query('forms', for_update=True)
        query.where('label = %s', name)
        try:
            dbrow = query.fetchone()
            if dbrow is None:
                dbrow = globals.db.new_row('forms')
            fn(dbrow, name, *args, **kwargs)
        except:
            globals.db.rollback()
            raise
        globals.db.commit()
        return dbrow
    return _exclusiveop
