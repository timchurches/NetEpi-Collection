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

from mx import DateTime
from cocklebur import dbobj, datetime
from casemgr import globals, paged_search, unituser, cached
import config

class TaskError(globals.Error): pass

# Task actions
ACTION_NOTE = 0
ACTION_NEW_CASE = 1
ACTION_UPDATE_CASE = 2
ACTION_NEW_CASE_FORM = 3
ACTION_UPDATE_CASE_FORM = 4
ACTION_THREAD_COMPLETED = 9
ACTION_THREAD_DELETED = 10

action_desc = {
    ACTION_NOTE: 'Information',
    ACTION_NEW_CASE: 'New Case',
    ACTION_UPDATE_CASE: 'Update Case',
    ACTION_NEW_CASE_FORM: 'New Case Form',
    ACTION_UPDATE_CASE_FORM: 'Update Case Form',
    ACTION_THREAD_COMPLETED: 'Completed',
    ACTION_THREAD_DELETED: 'Deleted',
}

action_req_case = set((
    ACTION_UPDATE_CASE, ACTION_NEW_CASE_FORM, ACTION_UPDATE_CASE_FORM,
))
action_req_form_name = set((
    ACTION_NEW_CASE_FORM, ACTION_UPDATE_CASE_FORM,
))
action_req_summary_id = set((
    ACTION_UPDATE_CASE_FORM,
))
action_closed = set((
    ACTION_THREAD_COMPLETED, ACTION_THREAD_DELETED,
))
action_case_edit = set((
    ACTION_UPDATE_CASE,
))
action_form_edit = set((
    ACTION_NEW_CASE_FORM, ACTION_UPDATE_CASE_FORM,
))
action_dispatchable = set((
    ACTION_NOTE,
    ACTION_UPDATE_CASE, ACTION_NEW_CASE_FORM, ACTION_UPDATE_CASE_FORM,
))


def guess_action(task):
    if task.case_id is None:
        # Ambiguous - ACTION_NOTE or ACTION_NEW_CASE
        return ACTION_NOTE
    else:
        if task.form_name is None:
            return ACTION_UPDATE_CASE
        elif task.summary_id is None:
            return ACTION_NEW_CASE_FORM
        else:
            return ACTION_UPDATE_CASE_FORM


def same_entity(task, action, case_id, form_name=None, 
                summary_id=None):
    """
    Check if the correct entity has been edited
    """
    if 0:
        import sys
        print >> sys.stderr, 'task: %r %r %r %r' %\
            (action_desc[task.action], 
             task.case_id, task.form_name, task.summary_id)
        print >> sys.stderr, 'user: %r %r %r %r' %\
            (action_desc[action], case_id, form_name, summary_id)
    if task.action != action:
        return False
    if action in action_req_case and task.case_id != case_id:
        return False
    if action in action_req_form_name and task.form_name != form_name:
        return False
    if action in action_req_summary_id and task.summary_id != summary_id:
        return False
    return True

class WorkQueues(cached.NotifyCache):
    notification_target = 'workqueues'

    def __init__(self):
        cached.NotifyCache.__init__(self)
        self.queues = None
        self.by_id = None

    def load(self):
        query = globals.db.query('workqueues', order_by='name')
        query.where('user_id is null AND unit_id is null')
        self.queues = query.fetchall()
        self.by_id = {}
        for queue in self.queues:
            self.by_id[queue.queue_id] = queue

    def __len__(self):
        self.refresh()
        return len(self.queues)

    def __iter__(self):
        self.refresh()
        return iter(self.queues)

    def __getitem__(self, i):
        self.refresh()
        return self.by_id[i]

    def options(self):
        self.refresh()
        return [(q.queue_id, q.name) for q in self.queues]

workqueues = WorkQueues()


