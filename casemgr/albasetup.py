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

#
# WARNING - this module relies on deep knowledge of how Albatross works, and
# the assumptions made by Albatross, and overrides and extends parts of
# Albatross functionality. In particular, we dynamically create the application
# and context classes out of the lower level Albatross mixin classes.  This is
# done to allow the application to be easily deployed in a number of ways, and
# to record information that would otherwise be discarded or inaccessible.
#

# Standard Libraries
import new
import os
import sys
import socket
import errno
import time

# 3rd Party
from albatross import ModularSessionApp, SessionAppContext, \
                      ModularApp, SimpleAppContext, Redirect
try:
    have_branching_session = True
    from albatross import BranchingSessionContext
except ImportError:
    have_branching_session = False

# Application
from cocklebur import dbobj, datetime, utils
from casemgr import globals, credentials, messages
from casemgr import version
from handle_exception import HandleExceptionMixin
from wiki.env import Environment
from wiki.href import Href
from wiki.formatter import wiki_to_html, wiki_to_oneliner


def is_fcgi():
    # If there's a better way of detecting a FastCGI environment, I'd love to
    # hear it.
    try:
        s=socket.fromfd(sys.stdin.fileno(), socket.AF_INET,
                        socket.SOCK_STREAM)
    except socket.error:
        return False
    try:
        try:
            s.getpeername()
        except socket.error, (eno, errmsg):
            return eno == errno.ENOTCONN
    finally:
        s.close()


class RequestMixin:

    def get_remote_addr(self):
        # Remote host - may be intermediate firewall, etc
        return self.get_param('REMOTE_ADDR', 'unknown')

    def get_forwarded_addr(self):
        forwarded_addr = (self.get_header('X-Forwarded-For') or 
                          self.get_header('Forwarded'))
        if forwarded_addr:
            return utils.safeprint(forwarded_addr[:80])  # Untrusted data

    def get_remote_host(self):
        remote_addr = self.get_remote_addr()
        forwarded_addr = self.get_forwarded_addr()
        if forwarded_addr:
            return '%s via %s' % (forwarded_addr, remote_addr)
        else:
            return remote_addr

    def get_user_agent(self):
        return self.get_header('User-Agent')


if is_fcgi():
    try:
        from albatross import fcgiappnew as fcgiapp
        print >> sys.stderr, '***** WARNING - using experimental "fcgiappnew"'
    except ImportError:
        from albatross import fcgiapp

    class Request(RequestMixin, fcgiapp.Request):
        pass

    if not hasattr(Request, 'get_param'):
        # Monkey patch old versions of Albatross < v1.35
        def get_param(self, key, default=None):
            return self._Request__fcgi.env.get(key, default)
        Request.get_param = get_param

    def next_request():
        while fcgiapp.running():
            yield Request()

    deploy_mode = 'fcgi'
else:
    from albatross import cgiapp

    class Request(RequestMixin, cgiapp.Request):
        pass

    if not hasattr(Request, 'get_param'):
        # Monkey patch old versions of Albatross < v1.35
        def get_param(self, key, default=None):
            return os.environ.get(key, default)
        Request.get_param = get_param

    def next_request():
        yield Request()

    deploy_mode = 'cgi'


class ProfilerMixin:

    def run(self, req):
        '''
        Process a single browser request
        Copied from albatross.app - only do this for profiling!
        '''
        ctx = None
        t = time.time()
        try:
            ctx = self.create_context()
            self.profiler.done('create_context')
            ctx.set_request(req)
            self.load_session(ctx)
            self.profiler.done('load_session')
            self.load_page(ctx)
            self.profiler.done('load_page')
            if self.validate_request(ctx):
                self.merge_request(ctx)
                self.process_request(ctx)
            self.profiler.done('validate, merge, process')
            self.display_response(ctx)
            self.profiler.done('display_response')
            self.save_session(ctx)
            self.profiler.done('save_session')
            ctx.flush_content()
            self.profiler.done('flush_content')
        except Redirect, e:
            self.save_session(ctx)
            return ctx.send_redirect(e.loc)
        except:
            self.handle_exception(ctx, req)
        return req.return_code()


