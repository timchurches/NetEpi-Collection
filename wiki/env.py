# -*- coding: iso-8859-1 -*-
#
# Copyright (C) 2003-2005 Edgewall Software
# Copyright (C) 2003-2005 Jonas Borgström <jonas@edgewall.com>
# All rights reserved.
#
# This software is licensed as described in the file Trac_licence.txt, which
# you should have received as part of this distribution. The terms
# are also available at http://trac.edgewall.com/license.html.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://projects.edgewall.com/trac/.
#
# Author: Jonas Borgström <jonas@edgewall.com>

from __future__ import generators

import os
from ConfigParser import SafeConfigParser

from wiki.core import Component, ComponentManager, implements, Interface, \
                      ExtensionPoint, TracError

__all__ = ['Environment']


class Environment(Component, ComponentManager):
    """An environment is a trac framework wrapper for a context object """   
    def __init__(self, ctx):
        """Initialize the environment.
        
        @param ctx:    the context object
        """
        ComponentManager.__init__(self)

        self.ctx = ctx
        #self.load_config()
        #self.setup_log()

        #from trac.loader import load_components
        #load_components(self)

    def _get_config(self):
        # The context has everything in the config placed into it
        return self.ctx.config
    config = property(_get_config)

    def component_activated(self, component):
        """Initialize additional member variables for components.
        
        Every component activated through the `Environment` object gets three
        member variables: `env` (the environment object), `config` (the
        environment configuration) and `log` (a logger object)."""
        component.env = self
        component.config = self.config
        #component.log = self.log

    def is_component_enabled(self, cls):
        """Implemented to only allow activation of components that are not
        disabled in the configuration.
        
        This is called by the `ComponentManager` base class when a component is
        about to be activated. If this method returns false, the component does
        not get activated."""
        if not isinstance(cls, (str, unicode)):
            component_name = (cls.__module__ + '.' + cls.__name__).lower()
        else:
            component_name = cls.lower()

        rules = [(name.lower(), value.lower() in ('enabled', 'on'))
                 for name, value in self.config.options('components')]
        rules.sort(lambda a, b: -cmp(len(a[0]), len(b[0])))

        for pattern, enabled in rules:
            if component_name == pattern or pattern.endswith('*') \
                    and component_name.startswith(pattern[:-1]):
                return enabled

        # By default, all components in the trac package are enabled
        return component_name.startswith('trac.')

    def get_db_cnx(self):
        """Return a database connection from the connection pool."""
        raise NotImplementedError

    def shutdown(self):
        """Close the environment."""
        pass

    def get_version(self, db=None):
        """Return the current version of the database."""
        raise NotImplementedError

    def load_config(self):
        """Load the configuration file."""
        self.config = SafeConfigParser()
        #for section, name, value in db_default.default_config:
        #    self.config.setdefault(section, name, value)

    def get_templates_dir(self):
        """Return absolute path to the templates directory."""
        raise NotImplementedError

    def get_htdocs_dir(self):
        """Return absolute path to the htdocs directory."""
        raise NotImplementedError

    def get_log_dir(self):
        """Return absolute path to the log directory."""
        raise NotImplementedError

    def setup_log(self):
        """Initialize the logging sub-system."""
        from log import logger_factory
        logtype = 'stderr' # self.config.get('logging', 'log_type')
        loglevel = 'WARNING' # self.config.get('logging', 'log_level')
        logfile = '/tmp/log' # self.config.get('logging', 'log_file')
        if not os.path.isabs(logfile):
            logfile = os.path.join(self.get_log_dir(), logfile)
        logid = self.config.appname # an ID
        self.log = logger_factory(logtype, logfile, loglevel, logid)

    def get_known_users(self, cnx=None):
        """Generator that yields information about all known users, i.e. users
        that have logged in to this Trac environment and possibly set their name
        and email.

        This function generates one tuple for every user, of the form
        (username, name, email) ordered alpha-numerically by username.

        @param cnx: the database connection; if ommitted, a new connection is
                    retrieved
        """
        return os.path.join(self.path, 'log')


