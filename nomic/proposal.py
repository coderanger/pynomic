from google.appengine.ext import webapp

from nomic.db import File
from nomic.util import _user, send_error

class CreateProposalHandler(webapp.RequestHandler):
    
    def get(self):
        user, user_admin, user_url = _user(self)
        f = File.from_path(self.request.get('path'))
        if not f:
            send_error(self, '%s not found', self.request.get('path'))
            return
        
        self.response.out.write(template.render('templates/create_proposal.html', locals()))