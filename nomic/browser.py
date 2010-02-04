from google.appengine.ext import webapp
import pygments
import pygments.lexers
import pygments.formatters

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
            if not f.name.startswith(path):
                continue
            sub_path = f.name[len(path):]
            if '/' in sub_path:
                dir_path = sub_path[:sub_path.find('/')]
                if dir_path not in dirs:
                    dirs.add(dir_path)
                    files.append({
                        'is_dir': True,
                        'name': dir_path,
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
        self.response.out.write(template.render('templates/browser.html', locals()))
    
    def _path_info(self, path):
        if not path:
            return '', [], None
        path_segs = []
        buf = ''
        for seg in path.rstrip('/').split('/'):
            buf += '/' + seg 
            path_segs.append({'path':buf, 'seg':seg})
        f = File.from_path(path)
        if not f and not path.endswith('/'):
            path += '/'
        return path, path_segs, f
    
    def _get_file(self, path, path_segs, file):
        user, user_admin, user_url = _user(self)
        lexer = pygments.lexers.guess_lexer_for_filename(file.name, file.data)
        formatter = pygments.formatters.get_formatter_by_name('html', linenos='table', lineanchors='line', anchorlinenos=True, nobackground=True)
        highlighted = pygments.highlight(file.data, lexer, formatter)
        pygments_css = formatter.get_style_defs('  #browser .code')
        self.response.out.write(template.render('templates/browser_file.html', locals()))