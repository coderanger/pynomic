from google.appengine.ext import webapp

from nomic.db import File
from nomic.util import _user

class BrowserHandler(webapp.RequestHandler):
    
    def get(self, path=None):
        user, user_admin, user_url = _user(self)
        if not path:
            path = ''
            path_segs = []
        else:
            path_segs = []
            buf = ''
            for seg in path.rstrip('/').split('/'):
                buf += seg
                path_segs.append({'path':buf, 'seg':seg})
        if path and not path.endswith('/'):
            path += '/'
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
            up_path = '/'.join(path.rstrip('/').split('/')[:-1])
        self.response.out.write(template.render('templates/browser.html', locals()))