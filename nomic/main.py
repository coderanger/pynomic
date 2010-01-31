import sys
import os
import logging

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import login_required
from google.appengine.ext import db

from nomic.browser import BrowserHandler
from nomic.proposal import CreateProposalHandler
from nomic.util import _user

class MainHandler(webapp.RequestHandler):
    
    def get(self):
        user, user_admin, user_url = _user(self)
        self.response.out.write(template.render('templates/index.html', locals()))


routes = [
    ('/', MainHandler),
    ('/browser(?:/(.*))?', BrowserHandler),
    ('/proposal/create', CreateProposalHandler),
]