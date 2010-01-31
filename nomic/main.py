import sys
import os
import logging
from copy import copy
from pprint import pformat

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app, login_required
#from google.appengine.ext.webapp import template
from google.appengine.ext import db
from google.appengine.api.urlfetch import fetch
from google.appengine.api import images, users

from nomic.db import User

def _user(self):
    is_admin = users.is_current_user_admin()
    guser = users.get_current_user()
    if guser:
        user = User.get_by_key_name(guser.user_id())
        if user is None:
            user = User(key_name=guser.user_id(), user=guser)
            user.put()
        url = users.create_logout_url(self.request.uri)
    else:
        user = None
        url = users.create_login_url(self.request.uri)
    return user, is_admin, url

class MainHandler(webapp.RequestHandler):
    
    def get(self):
        user, user_admin, user_url = _user(self)
        self.response.out.write(template.render('templates/index.html', locals()))


routes = [
    ('/', MainHandler),
]