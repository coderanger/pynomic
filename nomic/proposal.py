import difflib

from google.appengine.ext import webapp
from google.appengine.api import users
from google.appengine.ext.webapp.util import login_required
import pygments
import pygments.lexers
import pygments.formatters


from nomic.db import File, Proposal
from nomic.util import _user, send_error
from nomic.patch import fromstring

class CreateProposalHandler(webapp.RequestHandler):
    
    @login_required
    def get(self):
        user, user_admin, user_url = _user(self)
        path = self.request.get('path')
        f = File.from_path(path)
        if not f:
            send_error(self, '%s not found', path)
            return
        data = f.data.replace('    ', '\t')
        
        js_files = [
            'http://ajax.googleapis.com/ajax/libs/jquery/1.4.1/jquery.min.js',
            '/htdocs/jquery.tabby.js',
        ]
        self.response.out.write(template.render('templates/proposal_create.html', locals()))
    
    def post(self):
        if self.request.get('preview'):
            self._handle_preview()
        elif self.request.get('create'):
            self._handle_create()
        elif self.request.get('save'):
            self._handle_save()
    
    def _handle_preview(self):
        user, user_admin, user_url = _user(self)
        data = self.request.get('data').replace('\t', '    ').replace('\r\n', '\n')
        path = self.request.get('path')
        old_file = File.from_path(path)
        new_lines = [line+'\n' for line in data.splitlines()]
        old_lines = [line+'\n' for line in old_file.data.splitlines()]
        diff = difflib.unified_diff(old_lines, new_lines, 'a/'+path, 'b/'+path)
        diff_data = ''.join(diff)
        lexer = pygments.lexers.get_lexer_by_name('diff')
        formatter = pygments.formatters.get_formatter_by_name('html', nobackground=True)
        highlighted = pygments.highlight(diff_data, lexer, formatter)
        pygments_css = formatter.get_style_defs('  #proposal .code')
        self.response.out.write(template.render('templates/proposal_preview.html', locals()))

    def _handle_create(self):
        user, user_admin, user_url = _user(self)
        path = self.request.get('path')
        data = self.request.get('data').replace('    ', '\t')
        js_files = [
            'http://ajax.googleapis.com/ajax/libs/jquery/1.4.1/jquery.min.js',
            '/htdocs/jquery.tabby.js',
        ]
        self.response.out.write(template.render('templates/proposal_create.html', locals()))
    
    def _handle_save(self):
        user, user_admin, user_url = _user(self)
        prop = Proposal()
        prop.path = self.request.get('path')
        prop.diff = self.request.get('diff')
        prop.state = 'private'
        prop.put()
        self.redirect('/proposal/%s'%prop.key().id())

class ViewProposalHandler(webapp.RequestHandler):
    
    def get(self, id):
        user, user_admin, user_url = _user(self)
        prop = Proposal.get_by_id(int(id))
        lexer = pygments.lexers.get_lexer_by_name('diff')
        formatter = pygments.formatters.get_formatter_by_name('html', nobackground=True)
        highlighted = pygments.highlight(prop.diff, lexer, formatter)
        pygments_css = formatter.get_style_defs('  #proposal .code')
        vote = prop.get_vote(user)
        up_vote = vote == 1
        down_vote = vote == -1
        self.response.out.write(template.render('templates/proposal_view.html', locals()))
    
    def post(self, id):
        if self.request.get('apply'):
            self._handle_apply(id)
        elif self.request.get('vote'):
            user, user_admin, user_url = _user(self)
            prop = Proposal.get_by_id(int(id))
            vote = int(self.request.get('vote'))
            prop.set_vote(user, vote)
            self.redirect(self.request.path)
        else:
            self.redirect(self.request.path)
    
    def _handle_apply(self, id):
        if not users.is_current_user_admin():
            self.redirect(self.request.path)
            return
        prop = Proposal.get_by_id(int(id))
        p = fromstring(prop.diff)
        p.apply()
        self.redirect('/browser/'+prop.path)

class ListProposalHandler(webapp.RequestHandler):
    
    def get(self):
        user, user_admin, user_url = _user(self)
        total_props = Proposal.all().count()
        page = int(self.request.get('p', 1))-1
        props = Proposal.all().fetch(10, page*10)
        self.response.out.write(template.render('templates/proposal_list.html', locals()))