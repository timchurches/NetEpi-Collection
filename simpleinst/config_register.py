#
#   The contents of this file are subject to the HACOS License Version 1.2
#   (the "License"); you may not use this file except in compliance with
#   the License.  Software distributed under the License is distributed
#   on an "AS IS" basis, WITHOUT WARRANTY OF ANY KIND, either express or
#   implied. See the LICENSE file for the specific language governing
#   rights and limitations under the License.  The Original Software
#   is "SimpleInst". The Initial Developer of the Original
#   Software is the Health Administration Corporation, incorporated in
#   the State of New South Wales, Australia.  Copyright (C) 2004 Health
#   Administration Corporation. All Rights Reserved.
#

import sys
import os
import imp
import tempfile
import bisect
import fnmatch
from simpleinst.utils import chown, chmod, normjoin, make_dirs

class ConfigBase:
    pass


class ConfigAttrs(ConfigBase):
    config_source = 'Installer'


class ConfigCmdLine(ConfigBase):
    """
    Parse the command line, infering types from prior config (defaults)
    """
    config_source = 'Command Line'

    def __init__(self, config):
        for arg in sys.argv[1:]:
            try:
                a, v = arg.split('=')
            except ValueError:
                sys.exit('Unknown command line option: %r' % arg)
            try:
                t = type(getattr(config, a))
            except AttributeError:
                pass
            else:
                if t is bool:
                    v = v.lower() in ('t', 'true', 'y', 'yes', '1')
                else:
                    try:
                        v = t(v)
                    except (ValueError, TypeError):
                        pass
            setattr(self, a, v)


class Config:
    def __init__(self):
        self._sources = []
        self._config_attrs = ConfigAttrs()

    def source(self, prio, source):
        assert source
        pair = prio, source
        i = bisect.bisect(self._sources, pair)
        self._sources.insert(i, pair)

    def source_attrs(self, prio):
        self.source(prio, self._config_attrs)

    def source_file(self, prio, name='config', path='', exclude=None):
        if not os.path.isabs(path):
            path = normjoin(self.base_dir, path)
        try:
            f, filename, extras = imp.find_module(name, [path])
        except ImportError, e:
            return
        config_mod = imp.load_module(name, f, filename, extras)
        config_mod.config_source = filename
        if exclude:
            for attr in exclude:
                try:
                    delattr(config_mod, attr)
                except AttributeError:
                    pass
        self.source(prio, config_mod)

    def source_cmdline(self, prio):
        self.source(prio, ConfigCmdLine(self))

    def __getattr__(self, a):
        for prio, source in self._sources:
            try:
                return getattr(source, a)
            except AttributeError:
                pass
        raise AttributeError('attribute "%s" not found' % a)

    def __setattr__(self, a, v):
        if a.startswith('_'):
            self.__dict__[a] = v
        else:
            setattr(self._config_attrs, a, v)

    def _config_dict(self):
        """
        Produce a dictionary of the current config
        """
        class _ConfigItem(object):
            __slots__ = 'value', 'source'

            def __init__(self, value, source):
                self.value = value
                self.source = source

        config = {}
        for prio, source in self._sources:
            for a in dir(source):
                if not config.has_key(a) and not a.startswith('_') \
                    and a != 'config_source':
                    v = getattr(source, a)
                    if not callable(v):
                        config[a] = _ConfigItem(v, source.config_source)
        return config

    def write_file(self, filename, exclude=None, owner=None, mode=None):
        if not exclude:
            exclude = ()
        config = self._config_dict()
        if self.install_prefix:
            filename = self.install_prefix + filename
        target_dir = os.path.dirname(filename)
        make_dirs(target_dir, owner=owner)
        fd, tmpname = tempfile.mkstemp(dir=target_dir)
        f = os.fdopen(fd, 'w')
        attributes = config.keys()
        attributes.sort()
        try:
            for a in attributes:
                for e in exclude:
                    if fnmatch.fnmatch(a, e):
                        break
                else:
                    f.write('%s=%r\n' % (a, config[a].value))
            f.flush()
            if owner is not None:
                chown(tmpname, owner)
            if mode is not None:
                chmod(tmpname, mode)
            os.rename(tmpname, filename)
        finally:
            f.close()
            try:
                os.unlink(tmpname)
            except OSError:
                pass

    def __str__(self):
        srcs = ';'.join(['%s[%s]' % (s.config_source, p)
                         for p, s in self._sources])
        config = self._config_dict()
        attrs = config.keys()
        attrs.sort()
        attrs = ['\n    %s=%r (from %s)' % (a,config[a].value,config[a].source) 
                 for a in attrs]
        return '<%s %s%s>' % (self.__class__.__name__, srcs, ''.join(attrs))

class Args:
    pass

def args_with_defaults(kwargs, config, arglist, conf_prefix = ''):
    args = Args()
    for argname in arglist:
        try:
            value = kwargs[argname]
        except KeyError:
            try:
                value = getattr(config, conf_prefix + argname)
            except AttributeError:
                try:
                    value = getattr(config, argname)
                except AttributeError:
                    value = None
        setattr(args, argname, value)
    return args
