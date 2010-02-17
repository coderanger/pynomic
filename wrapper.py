import sys
import logging
import imp
import datetime

from google.appengine.ext.webapp import template
from django.template import TemplateDoesNotExist
import django.template.loader
import jinja2

from db import File

class TemplateLoader(jinja2.BaseLoader):
    def get_source(self, environment, template):
        path = 'templates/'+template
        file = File.from_path(path)
        if not file:
            return None
        return file.data, 'datastore:/'+path, lambda: False


class Loader(object):
    def __init__(self):
        self.jinja_env = jinja2.Environment(loader=TemplateLoader())
    
    def load_module(self, name):
        logging.debug('Trying to load %s', name)
        path = name[6:].replace('.', '/') + '.py'
        ispkg = '.' not in name
        do_reload = True
        if not ispkg:
            code_file = File.from_path(path)
            if not code_file:
                raise ImportError, 'datastore:%s not found (%s)'%(path, name)
            mod = sys.modules.get(name)
            if mod is not None and mod.__mtime__ >= code_file.last_modified:
                do_reload = False
        
        if do_reload:
            logging.debug('Loading module %s', name)
            mod = sys.modules.setdefault(name, imp.new_module(name))
            mod.__file__ = 'datastore:%s' % path
            mod.__loader__ = self
            mod.__mtime__ = datetime.datetime.now()
            if ispkg:
                mod.__path__ = []
                code = ''
            else:
                code = 'from __future__ import absolute_import\n' + code_file.data + '\n\n'
            mod.__dict__['env'] = self.jinja_env
            mod.__dict__['__NomicFile__'] = File
            compiled = compile(code, mod.__file__, 'exec')
            exec compiled in mod.__dict__
            if '.' in name:
                parent_name, child_name = name.rsplit('.', 1)
                setattr(sys.modules[parent_name], child_name, mod)
        return sys.modules[name]

class MetaImporter(object):
    def __init__(self):
        self.loader = Loader()
    
    def find_module(self, fullname, path=None):
        if fullname == 'nomic' or fullname.startswith('nomic.'):
            return self.loader
        return None
    
    @classmethod
    def install(cls):
        sys.meta_path.append(cls())


    