def user_workqueues_query(credentials, **kwargs):
    """
    Returns a query for workqueues the user is a member of
    """
    query = globals.db.query('workqueues', **kwargs)
    query.join('LEFT JOIN workqueue_members USING (queue_id)')
    query.where('workqueues.user_id is null AND workqueues.unit_id is null')
    if 'ACCESSALL' not in credentials.rights:
        subquery = query.sub_expr('OR')
        subquery.where('workqueue_members.unit_id = %s', 
                        credentials.unit.unit_id)
        subquery.where('workqueue_members.user_id = %s', 
                        credentials.user.user_id)
    return query


def user_workqueues(credentials):
    """
    Returns a list of workqueues the user is a member of
    """
    query = user_workqueues_query(credentials, distinct=True, order_by='name')
    return query.fetchall()


class QueueStats(cached.Cached):
    def __init__(self, queue_id):
        self.queue_id = queue_id
        self.refresh()

    def load(self):
        query = globals.db.query('tasks')
        if self.queue_id is not None:
            query.where('queue_id = %s', self.queue_id)
        now = datetime.now()
        self.total = self.completed = self.active =\
            self.overdue = self.locked = 0
        cols = 'due_date', 'completed_date', 'locked_by_id'
        for due_date, completed_date, locked_by_id in query.fetchcols(cols):
            self.total += 1
            if completed_date is None:
                self.active += 1
                if due_date < now:
                    self.overdue += 1
                if locked_by_id is not None:
                    self.locked += 1
            else:
                self.completed += 1

    def __iter__(self):
        self.refresh()
        return iter([
            ('Total', self.total),
            ('Active', self.active),
            ('Overdue', self.overdue),
            ('Completed', self.completed),
            ('Locked', self.locked),
        ])


def delete_queue(queue_id):
    assert queue_id is not None
    query = globals.db.query('workqueues')
    query.where('queue_id = %s', queue_id)
    queue = query.fetchone()
    query = globals.db.query('tasks')
    query.where('queue_id = %s', queue_id)
    query.where('completed_date is not null')
    query.delete()
    try:
        queue.db_delete()
    except dbobj.ConstraintError:
        raise TaskError('workqueue %r cannot be deleted as it has outstanding tasks' % queue.name)


class AssignHelper:
    assign_types = [
        ('me', 'Me'),
        ('myunit', 'My ' + config.unit_label.lower()),
        ('originator', 'Originator'),
        ('assigner', 'Last assigner'),
        ('queue', 'Task queue'),
        ('user', 'Another user'),
        ('unit', 'Another ' + config.unit_label.lower()),
    ]
    workqueues = workqueues

    def __init__(self, db, queue_id, 
                 this_unit_id, this_user_id, originator_id, last_assigner_id):
        self.queue_id = None
        self.this_unit_id = this_unit_id
        self.this_user_id = this_user_id
        self.originator_id = originator_id
        self.last_assigner_id = last_assigner_id
        self.unit_id = None
        self.user_id = None
        self.assign_type = 'me'
        if queue_id is not None:
            query = db.query('workqueues')
            query.where('queue_id = %s', queue_id)
            queue = query.fetchone()
            if queue.unit_id is not None:
                if queue.unit_id == self.this_unit_id:
                    self.assign_type = 'myunit'
                else:
                    self.assign_type = 'unit'
                    self.unit_id = queue.unit_id
            elif queue.user_id is not None:
                if queue.user_id == self.this_user_id:
                    self.assign_type = 'me'
                elif queue.user_id == self.originator_id:
                    self.assign_type = 'originator'
                else:
                    self.assign_type = 'user'
                    self.user_id = queue.user_id
            else:
                self.assign_type = 'queue'
                self.queue_id = queue_id
        disable = set()
        if self.originator_id == this_user_id:
            disable.add('originator')
        if self.last_assigner_id == this_user_id:
            disable.add('assigner')
        if self.last_assigner_id == self.originator_id:
            disable.add('assigner')
        if not self.workqueues:
            disable.add('queue')
        self.assign_types = [(k, v) for k, v in self.assign_types
                                if k not in disable]

    def get_queue_id(self, db):
        if self.assign_type == 'queue':
            try:
                return int(self.queue_id)
            except TypeError:
                # This might happen if no workqueues are configured.
                raise TaskError('Task is assigned to an invalid queue')
        if self.assign_type in ('myunit', 'unit'):
            attr = 'unit_id'
        else:
            attr = 'user_id'
        if self.assign_type == 'me':
            value = self.this_user_id
        elif self.assign_type == 'myunit':
            value = self.this_unit_id
        elif self.assign_type == 'originator':
            value = self.originator_id
        elif self.assign_type == 'assigner':
            value = self.last_assigner_id
        else:
            value = getattr(self, attr)
        while 1:
            query = db.query('workqueues')
            query.where('%s = %%s' % attr, value)
            queue = query.fetchone()
            if queue is not None:
                return queue.queue_id
            queue = db.new_row('workqueues')
            setattr(queue, attr, value)
            try:
                queue.db_update()
            except dbobj.DuplicateKeyError:
                pass
            else:
                return queue.queue_id

    def unit_str(self):
        if self.unit_id is None:
            return ''
        return unituser.units[self.unit_id].name

    def user_str(self):
        if self.user_id is None:
            return ''
        return unituser.users[self.user_id].username

    def originator_str(self):
        if self.originator_id is None:
            return ''
        return unituser.users[self.originator_id].username

    def last_assigner_str(self):
        if self.last_assigner_id is None:
            return ''
        return unituser.users[self.last_assigner_id].username



