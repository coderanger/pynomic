import mimetypes

from google.appengine.ext import webapp
import pygments
import pygments.lexers
import pygments.formatters

from nomic.chrome import add_stylesheet
from nomic.db import File
from nomic.util import _user

class BrowserHandler(webapp.RequestHandler):
    
    def get(self, path=None):
        path, path_segs, file = self._path_info(path)
        if file:
            return self._get_file(path, path_segs, file)
        else:
            return self._get_folder(path, path_segs, file)
    
    def _get_folder(self, path, path_segs, file):
        user, user_admin, user_url = _user(self)
        files = []
        dirs = set()
        for f in File.all().fetch(1000):
            if not f.path.startswith(path):
                continue
            sub_path = f.path[len(path):]
            if '/' in sub_path:
                dir_path = sub_path[:sub_path.find('/')]
                if dir_path not in dirs:
                    dirs.add(dir_path)
                    files.append({
                        'is_dir': True,
                        'name': dir_path,
                        'path': path+dir_path,
                    })
            else:
                files.append({
                    'is_dir': False,
                    'file': f,
                    'name': sub_path,
                })
        up_path = None
        if path:
            up_path = '/browser/' + '/'.join(path.rstrip('/').split('/')[:-1])
            up_path = up_path.rstrip('/')
        self.response.out.write(self.env.get_template('browser.html').render(locals()))
    
    def _path_info(self, path):
        if not path:
            return '', [], None
        path_segs = []
        buf = ''
        for seg in path.rstrip('/').split('/'):
            buf += '/' + seg 
            path_segs.append({'path':buf, 'seg':seg})
        f = File.from_path(path, version=self.request.get('version', None))
        if not f and not path.endswith('/'):
            path += '/'
        return path, path_segs, f
    
    def _get_file(self, path, path_segs, file):
        user, user_admin, user_url = _user(self)
        latest_file = File.from_path(file.path)
        mime_type, encoding = mimetypes.guess_type(file.path, False)
        if mime_type.startswith('text'):
            mode = 'code'
            lexer = pygments.lexers.guess_lexer_for_filename(file.path, file.data)
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