# A new Context is created for each request
class CommonAppContext(messages.MessageMixin):

    def __init__(self, app):
        self.__config_vars = app.config_vars
        self.__config = app.config
        self.init_locals()
        self.set_header('Cache-Control', 'no-cache, no-store')
        self.set_header('Content-Type', 'text/html; charset=utf-8')
        self.run_template_once('page_layout.html')
        self.locals.via_logout = False
        self.clear_messages()

    def log(self, msg, *args):
        args = [repr(a) for a in args]
        print >> sys.stderr, 'LOG:', msg, ' '.join(args)

    def request_elapsed(self):
        return time.time() - self.locals.request_start

    def appath(self, *args):
        return '/'.join(('', self.locals.appname) + args)

    def wiki_text(self, text):
        env = Environment(self.app)
        env.href = Href(self.__config.appname)
        text = wiki_to_html(text, env).strip()
        # FIXME: This will cause badly formed xhtml which we may be concerned
        # about at some point
        if text.startswith("<p>"):
            #text = text[3:]
            text = '<div class="wikitext">%s</div>' % text
        return text

    def wiki_oneliner(self, text):
        env = Environment(self.app)
        env.href = Href(self.__config.appname)
        return wiki_to_oneliner(text, env)

    def init_locals(self):
        self.locals.request_start = time.time()
        for attr in ('request_elapsed', 'appath', 'wiki_text', 'wiki_oneliner'):
            setattr(self.locals, attr, getattr(self, attr))
        for attr in self.__config_vars:
            setattr(self.locals, attr, getattr(self.__config, attr))
        self.locals.__version__ = version.__version__
        self.locals.__svnrev__ = version.__svnrev__
        self.locals.__pyver__ = sys.version.split(None, 1)[0]
        self.locals.deploy_mode = deploy_mode
        self.locals.get_messages = self.get_messages
        self.locals.have_errors = self.have_errors

    def user_log(self, event_type, **kw):
        self.locals._credentials.user_log(globals.db, event_type, **kw)

    def admin_log(self, event_type):
        self.locals._credentials.admin_log(globals.db, event_type)

    def logout(self):
        self.remove_session()
        self.init_locals()
        self.locals.via_logout = True
        self.set_page('login')


def call_all(meth_name):
    def _call_all(self, *args):
        for base in self.__class__.__bases__:
            try:
                meth = getattr(base, meth_name)
            except AttributeError:
                pass
            else:
                meth(self, *args)
    return _call_all


def get_app(config, config_vars, profiler=None, ctx_mixins=None, **kwargs):
    app_bases = [HandleExceptionMixin]
    if ctx_mixins:
        ctx_bases = list(ctx_mixins)
    else:
        ctx_bases = []
    if profiler:
        app_bases.append(ProfilerMixin)
    if config.session_server:
        try:
            sess_serv_host, sess_serv_port = config.session_server.split(':')
        except ValueError:
            sess_serv_host, sess_serv_port = config.session_server, 34343
        else:
            try:
                sess_serv_port = int(sess_serv_port)
            except ValueError:
                sys.exit('bad session server port specification: %s' % 
                         sess_serv_port)
        kwargs['session_appid'] = config.appname
        kwargs['session_server'] = sess_serv_host
        kwargs['server_port'] = sess_serv_port
        if config.session_timeout:
            kwargs['session_age'] = int(config.session_timeout)
        else:
            kwargs['session_age'] = 600
        app_bases.append(ModularSessionApp)
        if have_branching_session:
            ctx_bases.append(BranchingSessionContext)
        else:
            ctx_bases.append(SessionAppContext)
    else:
        app_bases.append(ModularApp)
        ctx_bases.append(SimpleAppContext)
    ctx_bases.append(CommonAppContext)
    kwargs['secret'] = config.session_secret
    # This is a *little* gross... create a class on the fly
    ctx_cls = new.classobj('AlbaCtx', tuple(ctx_bases), 
                           dict(__init__=call_all('__init__')))
    def create_context(self):
        return ctx_cls(self)
    app_cls = new.classobj('AlbaApp', tuple(app_bases), 
                           dict(create_context=create_context))
    app = app_cls(**kwargs)
    if profiler:
        app.profiler = profiler
    app.config = config
    app.config_vars = config_vars
    return app
