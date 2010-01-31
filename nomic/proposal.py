from google.appengine.ext import webapp

from nomic.util import _user

class CreateProposalHandler(webapp.RequestHandler):
    
    def get(self):
        user, user_admin, user_url = _user(self)
        self.response.out.write(template.render('templates/create_proposal.html', locals()))