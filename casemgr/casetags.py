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

import re

from cocklebur.compat import *
from cocklebur import utils
from casemgr import globals, mergelabels, cached

class InvalidTags(globals.Error): pass


def edit_tag(tag_id):
    row = None
    if tag_id:
        query = globals.db.query('tags')
        query.where('tag_id = %s', int(tag_id))
        row = query.fetchone()
    if row is None:
        row = globals.db.new_row('tags')
    return row

valid_tag_re = re.compile(r'^[a-zA-Z0-9_+-]+$')

def check_tag(row):
    if not valid_tag_re.match(str(row.tag)):
        raise InvalidTags('Tag names can only contain upper and lower case letters, numbers, underscore (_) and hypen (-)')
    tag = tags_from_str(row.tag)
    if not tag:
        raise InvalidTags('Tag must not be null')
    if len(tag) > 1:
        raise InvalidTags('Invalid tag name')
    row.tag = row.tag.upper()


class TagCacheItem(object):

    cols = 'tag_id', 'tag', 'notes'

    def __init__(self, row):
        for col, value in zip(self.cols, row):
            setattr(self, col, value)


class TagCache(cached.NotifyCache, list):

    notification_target = 'tags'

    def __hash__(self):
        return id(self)

    def load(self):
        query = globals.db.query('tags', order_by='tag')
        self[:] = [TagCacheItem(row) 
                   for row in query.fetchcols(TagCacheItem.cols)]
        self.by_tag = {}
        for tag in self:
            self.by_tag[tag.tag.upper()] = tag

tag_cache = TagCache()


def tags():
    tag_cache.refresh()
    return tag_cache


def notify():
    """
    Invalidate local and remote tag caches
    """
    tag_cache.cache_invalidate()
    globals.notify.notify('tags')


def use_count(tag_id):
    """
    Count cases associated with /tag_id/
    """
    query = globals.db.query('case_tags')
    query.where('tag_id = %s', tag_id)
    return query.aggregate('count(case_id)')


def delete_tag(tag_id):
    """
    Delete the specified tag
    """
    assert tag_id
    query = globals.db.query('tags')
    query.where('tag_id = %s', tag_id)
    query.delete()


class Tags(set):
    """
    A set-derived collection of tags
    """

    def __str__(self):
        return ' '.join(sorted(self))

    def ids(self):
        tag_cache.refresh()
        return [tag_cache.by_tag[tag.upper()].tag_id for tag in self]

    def validate(self):
        tag_cache.refresh()
        return [tag for tag in self if tag.upper() not in tag_cache.by_tag]

splitre = re.compile(r'[\s/,]*')

def tags_from_str(buf):
    """
    Return a Tags (set of tags) given a space or comma delimited string of tags
    """
    if buf is None:
        return Tags()
    if isinstance(buf, Tags):
        return buf
    tags = Tags()
    for tag in splitre.split(buf.strip()):
        if tag:
            tags.add(tag.upper())
    return tags


def case_tags(case_id, for_update=False):
    """
    Return a Tags (set of tags) associated with the specified case
    """
    if not case_id:
        return Tags()
    query = globals.db.query('tags', for_update=for_update)
    query.join('JOIN case_tags USING (tag_id)')
    query.where('case_id = %s', case_id)
    return Tags(query.fetchcols('tag'))


class CasesTags(dict):
    """
    Efficiently load tags associated with multiple case ids,
    producing a dict of Tags indexed by case id.
    """

    def __init__(self, case_ids):
        query = globals.db.query('case_tags')
        query.join('JOIN tags USING (tag_id)')
        query.where_in('case_id', case_ids)
        for case_id, tag in query.fetchcols(('case_id', 'tag')):
            try:
                tags = self[case_id]
            except KeyError:
                tags = self[case_id] = Tags()
            tags.add(tag)


def desc_changes(old, new):
    desc = []
    for del_tag in old - new:
        desc.append('-' + del_tag)
    for add_tag in new - old:
        desc.append('+' + add_tag)
    if desc:
        return 'tags: ' + ' '.join(desc)


def set_case_tags(case_id, tags):
    tags = tags_from_str(tags)
    bad_tags = tags.validate()
    if bad_tags:
        bad_tags.sort()
        bad_tags = utils.commalist(bad_tags, 'and')
        raise InvalidTags('Invalid tag(s): %s' % bad_tags)
    cur_tags = case_tags(case_id, for_update=True)
    del_tags = cur_tags - tags
    if del_tags:
        del_ids = del_tags.ids()
        query = globals.db.query('case_tags')
        query.where('case_id = %s', case_id)
        query.where_in('tag_id', del_ids)
        query.delete()
    add_tags = tags - cur_tags
    if add_tags:
        for id in add_tags.ids():
            row = globals.db.new_row('case_tags')
            row.case_id = case_id
            row.tag_id = id
            row.db_update(refetch=False)
    return desc_changes(cur_tags, tags)


class CaseTags:
    """
    A helper for case editing - tracks "changed" status and can generate
    a list of field edits (desc).
    """

    def __init__(self, case_id):
        self.initial = self.cur = case_tags(case_id)

    def normalise(self):
        if not isinstance(self.cur, Tags):
            self.cur = tags_from_str(self.cur)

    def has_changed(self):
        self.normalise()
        return self.initial != self.cur

    def update(self, case_id):
        if self.has_changed():
            set_case_tags(case_id, self.cur)
            # If a rollback occurs, we will be out of sync...
            self.initial = self.cur

    def desc(self):
        self.normalise()
        return desc_changes(self.initial, self.cur)
