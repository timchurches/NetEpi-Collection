#!/usr/bin/python
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
#   Copyright (C) 2004-2011 Health Administration Corporation and others. 
#   All Rights Reserved.
#
#   Contributors: See the CONTRIBUTORS file for details of contributions.
#

# Standard libraries
import csv

# 3rd party libs
from albatross import SimpleApp, SimpleAppContext
from albatross.fcgiapp import Request, running
# mxTools
from mx import DateTime

# Application modules
from labsurv import labsurv, pcode, dbapi
import config

dbapi.execute_debug(config.tracedb)

class PageError(Exception): pass

class PageBase:

    def new_report(self, ctx):
        user = ctx.request.get_param('REMOTE_USER')
        ctx.locals.report = labsurv.LabSurv(user)

    def page_display(self, ctx):
        ctx.run_template(self.name + '.html')

    def do_back(self, ctx, ignore):
        ctx.pop_page()

    def page_process(self, ctx):
        for field_name in ctx.request.field_names():
            # <input type="image"> returns fieldname.x and fieldname.y
            if field_name.endswith('.x'):
                field_name = field_name[:-2]
            elif field_name.endswith('.y'):
                continue
            fields = field_name.split(':')
            meth_name = fields.pop(0)
            try:
                meth = getattr(self, 'do_' + meth_name)
            except AttributeError:
                continue
            if not fields:
                value = getattr(ctx.locals, field_name, None)
                if isinstance(value, list):
                    for v in value:
                        if v:
                            value = v
                            break
                if value:
                    fields = [value]
            if fields:
                try:
                    if meth(ctx, *fields):
                        return True
                except (PageError, labsurv.ReportError), e:
                    ctx.msg('err', str(e))
        return False


class WriteWrapper:
    # The CSV module wants a file-like object, when it really
    # just needs a write function - too late to fix it now!
    def __init__(self, writer):
        self.write = writer


class DatePage(PageBase):

    name = 'date'

    def page_enter(self, ctx):
        self.new_report(ctx)
        ctx.add_session_vars('report')

    def page_display(self, ctx):
        export = getattr(ctx.locals, 'export', None)
        if export:
            filename = '%s_%s_%s.csv' % (config.appname, ctx.locals.mode,
                                         DateTime.now().strftime('%Y%m%d-%H%M'))
            ctx.set_save_session(False)
            # IE will not download via SSL if caching is disabled. 
            # See: http://support.microsoft.com/?kbid=323308
            ctx.del_header('Cache-Control')
            ctx.del_header('Pragma')
            ctx.set_header('Content-Type', 'application/vnd.ms-excel')
            ctx.set_header('Content-Disposition', 
                           'attachment; filename="%s"' % filename)
            writer = csv.writer(WriteWrapper(ctx.send_content))
            writer.writerows(export)
        else:
            PageBase.page_display(self, ctx)

    def do_next(self, ctx, ignore):
        if ctx.locals.report.load():
            ctx.msg('info', 'Loaded existing report')
        ctx.push_page('totals')

    def do_export(self, ctx, mode):
        ctx.locals.mode = mode
        ctx.locals.export = ctx.locals.report.export(mode)



class TotalsPage(PageBase):

    name = 'totals'

    def do_back(self, ctx, ignore):
        ctx.locals.report.update_totals()
        ctx.pop_page()

    def do_next(self, ctx, ignore):
        ctx.locals.report.update_totals()
        ctx.push_page('details')


class DetailsPage(PageBase):

    name = 'details'

    def do_back(self, ctx, ignore):
        ctx.locals.report.update_diags()
        ctx.pop_page()

    def do_next(self, ctx, ignore):
        ctx.locals.report.update_diags()
        ctx.push_page('cases')


class CasesPage(PageBase):

    name = 'cases'

    def page_okay(self, ctx):
        errors = 0
        for case in ctx.locals.report.positive_case_page():
            try:
                case.check()
            except labsurv.ReportError, e:
                ctx.msg('err', 'Record %s: %s' % (case.idx + 1, e))
                errors += 1
        return not errors
    
    def do_back(self, ctx, ignore):
        ctx.locals.report.update_report()       # Notes
        if self.page_okay(ctx):
            ctx.locals.report.update_positive_cases()
            if not ctx.locals.report.prev_case_page():
                ctx.pop_page()

    def do_next(self, ctx, ignore):
        ctx.locals.report.update_report()       # Notes
        if self.page_okay(ctx):
            ctx.locals.report.update_positive_cases()
            if not ctx.locals.report.next_case_page():
                ctx.push_page('submit')


class SubmitPage(PageBase):

    name = 'submit'

    def do_submit(self, ctx, ignore):
        ctx.locals.report.submit()
        ctx.msg('info', 'Report submitted - Thank you.')
        self.new_report(ctx)
        ctx.pop_page('date')



def ajax(req):
    suburb = req.field_value('lookup_suburb')
    suburb = suburb.upper().replace('.', '').replace('-', '')
    if suburb.startswith('MT '):
        suburb = 'MOUNT ' + suburb[3:]
    req.write_header('Content-Type', 'text/html')
    req.end_headers()
    req.write_content('%r' % pcode.locality_to_postcode.get(suburb, ''))
    req.return_code()   # Defacto "end of request"


class AppContext(SimpleAppContext):
    
    def appath(self, *args):
        return '/'.join(('', self.locals.appname) + args)

    def msg(self, lvl, msg):
        self.locals.msgs.append((lvl, msg))


class App(SimpleApp):
    pages = DatePage, TotalsPage, DetailsPage, CasesPage, SubmitPage

    def __init__(self):
        SimpleApp.__init__(self,
                           base_url='app.py',
                           template_path='pages',
                           start_page='date',
                           secret=config.session_secret)
        for page_class in self.pages:
            self.register_page(page_class.name, page_class())

    def create_context(self):
        ctx = AppContext(self)
        for a, v in config.__dict__.iteritems():
            setattr(ctx.locals, a, v)
        ctx.locals.msgs = []
        ctx.locals.appath = ctx.appath
        ctx.run_template_once('macros.html')
        return ctx


app = App()


if __name__ == '__main__':
    while running():
        req = Request()
        if req.has_field('lookup_suburb'):
            ajax(req)
        else:
            app.run(req)
        dbapi.db.rollback()

