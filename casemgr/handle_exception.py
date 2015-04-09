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
import os
import sys
import config
import albatross
import sendmail
import notify
import version

def simple_template(req, template_path, template_name, locals_dict = {}):
    class LocalsDict:
        def __init__(self, locals_dict):
            self.__dict__ = locals_dict

    req.set_status(albatross.HTTP_INTERNAL_SERVER_ERROR)
    req.write_header('Content-Type', 'text/html')
    req.end_headers()
    tmp_ctx = albatross.SimpleContext(template_path)
    tmp_ctx.locals = LocalsDict(locals_dict)
    templ = tmp_ctx.load_template(template_name)
    templ.to_html(tmp_ctx)
    tmp_ctx.flush_content()


class ExcMsg(list):
    def safeadd(self, label, value):
        if not value:
            value = '[unknown]'
        if len(value) > 200:
            value = value[:200] + '...'
        self.append('  %-15s: %s' % (label, value))
            

def session_limit():
    limit = (config.session_timeout / 60.0) or 20
    if limit >= 120:
        return '%.0f hours' % (limit / 60.0)
    return '%.0f minutes' % limit


class HandleExceptionMixin:

    def handle_exception(self, ctx, req):
        user = rights = page_stack = deploy_mode = None
        double_trap = True
        if ctx:
            if ctx.locals.__page__:
                page_stack = '>'.join(ctx.locals.__pages__ + [ctx.locals.__page__])
            double_trap = getattr(ctx.locals, 'double_trap', True)
            if hasattr(ctx.locals, '_credentials'):
                creds = ctx.locals._credentials
                user = creds.user.username
#                rights = str(creds.rights)
            deploy_mode = getattr(ctx.locals, 'deploy_mode', None)
            if not config.debug:
                self.remove_session(ctx)
        exc_type = sys.exc_info()[0]
        if exc_type == albatross.SessionExpired:
            simple_template(req, 'pages', 'nocookies.html', vars(config))
        elif exc_type == albatross.ServerError:
            simple_template(req, 'pages', 'shutdown.html', vars(config))
        else:
            try:
                body = ExcMsg()
                body.append('Environment:')
                body.safeadd('User', user)
#                body.safeadd('User rights', rights)
                body.safeadd('Remote IP', req.get_remote_host())
                body.safeadd('User agent', req.get_user_agent())
                body.safeadd('App vers', version.__version__)
                body.safeadd('SVN rev', version.__svnrev__)
                body.safeadd('Py vers', sys.version.replace('\n', ''))
                body.safeadd('Albatross vers', albatross.__version__)
                body.safeadd('Page stack', page_stack)
                body.safeadd('Deploy mode', deploy_mode)
                pyexc, htmlexc = self.format_exception()
                body.append('')
                body.append(htmlexc)
                body.append('')
                body.append(pyexc)
            except:
                body = None
                sys.stderr.write('Uncaught exception, exception in '
                                'exception handler: %s\n' % sys.exc_info()[1])
            else:
                sys.stderr.write('\n'.join(body))

#            double_trap = 1
            if not double_trap:
                try:
                    # Albatross needs to expose method to clear the page stack
                    ctx.locals.__page__ = None
                    ctx.locals.__pages__ = []
                    ctx.add_error('WARNING - An application error has occurred, attempting to continue...')
                    ctx.set_page('main')
                    ctx.reset_content()
                    self.load_page(ctx)
                    self.display_response(ctx)
                    self.save_session(ctx)
                    ctx.flush_content()
                except Exception:
                    double_trap = True
            if double_trap:
                simple_template(req, 'pages', 'traceback.html', vars(config))

            if body:
                notify.exception_notify(body)
