import mimetypes
import logging

from google.appengine.ext import webapp
import pygments
import pygments.lexers
import pygments.formatters

from nomic.chrome import add_stylesheet
from nomic.db import DirEntry
from nomic.util import send_error

class BrowserHandler(webapp.RequestHandler):
    
    def get(self, path):
        # Compute the info for the top-bar navigation
        path_segs = []
        buf = ''
        for seg in path.strip('/').split('/'):
            buf += '/' + seg 
            path_segs.append({'path':buf, 'seg':seg})
        
        if not path:
            path = '/'
        dir = DirEntry.from_path(path)
        
        if not dir:
            send_error(self, 'Directory entry %s not found', path)
            return
        
        if not dir.children.count(1):
            if dir.latest:
                self._get_file(path, path_segs, dir)
            else:
                send_error(self, 'File %s has no versions', dir.path)
        else:
            self._get_folder(path, path_segs, dir)
    
    def _get_folder(self, path, path_segs, dir):
        children = dir.children.fetch(1000)
        children.sort(key=lambda f: f.name)
        up_path = None
        if dir:
            up_path = '/browser/' + '/'.join(path.rstrip('/').split('/')[:-1])
            up_path = up_path.rstrip('/')
        self.response.out.write(self.env.get_template('browser.html').render(locals()))
    
    def _get_file(self, path, path_segs, dir):
        if self.request.get('version'):
            file = dir.version(self.request.get('version'))
        else:
            file = dir.latest
        latest_file = dir.latest
        mime_type, encoding = mimetypes.guess_type(dir.path, False)
        if mime_type.startswith('text'):
            mode = 'code'
            lexer = pygments.lexers.guess_lexer_for_filename(dir.path, file.data)
            formatter = pygments.formatters.get_formatter_by_name('html', linenos='table', lineanchors='line', anchorlinenos=True, nobackground=True)
            highlighted = pygments.highlight(file.data, lexer, formatter)
            add_stylesheet(self.request, '/pygments.css')
        elif mime_type.startswith('image'):
            mode = 'image'
        else:
            mode = 'binary'
        
        if self.request.get('format') == 'raw':
            if mode == 'binary':
                self.response.headers['Content-Disposition'] = 'attachment'
            self.response.headers['Content-Type'] = mime_type
            self.response.out.write(file.data)
        else:
            self.response.out.write(self.env.get_template('browser_file.html').render(locals()))
