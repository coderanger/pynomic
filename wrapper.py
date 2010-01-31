import sys
import logging
import imp
import datetime

from google.appengine.ext.webapp import template
from django.template import TemplateDoesNotExist
import django.template.loader

from db import File

class TemplateWrapper(object):
    
    def _replace_loader(self, new):
        old = django.template.loader.template_source_loaders
        django.template.loader.template_source_loaders = new
        return old
    
    def _loader(self, name, dirs=None):
        name = name[:-14]
        template_file = File.get_by_key_name('templates/'+name)
        if not template_file:
            raise TemplateDoesNotExist, '%s not found'%name
        return template_file.data, 'datastore:'+name
    
    def render(self, template_path, template_dict, debug=True):
        logging.debug('Using TemplateWrapper for render of %s', template_path)
        t = self.load(template_path, debug)
        return t.render(template.Context(template_dict))
    
    def load(self, path, debug=False):
        #if path == 'templates/base.html':
        #    return template.load(path, debug)
        
        old_loaders = self._replace_loader([self._loader])
        try:
            t = template.load(path+'.fromdatastore', debug)
        finally:
            self._replace_loader(old_loaders)
        return t
    
    Template = template.Template
    Context = template.Context


class Loader(object):
    def __init__(self):
        self.template_wrapper = TemplateWrapper()
    
    def load_module(self, name):
        logging.debug('Trying to load %s', name)
        path = name[6:].replace('.', '/') + '.py'
        ispkg = '.' not in name
        do_reload = True
        if not ispkg:
            code_file = File.get_by_key_name(path)
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
                code = 'from __future__ import absolute_import\n' + code_file.data
            mod.__dict__['template'] = self.template_wrapper
            mod.__dict__['__NomicFile__'] = File
            exec code in mod.__dict__
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


    