class _TaskBase:
    _copy_attrs = (
        'queue_id', 'action', 'task_description', 'annotation',
        'case_id', 'form_name', 'summary_id', 
        'originator_id', 'assigner_id', 'active_date', 'due_date',
    )
    def _fetch(self, db, task_id):
        return db.query('tasks').where('task_id = %s', task_id).fetchone()

    def _locked_fetch(self, db, task_id, user_id=None):
        query = db.query('tasks', for_update=True)
        query.where('task_id = %s', task_id)
        if user_id is not None:
            query.where('locked_by_id = %s', user_id)
        return query.fetchone()

    def _copy(self, src, dst):
        for attr in self._copy_attrs:
            setattr(dst, attr, getattr(src, attr))

    def _init(self, user_id):
        self.queue_id = None
        self.case_id = None
        self.task_description = ''
        self.annotation = ''
        self.form_name = None
        self.summary_id = None
        self.originator_id = user_id
        self.assigner_id = user_id
        self.active_date = None
        self.due_date = None


def _our_lock(task, user_id):
    return task.locked_by_id is not None and task.locked_by_id == user_id

def _set_unlocked(task):
    task.locked_by_id = None
    task.locked_date = None

def _set_completed(task, user_id):
    assert user_id is not None
    if not task.completed_date:
        task.completed_date = datetime.now()
        task.completed_by_id = user_id

def _set_assigned(task, user_id):
    assert user_id is not None
    task.assigner_id = user_id
    task.assignment_date = datetime.now()

def _clear_completed(task):
    task.completed_date = None
    task.completed_by_id = None

