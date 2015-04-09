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

class Spacer(object):
    spacer = True

class Tab(object):
    spacer = False

    def __init__(self, tabs, name, label, 
                 action=False, danger=True, accesskey=None):
        self.tabs = tabs
        self.name = name
        self.label = label
        self.action = action
        self.danger = danger
        self.accesskey = accesskey
        if self.action:
            self.nameexpr = self.name
        else:
            self.nameexpr = 'tab:' + self.name

    def selected(self):
        return self.name == self.tabs.selected

    def css_class(self):
        style = 'tab'
        if self.danger:
            style += ' danger'
        if self.action:
            style += ' act'
        if self.name == self.tabs.selected:
            style += ' selected'
        return style


class Tabs(list):
    def __init__(self, initial=None):
        self.accesskeys = {}
        self.selected = initial
        self.width = None

    def add(self, name, label, action=False, danger=False, accesskey=None):
        """
        An "action" is a button that leaves the context of the tab system
        """
        self.append(Tab(self, name, label, action, danger, accesskey))

    def spacer(self):
        self.append(Spacer())

    def select(self, name):
        """
        Attempt to select the requested tab. If not found, select the
        first tab.
        """
        first = None
        for tab in self:
            if not tab.spacer and tab.name:
                if first is None:
                    first = tab.name
                if tab.name == name:
                    break
        else:
            name = first
        self.selected = name

    def done(self):
        self.select(self.selected)      # Force valid selection
        if self:
            widths = []
            for tab in self:
                if not tab.spacer:
                    widths.append(len(tab.label))
                    if tab.accesskey is None:
                        for l in tab.label:
                            l = l.lower()
                            if l.isalpha() and l not in self.accesskeys:
                                self.accesskeys[l] = tab
                                tab.accesskey = l
                                break
            self.width = max(widths)
        return self

    def css_width(self):
        style = []
        if self.width:
            # Only an approximation with proportional width fonts
            style.append('width: %.1fem;' % (self.width * .6))
        return ''.join(style)
