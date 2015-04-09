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

def acl_query(query, credentials, deleted=False):
    """
    This adds a "where" clause to the given /query/ to limit the query to
    the subset of cases and/or contacts that this unit has access to (as
    given by /credentials/). 

    The where clause is implemented as an "IN" subselect returning the
    visible case_id's.
    """
    if 'ACCESSALL' not in credentials.rights:
        or_query = query.sub_expr('OR')
        if 'ACCESSSYND' in credentials.rights:
            accessquery = or_query.in_select('syndrome_id', 'group_syndromes')
            accessquery.join('JOIN unit_groups USING (group_id)')
            accessquery.where('unit_id = %s', credentials.unit.unit_id)
        else:
            accessquery = or_query.in_select('case_id', 'case_acl')
            accessquery.where('unit_id = %s', credentials.unit.unit_id)
        taskquery = or_query.in_select('case_id', 'tasks', 
                                        columns=['case_id'])
        queuequery = taskquery.in_select('queue_id', 'workqueues')
        queuequery.where('user_id = %s OR unit_id = %s',
                         credentials.user.user_id, credentials.unit.unit_id)
        memberquery = queuequery.union_query('workqueue_members')
        memberquery.where('user_id = %s OR unit_id = %s',
                          credentials.user.user_id, credentials.unit.unit_id)
    if deleted in ('y', True, 'True'):
        query.where('cases.deleted')
    elif deleted in ('n', False, 'False'):
        query.where('not cases.deleted')

def contact_query(query, case_id):
    inq = query.in_select('case_id', 'case_contacts')
    inq.where('contact_id = %s', case_id)
