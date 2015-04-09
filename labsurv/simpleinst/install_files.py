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
import os
import stat
import errno
import tempfile
import re
from fnmatch import fnmatch
from simpleinst.config_register import args_with_defaults
from simpleinst.usergroup import user_lookup
from simpleinst.glob import glob
from simpleinst.filter import Filter
from simpleinst.utils import *

class PostInstallAction:
    def __init__(self, pattern, fn, args, kwargs):
        self.pattern = pattern
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def match(self, filename):
        return fnmatch(filename, self.pattern)

    def action(self, filename, verbose):
        if verbose:
            print '    %s(%s)' % (self.fn.__name__, filename)
        self.fn(filename, *self.args, **self.kwargs)

class PostInstallActions:
    def __init__(self, config):
        self.actions = []
        self.config = config

    def add(self, pattern, fn, *args, **kwargs):
        self.actions.append(PostInstallAction(pattern, fn, args, kwargs))

    def post_install(self, filename, verbose=False):
        for action in self.actions:
            if action.match(filename):
                action.action(filename, verbose=verbose)

post_install_actions = None

class FilenameFilter:
    def __init__(self, include, exclude):
        if type(include) in (str, unicode):
            include = [include]
        if type(exclude) in (str, unicode):
            exclude = [exclude]
        self.include_nop = not include
        self.exclude_nop = not exclude
        if not self.include_nop:
            self.path_include = [i for i in include if i.find(os.path.sep) >= 0]
            self.name_include = [i for i in include if i.find(os.path.sep) < 0]
        if not self.exclude_nop:
            self.path_exclude = [i for i in exclude if i.find(os.path.sep) >= 0]
            self.name_exclude = [i for i in exclude if i.find(os.path.sep) < 0]
    
    def include(self, name):
        basename = os.path.basename(name)

        if not self.exclude_nop:
            if basename != name:
                for exclude in self.path_exclude:
                    if fnmatch(name, exclude):
                        return False
            for exclude in self.name_exclude:
                if fnmatch(basename, exclude):
                    return False

        if self.include_nop:
            return True

        if basename != name:
            for include in self.path_include:
                if fnmatch(name, include):
                    return True
        for include in self.name_include:
            if fnmatch(basename, include):
                return True

        return False

def copy(src, dst, 
         owner = None, mode = None, filter = None, verbose = False,
         bufsize = 1 << 22):
    dst_dir = os.path.dirname(dst)
    make_dirs(dst_dir, owner)
    r_fd = os.open(src, os.O_RDONLY)
    try:
        st = os.fstat(r_fd)
        try:
            dst_st = os.stat(dst)
        except OSError, (eno, estr):
            if eno != errno.ENOENT:
                raise
        else:
            # Same file? utime almost matches, and size matches...
            if (abs(st.st_mtime - dst_st.st_mtime) <= 1 and
                st.st_size == dst_st.st_size):
                return False
        w_fd, tmp_filename = tempfile.mkstemp(dir = dst_dir)
        try:
            while 1:
                buf = os.read(r_fd, bufsize)
                if not buf:
                    break
                if filter:
                    if len(buf) == bufsize:
                        raise IOError('Can\'t filter files larger than %s' %
                                        bufsize - 1)
                    for f in filter:
                        buf = f.filter(buf)
                os.write(w_fd, buf)
            if mode:
                chmod(tmp_filename, mode)
            else:
                os.chmod(tmp_filename, st.st_mode & 0777)
            if owner:
                os.chown(tmp_filename, *owner)
            os.rename(tmp_filename, dst)
            os.utime(dst, (st.st_atime, st.st_mtime))
            if verbose:
                print '    %s -> %s' % (src, dst_dir)
            tmp_filename = None
            return True
        finally:
            os.close(w_fd)
            if tmp_filename:
                os.unlink(tmp_filename)
    finally:
        os.close(r_fd)

def recursive_copy(args, src):
    fullsrc = normjoin(args.base, src)
    src_path, src_file = os.path.split(src)
    st = os.stat(fullsrc)
    if stat.S_ISDIR(st.st_mode):
        for filename in os.listdir(fullsrc):
            recursive_copy(args, os.path.join(src, filename))
    else:
        if not args.filename_filter.include(src):
            return
        dst = normjoin(args.target, src)
        if copy(fullsrc, dst, filter = args.filter,
                owner = args.owner, mode = args.mode, 
                verbose = args.verbose) and post_install_actions:
            post_install_actions.post_install(dst, verbose=args.verbose)

def install(config, **kwargs):
    args = args_with_defaults(kwargs, config, 
                              ('target', 'base', 'files', 'owner', 'mode', 
                               'include', 'exclude', 'filter'),
                              conf_prefix = 'install_')

    if type(args.files) in (str, unicode):
        args.files = [args.files]
    if isinstance(args.filter, Filter):
        args.filter = [args.filter]
    if config.install_prefix:
        args.target = config.install_prefix + args.target
    args.verbose = getattr(config, 'install_verbose')
    args.filename_filter = FilenameFilter(args.include, args.exclude)
    if args.base:
        args.base = normjoin(config.base_dir, args.base)
    else:
        args.base = config.base_dir
    args.owner = user_lookup(args.owner)

    for pat in args.files:
        print 'installing %s to %s' % (normjoin(args.base, pat), args.target)
        for src in glob(args.base, pat):
            recursive_copy(args, src)

def on_install(config, pattern, fn, *args, **kwargs):
    global post_install_actions
    if post_install_actions is None:
        post_install_actions = PostInstallActions(config)
    post_install_actions.add(pattern, fn, *args, **kwargs)
