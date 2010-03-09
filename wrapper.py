import sys
import logging
import imp
import datetime

from google.appengine.ext.webapp import template
from django.template import TemplateDoesNotExist
import django.template.loader
import jinja2

from db import DirEntry

class TemplateLoader(jinja2.BaseLoader):
    def get_source(self, environment, template):
        path = '/templates/'+template
        dir = DirEntry.from_path(path)
        if not dir:
            return None
        ver = dir.latest
        if not ver:
            return None
        return ver.data, 'datastore:'+path, lambda: False


class Loader(object):
    
    def load_module(self, name):
        logging.debug('Trying to load %s', name)
        path = self._modname_to_path(name)
        ispkg = self.is_package(name)
        if ispkg:
            code_file = ispkg
        else:
            dir = DirEntry.from_path(path)
            if not dir or not dir.latest:
                raise ImportError, 'datastore:%s not found (%s)'%(path, name)
            code_file = dir.latest
        
        mod = sys.modules.get(name)
        do_reload = True
        if mod is not None and mod.__mtime__ >= code_file.last_modified:
            do_reload = False
        
        if do_reload:
            logging.debug('Loading module %s', name)
            mod = sys.modules.setdefault(name, imp.new_module(name))
            mod.__file__ = 'datastore:%s' % code_file.parent().path
            mod.__loader__ = self
            mod.__mtime__ = datetime.datetime.now()
            if ispkg:
                mod.__path__ = [code_file.parent().path[:-12]]
            code = 'from __future__ import absolute_import\n' + code_file.data + '\n\n'
            mod.__dict__['__NomicDirEntry__'] = DirEntry
            compiled = compile(code, mod.__file__, 'exec')
            exec compiled in mod.__dict__
            if '.' in name:
                parent_name, child_name = name.rsplit('.', 1)
                setattr(sys.modules[parent_name], child_name, mod)
        return sys.modules[name]
    
    def _path_to_modname(self, path):
        pass
    
    def _modname_to_path(self, name):
        """Convert 'nomic.main' to '/main.py'."""
        return name[5:].replace('.', '/') + '.py'
    
    def _pkgname_to_path(self, name):
        """Convert 'nomic.main' to '/main/__init__.py'."""
        return name[5:].replace('.', '/') + '/__init__.py'
    
    def get_source(self, name):
        pkg = self.is_package(name)
        if pkg:
            return '\n'+pkg.data
        path = self._modname_to_path(name)
        dir = DirEntry.from_path(name)
        if not dir:
            return None
        ver = dir.latest
        if not ver:
            return None
        return '\n'+ver.data
    
    def is_package(self, name):
        path = self._pkgname_to_path(name)
        dir = DirEntry.from_path(path)
        if not dir:
            return False
        return dir.latest
        

class MetaImporter(object):
    def __init__(self):
        self.loader = Loader()
    
    def find_module(self, fullname, path=None):
        if fullname == 'nomic' or fullname.startswith('nomic.'):
            return self.loader
        return None
    
    @classmethod
    def install(cls):
        sys.meta_path.insert(0, cls())


    