# Copyright 2010 Noah Kantrowitz
from google.appengine.ext import webapp
import pygments
import pygments.formatters

def add_link(req, rel, href, title=None, mimetype=None, classname=None):
    link = {
        'rel': rel,
        'href': href,
        'title': title,
        'mimetype': mimetype,
        'classname': classname,
    }
    req._head_links.append(link)

def add_stylesheet(req, filename, mimetype='text/css'):
    if not filename.startswith('/') and not filename.startswith('http'):
        filename = '/htdocs/' + filename
    add_link(req, 'stylesheet', filename, mimetype=mimetype)

def add_script(req, filename, mimetype='text/javascript'):
    if not filename.startswith('/') and not filename.startswith('http'):
        filename = '/htdocs/' + filename
    js = {
        'href': filename,
        'mimetype': mimetype,
    }
    req._head_js.append(js)

class PygmentsHandler(webapp.RequestHandler):
    
    def get(self):
        formatter = pygments.formatters.get_formatter_by_name('html', linenos='table', lineanchors='line', anchorlinenos=True, nobackground=True)
        self.response.headers['Content-Type'] = 'text/css'
        self.response.out.write(formatter.get_style_defs('.code'))
        
        