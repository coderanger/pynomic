#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import sys
import os
import logging
import re
import mimetypes
from copy import copy

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app, login_required
from google.appengine.ext.webapp import template
from google.appengine.ext import db
from google.appengine.api.urlfetch import fetch
from google.appengine.api import images, users
import jinja2

import _linecache
from db import DirEntry
from wrapper import MetaImporter, TemplateLoader

def _user(self):
    is_admin = users.is_current_user_admin()
    user = users.get_current_user()
    if user:
        url = users.create_logout_url(self.request.uri)
    else:
        user = None
        url = users.create_login_url(self.request.uri)
    return user, is_admin, url

class MainHandler(webapp.RequestHandler):
    
    def __init__(self):
        self.last_routes = []
        self.compiled_routes = []
        #self.jinja_env = jinja2.Environment(loader=TemplateLoader())
    
    def get(self, path='/'):
        self._handle('get', path)
    
    def post(self, path='/'):
        self._handle('post', path)
    
    def head(self, path='/'):
        self._handle('head', path)
    
    def _handle(self, handler_type, path='/'):
        import nomic.main
        handler = None
        groups = ()
        if not hasattr(nomic.main, 'routes'):
            reload(nomic.main)
            if not hasattr(nomic.main, 'routes'):
                raise Exception, 'Code invalid'
        self._compile_routes(nomic.main.routes)
        for regexp, handler_class in self.compiled_routes:
          match = regexp.match(self.request.path)
          if match:
            handler = handler_class()
            handler.initialize(self.request, self.response)
            groups = match.groups()
            break
        
        if handler:
            self.request._head_links = []
            self.request._head_js = []
            handler.env = jinja2.Environment(loader=TemplateLoader())
            handler.env.globals['request'] = self.request
            getattr(handler, handler_type)(*groups)
        else:
            self.response.set_status(404)
    
    def _compile_routes(self, routes):
        if routes is self.last_routes:
            return
        # self.compiled_routes = [
        #     (re.compile(regexp), handler_class)
        #     for regexp, handler_class in routes
        # ]
        del self.compiled_routes[:]
        for regexp, handler_class in routes:
            if not regexp.startswith('^'):
                regexp = '^' + regexp
            if not regexp.endswith('$'):
                regexp += '$'
            self.compiled_routes.append((re.compile(regexp), handler_class))
        self.last_routes = routes


class HtdocsHandler(webapp.RequestHandler):
    
    def get(self, path=None):
        dir = DirEntry.from_path('/htdocs/'+path)
        if not dir:
            self.error(404)
            return
        ver = dir.latest
        if not ver:
            self.error(404)
            return
        mime_type, encoding = mimetypes.guess_type(dir.path, False)
        if not mime_type:
            mime_type = 'application/octet-stream'
        self.response.headers['Content-Type'] = mime_type
        self.response.out.write(ver.data)


class EditHandler(webapp.RequestHandler):
    
    def get(self, path=None):
        user, user_admin, user_url = _user(self)
        if not user_admin:
            self.error(404)
            return
        if not path:
            self.redirect('/edit/index.py')
        code_file = File.from_path(path)
        code_data = ''
        if code_file:
            code_data = code_file.data
        self.response.out.write(template.render('templates/edit.html', locals()))
    
    def post(self, path):
        if not users.is_current_user_admin():
            self.error(404)
            return
        if not path:
            self.error(404)
            return
        code_file = File.from_path(path)
        if not code_file:
            code_file = File(key_name=path, path=path)
        code_file.data = self.request.get('data').replace('\r\n', '\n')
        code_file.put()
        if path.endswith('.py'):
            mod_name = 'nomic.' + path.replace('/', '.')[:-3]
            mod = sys.modules.get(mod_name)
            if mod:
                try:
                    reload(mod)
                except:
                    pass
        self.redirect(self.request.path)


class AdminHandler(webapp.RequestHandler):
    """A handler for the admin system."""
    
    @login_required
    def get(self):
        user, user_admin, user_url = _user(self)
        if not user_admin:
            self.error(404)
            return
        self.response.out.write(template.render('templates/admin.html', locals()))
    
    def post(self):
        if not users.is_current_user_admin():
            self.error(404)
            return
        cmd = self.request.get('cmd')
        if cmd == 'reset':
            self._reset_files()
        self.redirect(self.request.path)
    
    def _reset_files(self):
        for dir in DirEntry.all().fetch(1000):
            dir.delete()
        reloads = []
        for dirpath, dirs, files in os.walk('nomic'):
            for name in files:
                if name.startswith('.') or name.endswith('.pyc'):
                    continue
                path = os.path.join(dirpath, name)[len('nomic'):]
                dir = DirEntry.from_path(path, create=True)
                data = open('nomic/'+path).read()
                mime_type, encoding = mimetypes.guess_type(path, False)
                if not mime_type:
                    mime_type = 'application/octet-stream'
                if mime_type.startswith('text'):
                    data = data.replace('\r\n', '\n')
                dir.new_version(data)
                if path.endswith('.py'):
                    mod_name = 'nomic.' + path[1:-3].replace('/', '.')
                    mod = sys.modules.get(mod_name)
                    if mod is not None:
                        reloads.append(mod)
        for mod in reloads:
            try:
                reload(mod)
            except:
                pass


def main():
    logging.getLogger().setLevel(logging.DEBUG)
    MetaImporter.install()
    mimetypes.add_type('text/javascript', '.js')
    sys.modules['linecache'] = _linecache
    if 'traceback' in sys.modules:
        sys.modules['traceback'].linecache = _linecache
    application = webapp.WSGIApplication([('/edit/(.*)', EditHandler),
                                          ('/admin', AdminHandler),
                                          ('/htdocs/(.*)', HtdocsHandler),
                                          ('/(.*)', MainHandler)
                                         ], debug=True)
    run_wsgi_app(application)


if __name__ == '__main__':
  main()
