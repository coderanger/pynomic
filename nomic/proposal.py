import difflib
import mimetypes

from google.appengine.ext import webapp, db
from google.appengine.api import users
from google.appengine.ext.webapp.util import login_required
import pygments
import pygments.lexers
import pygments.formatters

from nomic.db import File, Proposal, Change, PatchChange, BinaryChange
from nomic.util import _user, send_error

from nomic.chrome import add_stylesheet, add_script

class CreateProposalHandler(webapp.RequestHandler):
    
    @login_required
    def get(self):
        user, user_admin, user_url = _user(self)
        path = self.request.get('path')
        title = path
        f = File.from_path(path)
        if not f:
            send_error(self, '%s not found', path)
            return
        mime_type, encoding = mimetypes.guess_type(f.path, False)
        if mime_type.startswith('text'):
            data = f.data.replace('    ', '\t')
            add_script(self.request, 'http://ajax.googleapis.com/ajax/libs/jquery/1.4.1/jquery.min.js')
            add_script(self.request, '/htdocs/jquery.tabby.js')
            self.response.out.write(self.env.get_template('proposal_create.html').render(locals()))
        else:
            self.response.out.write(self.env.get_template('proposal_create_binary.html').render(locals()))
    
    def post(self):
        if self.request.get('preview'):
            self._handle_preview()
        elif self.request.get('create'):
            self._handle_create()
        elif self.request.get('save'):
            self._handle_save()
        elif self.request.get('save_binary'):
            self._handle_save_binary()
    
    def _handle_preview(self):
        user, user_admin, user_url = _user(self)
        data = self.request.get('data').replace('\t', '    ').replace('\r\n', '\n')
        path = self.request.get('path')
        title = self.request.get('title')
        old_file = File.from_path(path)
        new_lines = [line+'\n' for line in data.splitlines()]
        old_lines = [line+'\n' for line in old_file.data.splitlines()]
        diff = difflib.unified_diff(old_lines, new_lines, 'a/'+path, 'b/'+path)
        diff_data = ''.join(diff)
        lexer = pygments.lexers.get_lexer_by_name('diff')
        formatter = pygments.formatters.get_formatter_by_name('html', nobackground=True)
        highlighted = pygments.highlight(diff_data, lexer, formatter)
        add_stylesheet(self.request, '/pygments.css')
        self.response.out.write(self.env.get_template('proposal_preview.html').render(locals()))

    def _handle_create(self):
        user, user_admin, user_url = _user(self)
        path = self.request.get('path')
        data = self.request.get('data').replace('    ', '\t')
        title = self.request.get('title')
        add_script(self.request, 'http://ajax.googleapis.com/ajax/libs/jquery/1.4.1/jquery.min.js')
        add_script(self.request, '/htdocs/jquery.tabby.js')
        self.response.out.write(self.env.get_template('proposal_create.html').render(locals()))
    
    def _handle_save(self):
        user, user_admin, user_url = _user(self)
        prop = Proposal(title=self.request.get('title'), state='private')
        def txn():
            prop.put()
            change = PatchChange(parent=prop, path=self.request.get('path'), diff=self.request.get('diff'))
            change.put()
            
        db.run_in_transaction(txn)
        self.redirect('/proposal/%s'%prop.key().id())

    def _handle_save_binary(self):
        user, user_admin, user_url = _user(self)
        prop = Proposal(title=self.request.get('title'), state='private')
        data = self.request.get('newfile')
        path = self.request.get('path')
        def txn():
            prop.put()
            change = BinaryChange(parent=prop, path=path)
            change.data = data
            #if len(change.data) == 0:
            #    raise ValueError, 'Data is empty'
            change.put()
            
        db.run_in_transaction(txn)
        self.redirect('/proposal/%s'%prop.key().id())

class ViewProposalHandler(webapp.RequestHandler):
    
    def get(self, id):
        user, user_admin, user_url = _user(self)
        prop = Proposal.get_by_id(int(id))
        if self.request.get('change'):
            self._handle_change(prop, self.request.get('change'))
            return
        changes_db = Change.all().ancestor(prop).order('created').fetch(100)
        changes = []
        lexer = pygments.lexers.get_lexer_by_name('diff')
        formatter = pygments.formatters.get_formatter_by_name('html', nobackground=True)
        for change_db in changes_db:
            change = {
                'db': change_db,
            }
            if change_db.class_name() == 'PatchChange':
                change['type'] = 'patch'
                change['highlighted'] = pygments.highlight(change_db.diff, lexer, formatter)
            elif change_db.class_name() == 'BinaryChange':
                mime_type, encoding = mimetypes.guess_type(change_db.path, False)
                if mime_type.startswith('image'):
                    change['type'] = 'image'
                else:
                    change['type'] = 'binary'
            changes.append(change)
        
        vote = prop.get_vote(user)
        add_stylesheet(self.request, '/pygments.css')
        self.response.out.write(self.env.get_template('proposal_view.html').render(locals()))
    
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
        changes = Change.all().ancestor(prop).order('created').fetch(100)
        def txn():
            for change in changes:
                change.apply()
        #db.run_in_transaction(txn)
        txn()
        self.redirect(self.request.path)
    
    def _handle_change(self, prop, change_id):
        change = Change.get_by_id(int(change_id), parent=prop)
        if not change:
            send_error(self, 'Change %s not found', change_id, status=404)
            return
        if self.request.get('format') == 'raw':
            if change.class_name() == 'PatchChange':
                self.response.headers['Content-Type'] = 'text/diff'
                self.response.write(change.diff)
            elif change.class_name() == 'BinaryChange':
                mime_type, encoding = mimetypes.guess_type(change.path, False)
                self.response.headers['Content-Type'] = mime_type
                if not mime_type.startswith('image'):
                    self.response.headers['Content-Disposition'] = 'attachment'
                self.response.out.write(change.data)

class ListProposalHandler(webapp.RequestHandler):
    
    def get(self):
        user, user_admin, user_url = _user(self)
        total_props = Proposal.all().count()
        page = int(self.request.get('p', 1))-1
        props = Proposal.all().order('-vote_total').fetch(10, page*10)
        self.response.out.write(self.env.get_template('proposal_list.html').render(locals()))