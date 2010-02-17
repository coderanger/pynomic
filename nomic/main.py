import sys
import os
import logging

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import login_required
from google.appengine.ext import db

from nomic.browser import BrowserHandler
from nomic.proposal import CreateProposalHandler, ViewProposalHandler, ListProposalHandler
from nomic.util import _user

class MainHandler(webapp.RequestHandler):
    
    def get(self):
        user, user_admin, user_url = _user(self)
        self.response.out.write(env.get_template('index.html').render(locals()))


class AboutHandler(webapp.RequestHandler):
    
    def get(self):
        user, user_admin, user_url = _user(self)
        self.response.out.write(env.get_template('about.html').render(locals()))


routes = [
    ('/', MainHandler),
    ('/browser(?:/(.*))?', BrowserHandler),
    ('/proposal/create', CreateProposalHandler),
    ('/proposal/(\d+)', ViewProposalHandler),
    ('/proposal(?:/)?', ListProposalHandler),
    ('/about', AboutHandler),
]