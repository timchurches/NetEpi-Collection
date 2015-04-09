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

from casemgr import globals, cached

class TaskDescError(globals.Error): pass

class TaskDescriptions(cached.NotifyCache):
    """
    This class "learns" what task parameters are typically set by a
    given task_description.
    """
    cols = (
        'queue_id', 'creation_date', 'active_date', 'due_date', 
        'task_description', 'annotation', 'form_name'
    )
    notification_target = 'taskdesc'

    def __init__(self, syndrome_id):
        cached.NotifyCache.__init__(self)
        self.syndrome_id = syndrome_id

    def load(self):
        query = globals.db.query('tasks', limit=200, order_by='task_id desc')
        if self.syndrome_id is None:
            query.where('case_id IS null')
        else:
            query.join('LEFT JOIN cases USING (case_id)')
            query.where('syndrome_id = %s', self.syndrome_id)
        desc_kv_counts = {}
        desc_count = {}
        for row in query.fetchcols(self.cols):
            row = dict(zip(self.cols, row))
            creation_date = row.pop('creation_date')
            active_date = row.pop('active_date')
            active_relative = active_date - creation_date
            if active_relative >= 0:
                row['active_date'] = active_relative
            if row['due_date']:
                due_relative = row['due_date'] - active_date
                if due_relative >= 0:
                    row['due_date'] = due_relative
            desc_key = row['task_description']
            desc_count[desc_key] = desc_count.get(desc_key, 0) + 1
            kv_counts = desc_kv_counts.setdefault(desc_key, {})
            for key, value in row.items():
                vc = kv_counts.setdefault(key, {})
                vc[value] = vc.get(value, 0) + 1
        desc_kv_counts = [(desc_count[desc], desc, kv_counts)
                          for desc, kv_counts in desc_kv_counts.iteritems()]
        desc_kv_counts.sort()
        desc_kv_counts.reverse()
        del desc_kv_counts[20:]
        names_order = []
        desc_params_by_name = {}
        for row_count, desc, kv_counts in desc_kv_counts:
            desc_params = {}
            for key, vc in kv_counts.iteritems():
                vc = [(c, i, v) for i, (v, c) in enumerate(vc.iteritems())]
                vc.sort()
                top_count, ignore, value = vc[-1]
                if float(top_count) / float(row_count) > 0.5:
                    desc_params[key] = value
            names_order.append(desc)
            desc_params_by_name[desc] = desc_params
        self.names_order = names_order
        self.desc_params_by_name = desc_params_by_name

    def options(self):
        return self.names_order

    def params(self, name):
        try:
            return self.desc_params_by_name[name]
        except KeyError:
            raise TaskDescError('Task description %r not available' % name)

task_desc_by_syndrome = {}

def get_task_descs(syndrome_id):
    try:
        td = task_desc_by_syndrome[syndrome_id]
    except KeyError:
        td = task_desc_by_syndrome[syndrome_id] = TaskDescriptions(syndrome_id)
    td.refresh()
    return td

def task_options(syndrome_id):
    return get_task_descs(syndrome_id).options()

def params(syndrome_id, name):
    return get_task_descs(syndrome_id).params(name)
