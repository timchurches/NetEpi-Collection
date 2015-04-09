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
import copy
try:
    set
except NameError:
    from sets import Set as set

from cocklebur import datetime, trafficlight
from casemgr import paged_search, demogfields, globals, tasks, cached
import config

def case_summary(db, case_id, case_dict, person_dict):
    case_row = case_dict.get(case_id)
    if case_row is None:
        return 'unknown'
    fields = demogfields.get_demog_fields(db, case_row.syndrome_id)
    fields = fields.context_fields('result')
    person_row = person_dict.get(case_row.person_id)
    if person_row is not None:
        summary = '%s, %s' % (fields.summary(case_row), 
                              fields.summary(person_row))
    return summary


def task_subscription_query(query, credentials):
    subquery = query.in_select('queue_id', 'workqueue_members',
                                conjunction='OR')
    subquery.where('unit_id = %s', credentials.unit.unit_id)
    subquery.where('user_id = %s', credentials.user.user_id)
    subquery = subquery.union_query('workqueues', conjunction='OR')
    subquery.where('unit_id = %s', credentials.unit.unit_id)
    subquery.where('user_id = %s', credentials.user.user_id)


class TaskSearchParams:
    def __init__(self, view_type, order_by):
        self.view_type = view_type
        self.order_by = order_by
        self.include_future = False
        self.include_completed = False
        self.include_deleted_cases = False

    def __eq__(self, other):
        if not isinstance(other, TaskSearchParams):
            return False
        return (self.view_type == other.view_type and
                self.order_by == other.order_by and
                self.include_future == other.include_future and
                self.include_completed == other.include_completed and
                self.include_deleted_cases == other.include_deleted_cases)

    def __ne__(self, other):
        return not self == other

    def copy(self):
        return copy.copy(self)

    def __repr__(self):
        return 'TaskSearchParams(%r, %r, %r, %r, %r)' %\
            (self.view_type, self.order_by, self.include_future,
             self.include_completed, self.include_deleted_cases)
            

