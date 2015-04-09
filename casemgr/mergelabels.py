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

class MergeLabels:
    """
    Manage a set of name/label pairs, merging labels when names collide.
    """
    def __init__(self):
        self.label_map = {}
        self.name_order = []

    def add(self, name, label):
        try:
            other = self.label_map[name]
        except KeyError:
            self.name_order.append(name)
        else:
            if other != label:
                label = '%s/%s' % (other, label)
        self.label_map[name] = label

    def addall(self, pairs):
        for name, label in pairs:
            self.add(name, label)

    def in_order(self):
        return [(name, self.label_map[name]) for name in self.name_order]

    def label_order(self):
        pairs = [(self.label_map[name], name) 
                 for name in self.name_order if name]
        pairs.sort()
        pairs = [(name, label) for label, name in pairs]
        if '' in self.label_map:
            pairs.insert(0, ('', self.label_map['']))
        return pairs