class EditTask(_TaskBase):
    active_options = [
        ('now', 'Immediately'),
        ('tomorrow', 'Tomorrow'),
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
        ('week', 'One week'),
        ('fortnight', 'Two weeks'),
        ('month', 'One month'),
        ('quarter', 'Three months'),
    ]
    due_options = [
        ('', 'No deadline'),
        ('now', 'As soon as possible'),
        ('1h', 'One hour'),
        ('4h', 'Four hours'),
        ('tomorrow', 'One day'),
        ('monday', 'Monday after active'),
        ('tuesday', 'Tuesday after active'),
        ('wednesday', 'Wednesday after active'),
        ('thursday', 'Thursday after active'),
        ('friday', 'Friday after active'),
        ('saturday', 'Saturday after active'),
        ('sunday', 'Sunday after active'),
        ('week', 'One week after active'),
        ('fortnight', 'Two weeks after active'),
        ('month', 'One month after active'),
        ('quarter', 'Three months after active'),
    ]
    repeat_options = [
        ('none', 'Don\'t repeat'),
        ('hourly', 'Hourly'),
        ('twohourly', 'Every 2 Hours'),
        ('fourhourly', 'Every 4 Hours'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]
    repeat_delta_map = {
        'hourly': DateTime.RelativeDateTime(hours=1),
        'twohourly': DateTime.RelativeDateTime(hours=2),
        'fourhourly': DateTime.RelativeDateTime(hours=4),
        'daily': DateTime.RelativeDateTime(days=1),
        'weekly': DateTime.RelativeDateTime(weeks=1),
        'monthly': DateTime.RelativeDateTime(months=1),
    }
    repeatcount_options = ['n/a'] + range(2, 53)

    def __init__(self, db, credentials, task_row=None, 
                 case_id=None, inplace=False):
        self.credentials = credentials
        self.inplace = inplace
        self.this_user_id = self.credentials.user.user_id
        self.repeat = self.repeat_options[0][0]
        self.repeatcount = self.repeatcount_options[0][0]
        self.datetime_format = datetime.mx_parse_datetime.format
        if task_row is None:
            self._init(self.this_user_id)
            self.seed_task_id = None
            if case_id is not None:
                self.case_id = case_id
        else:
            self._copy(task_row, self)
            self.seed_task_id = task_row.task_id
            if self.inplace:
                self.active_options = [('nochange', 'No change')] \
                            + self.active_options
                self.due_options = [('nochange', 'No change')] \
                            + self.due_options
        self.set_queue_id(db, self.queue_id)
        self.active = self.active_options[0][0]
        self.due = self.due_options[0][0]
        self.active_abs = self.due_abs = ''
        if self.active_date:
            self.active_abs = str(self.active_date)
        if self.due_date:
            self.due_abs = str(self.due_date)

    def set_queue_id(self, db, queue_id):
        self.assignee = AssignHelper(db, queue_id,
                                     self.credentials.unit.unit_id,
                                     self.credentials.user.user_id,
                                     self.originator_id, self.assigner_id)

    def set_params(self, db, queue_id=None, active_date=None, due_date=None, 
                   task_description=None, annotation=None, form_name=None):
        if queue_id is not None:
            self.set_queue_id(db, queue_id)
        if active_date is not None:
            self.active = datetime.to_discrete(active_date) 
        if due_date is not None:
            self.due = datetime.to_discrete(due_date) 
        if task_description is not None:
            self.task_description = task_description
        if annotation is not None:
            self.annotation = annotation
        if form_name is not None:
            self.form_name = form_name

    def _update(self, db, inplace=False, complete=False):
        if inplace:
            # Update in place
            task = self._locked_fetch(db, self.seed_task_id, self.this_user_id)
            if task is None:
                raise TaskError('Update failed - the task has been changed'
                                ' by another user')
            _set_unlocked(task)
            _clear_completed(task)
        else:
            # Create a new task, closing the old one if necessary.
            if self.seed_task_id is not None:
                task = self._locked_fetch(db, self.seed_task_id)
                if _our_lock(task, self.this_user_id):
                    _set_unlocked(task)
                _set_completed(task, self.this_user_id)
                task.db_update()
            task = db.new_row('tasks')
            task.parent_task_id = self.seed_task_id
            task.creation_date = datetime.now()
        self._copy(self, task)
        if not self.task_description or not self.task_description.strip():
            raise TaskError('Task must have a description')
        old_due = None
        if task.due_date and task.active_date:
            old_due = task.due_date - task.active_date
        if self.active_abs and self.active_abs.strip():
            try:
                active_abs = datetime.mx_parse_datetime(self.active_abs)
            except datetime.Error, e:
                raise TaskError('Start date: %s' % e)
            if not datetime.near(active_abs, task.active_date):
                task.active_date = active_abs
        elif self.active != 'nochange':
            task.active_date = datetime.parse_discrete(self.active)
        if self.due_abs and self.due_abs.strip():
            try:
                due_abs = datetime.mx_parse_datetime(self.due_abs)
            except datetime.Error, e:
                raise TaskError('Complete by date: %s' % e)
            if not datetime.near(due_abs, task.due_date):
                task.due_date = due_abs
        elif self.due != 'nochange':
            task.due_date = datetime.parse_discrete(self.due, task.active_date)
        if self.active != 'nochange' and self.due == 'nochange' and old_due:
            # If active date has changed, but due date has not, preserve the
            # relationship between the old active date and the old due date...
            task.due_date = task.active_date + old_due
        _set_assigned(task, self.this_user_id)
        task.queue_id = self.assignee.get_queue_id(db)
        if complete:
            _set_completed(task, self.this_user_id)
        assert task.assigner_id is not None
        task.db_update()
        if not complete and self.repeat != 'none':
            try:
                repeatcount = int(self.repeatcount)
            except ValueError:
                raise TaskError('invalid repeat count')
            repeat_delta = self.repeat_delta_map[self.repeat]
            for n in xrange(1, repeatcount):
                task = task.db_clone()
                task.active_date += repeat_delta
                if task.due_date:
                    task.due_date += repeat_delta
                task.db_update()
        globals.notify.notify('taskdesc')

    def update(self, db):
        # Fix up types from web interaction
        if self.form_name == 'None':
            self.form_name = None
        if self.summary_id == 'None' or not self.form_name:
            self.summary_id = None
        self.action = guess_action(self)
        self._update(db, inplace=self.inplace)

    def close(self, db):
        self.form_name = self.summary_id = None
        self.action = ACTION_THREAD_COMPLETED
        self._update(db, complete=True, inplace=False)

    def delete(self, db):
        self.form_name = self.summary_id = None
        self.action = ACTION_THREAD_DELETED
        self._update(db, complete=True, inplace=True)


class UnlockedTask(_TaskBase):
    def __init__(self, db, credentials, task_id):
        self.task_id = task_id
        task = self._fetch(db, self.task_id)
        self._copy(task, self)

class LockedTask(_TaskBase):
    def __init__(self, db, credentials, task_id):
        self.user_id = credentials.user.user_id
        self.task_id = task_id
        self.done = False
        task = self._locked_fetch(db, self.task_id)
        self._copy(task, self)
        self.assigner = unituser.users[task.assigner_id]
        self.was_locked = None
        if task.locked_by_id is not None and task.locked_by_id != self.user_id:
            username = unituser.users[task.locked_by_id].username
            self.was_locked = '%s %s' % (username,
                                         datetime.relative(task.locked_date))
        task.locked_by_id = self.user_id
        task.locked_date = datetime.now()
        task.db_update()

    def unlock(self, db):
        task = self._locked_fetch(db, self.task_id, self.user_id)
        if task is None:
            return
        _set_unlocked(task)
        task.db_update()

    def same_entity(self, action, case_id, form_name=None, summary_id=None):
        return same_entity(self, action, case_id, form_name, summary_id)

    def entity_update(self, db, action, case_id,
                      form_name=None, summary_id=None):
        """
        When a case or form is updated, check if it is the subject
        of this task and note the fact by setting the "done" flag.
        
        If the case or form is new, update the task record with the
        record's primary key (turning a "create" request into an "edit"),
        so a subsequent edit will return to the newly created record,
        whether the task is is completed or not.
        """
        task = self._locked_fetch(db, self.task_id, self.user_id)
        if task is None:
            return
        if not same_entity(task, action, case_id, form_name, summary_id):
            return
        self.done = True
        task.case_id = self.case_id = case_id
        task.form_name = self.form_name = form_name
        task.summary_id = self.summary_id = summary_id
        task.db_update()