class TaskSearch(paged_search.SortablePagedSearch):
    orders = [
        ('due_date,active_date', 'Due Date'),
        ('active_date', 'Active Date'),
        ('completed_date', 'Completed Date'),
        ('task_description,task_id', 'Task Description'),
        ('users.username', 'Assigner'),
        ('task_id', 'Task ID'),
        ('case_id,task_id', 'Case ID'),
    ]
    views = [
        ('active', 'Active tasks'),
        ('assignee', 'Edit my tasks'),
        ('overdue', 'Overdue tasks'),
    ]

    def __init__(self, db, credentials, prefs, case_id=None):
        self.db = db
        self.credentials = credentials
        self.case_id = case_id
        self.only_overdue = False
        if 'ACCESSALL' in self.credentials.rights:
            self.views = self.views + [('alloverdue', 'All overdue tasks')]
        saved_params = prefs.get('ts_params')
        if saved_params is None:
            self.params = TaskSearchParams(view_type=self.views[0][0],
                                           order_by=self.orders[0][0])
        else:
            self.params = saved_params.copy()
        self.last_params = None
        paged_search.SortablePagedSearch.__init__(self, db, prefs)

    def user_views(self, credentials):
        views = list(self.views)
        for queue in tasks.user_workqueues(credentials):
            name = queue.name
            if len(name) > 20:
                name = name[:20] + '...'
            views.append(('queue_%d' % queue.queue_id, name + ' queue'))
        return views

    def new_search(self):
        if self.params == self.last_params:
            return
        paged_search.SortablePagedSearch.new_search(self)
        is_admin = 'ACCESSALL' in self.credentials.rights
        query = self.db.query('tasks', order_by=self.params.order_by)
        self.viewonly = 'VIEWONLY' in self.credentials.rights
        self.allow_edit = False
        if self.case_id is not None:
            query.where('case_id = %s', self.case_id)
        if not self.params.include_deleted_cases and self.case_id is None:
            query.join('LEFT JOIN cases USING (case_id)')
            subquery = query.sub_expr(conjunction='OR')
            subquery.where('NOT cases.deleted')
            subquery.where('cases.deleted IS null')
            subquery.where('tasks.case_id IS null')
        if self.params.view_type == 'assignee':
            self.allow_edit = True
            subquery = query.sub_expr(conjunction = 'OR')
            subquery.where('assigner_id = %s', self.credentials.user.user_id)
            subquery.where('originator_id = %s', self.credentials.user.user_id)
        elif self.params.view_type == 'alloverdue' and is_admin:
            # admin sees everything
            self.allow_edit = True
        elif self.params.view_type.startswith('queue_'):
            queue_id = int(self.params.view_type[len('queue_'):])
            query.where('queue_id = %s', queue_id)
        else:
            subquery = query.sub_expr(conjunction = 'OR')
            # Filter for tasks assigned to us
            task_subscription_query(subquery, self.credentials)
            # OR tasks assigned by us that are overdue
            overdue_query = subquery.sub_expr(conjunction = 'AND')
            uquery = overdue_query.sub_expr(conjunction = 'OR')
            uquery.where('assigner_id = %s', self.credentials.user.user_id)
            uquery.where('originator_id = %s', self.credentials.user.user_id)
            overdue_query.where('due_date <= CURRENT_TIMESTAMP')
        if self.params.order_by.startswith('users.'):
            query.join('JOIN users ON (users.user_id = assigner_id)')
        if (not bool(self.params.include_future) 
            and self.params.view_type != 'assignee'):
            query.where('active_date <= CURRENT_TIMESTAMP')
        if not bool(self.params.include_completed):
            query.where('completed_date is null')
        if self.params.view_type in ('overdue', 'alloverdue'):
            query.where('due_date <= CURRENT_TIMESTAMP')
        self.query = query
        self.last_params = self.params.copy()
        self.prefs.set('ts_params', self.last_params)

    def page_rows(self, cred):
        self.page_jump()
        # Fetch task rows
        results = paged_search.SortablePagedSearch.page_rows(self)
        # Fetch associated entities
        case_dict = self.db.table_dict('cases')
        user_dict = self.db.table_dict('users')
        unit_dict = self.db.table_dict('units')
        person_dict = self.db.table_dict('persons')
        queue_dict = self.db.table_dict('workqueues')
        for task in results:
            if task.case_id is not None:
                case_dict.want(task.case_id)
            if task.originator_id is not None:
                user_dict.want(task.originator_id)
            if task.assigner_id is not None:
                user_dict.want(task.assigner_id)
            if task.locked_by_id is not None:
                user_dict.want(task.locked_by_id)
            if task.completed_by_id is not None:
                user_dict.want(task.completed_by_id)
            queue_dict.want(task.queue_id)
        queue_dict.preload()
        for queue in queue_dict.values():
            if queue.unit_id is not None:
                unit_dict.want(queue.unit_id)
            if queue.user_id is not None:
                user_dict.want(queue.user_id)
        case_dict.preload()
        unit_dict.preload()
        user_dict.preload()
        for case in case_dict.itervalues():
            person_dict.want(case.person_id)
        person_dict.preload()
        # Now join it all together
        now = datetime.now()
        for task in results:
            task.active_relative = datetime.relative(task.active_date, now)
            active_days = (now - task.active_date).days
            task.active_color = trafficlight.web_trafficlight(active_days, 30)
            if task.completed_date:
                task.complete_color = '#cccccc'
                if task.action == tasks.ACTION_THREAD_DELETED:
                    task.complete_relative = 'DELETED'
                else:
                    task.complete_relative = 'completed'
                completed_by = user_dict.get(task.completed_by_id)
                if completed_by is not None:
                    task.complete_relative += ' by %s ' % completed_by.username
                task.complete_relative += str(task.completed_date)
            elif task.due_date is None:
                task.complete_color = 'transparent'
                task.complete_relative = ''
            else:
                due_days = (now - task.due_date).days + 15
                task.complete_color = trafficlight.web_trafficlight(due_days, 30)
                task.complete_relative = datetime.relative(task.due_date, now)
            task.originator = user_dict.get(task.originator_id)
            task.assigner = user_dict.get(task.assigner_id)
            task.locked_by = user_dict.get(task.locked_by_id)
            task.locked_relative = datetime.relative(task.locked_date, now)
            queue = queue_dict.get(task.queue_id)
            if queue is None:
                task.assignee = ''
            elif queue.unit_id is not None:
                task.assignee = '%s: %s' %\
                    (config.unit_label, unit_dict.get(queue.unit_id).name)
            elif queue.user_id is not None:
                task.assignee = 'User: %s' %\
                    user_dict.get(queue.user_id).username
            else:
                task.assignee = 'Queue: %s' % queue.name
            task.case_summary = task.contact_summary = ''
            if task.case_id is not None:
                task.case_summary = case_summary(self.db, task.case_id,
                                                 case_dict, person_dict)
            task.action_summary = tasks.action_desc.get(task.action, 'unknown')
        return results


class QuickTask:

    cols = (
        'tasks.task_id', 'cases.case_id',
        'persons.surname', 'persons.given_names', 
        'tasks.task_description', 'tasks.due_date', 'tasks.active_date',
    )

    def __init__(self, now, task_id, case_id, surname, given_names, 
                 description, due_date, active_date):
        self.task_id = task_id
        self.case_id = case_id
        self.surname = surname
        self.given_names = given_names
        self.description = description
        self.due_relative = datetime.relative(due_date or active_date, now)


class QuickTasks(list, cached.Cached):

    def __init__(self, credentials):
        self.credentials = credentials

    def load(self):
        query = globals.db.query('tasks', order_by='due_date,active_date',                                       limit=10)
        # Exclude deleted cases via /cases/ LEFT JOIN
        query.join('LEFT JOIN cases USING (case_id)')
        subquery = query.sub_expr(conjunction='OR')
        subquery.where('NOT cases.deleted')
        subquery.where('cases.deleted IS null')
        subquery.where('tasks.case_id IS null')
        if 0:
            # Filter for tasks assigned to us
            subquery = query.sub_expr(conjunction = 'OR')
            task_subscription_query(subquery, self.credentials)
            # OR tasks assigned by us that are overdue
            overdue_query = subquery.sub_expr(conjunction = 'AND')
            uquery = overdue_query.sub_expr(conjunction = 'OR')
            uquery.where('assigner_id = %s', self.credentials.user.user_id)
            uquery.where('originator_id = %s', self.credentials.user.user_id)
            overdue_query.where('due_date <= CURRENT_TIMESTAMP')
        else:
            task_subscription_query(query, self.credentials)
        query.where('active_date <= CURRENT_TIMESTAMP')
        query.where('completed_date is null')
        query.join('LEFT JOIN persons USING (person_id)')
        now = datetime.now()
        self[:] = [QuickTask(now, *row) 
                   for row in query.fetchcols(QuickTask.cols)]
