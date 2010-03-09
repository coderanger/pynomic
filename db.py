import logging

from google.appengine.ext import db

class File(db.Model):
    path = db.StringProperty()
    data = db.BlobProperty()
    version = db.IntegerProperty(default=0)
    last_modified = db.DateTimeProperty(auto_now=True)

    @property
    def size(self):
        return len(self.data)
    
    @classmethod
    def from_path(cls, path, version=None):
        query = cls.all().filter('path', path).order('-version')
        if version is not None:
            query = query.filter('version', int(version))
        ret = query.fetch(1)
        if ret:
            return ret[0]
        return None
    
    def new_version(self, data):
        """Create a new version of this file with the given data."""
        new_file = File(path=self.path, data=data, version=self.version+1)
        new_file.put()
        return new_file


class DirEntry(db.Model):
    path = db.StringProperty()
    name = db.StringProperty()
    parent_ = db.SelfReferenceProperty(collection_name='children')
    # children = db.ListProperty(db.Key) # This is created automatically by the .parent self ref.
    # versions = db.ListProperty(db.Key) # This is created automatically by the FileVersion.parent ref.
    last_modified = db.DateTimeProperty(auto_now=True)
    
    @classmethod
    def from_path(cls, path, create=False):
        dir = cls.get_by_key_name(path)
        if dir is None and create:
            if path == '/':
                base, name = None, ''
            else:
                base, name = path.rstrip('/').rsplit('/', 1)
                #base = db.Key.from_path('DirEntry', base)
                base = cls.from_path(base or '/', create=True)
            dir = cls(key_name=path, path=path, name=name, parent_=base)
            dir.put()
        return dir
    
    @classmethod
    def root(cls):
        return cls.from_path('/')
    
    def version(self, version):
        return FileVersion.get_by_key_name(str(version), parent=self)
    
    @property
    def latest(self):
        if hasattr(self, '_latest'):
            return self._latest
        query = FileVersion.all().ancestor(self).order('-version')
        ret = query.fetch(1)
        if ret:
            self._latest = ret[0]
            return ret[0]
        return None
    
    def new_version(self, data):
        """Create a new version of this file with the given data."""
        latest = self.latest
        if latest:
            next_version = latest.version + 1
        else:
            next_version = 0
        new_ver = FileVersion(parent_=self, version=next_version, data=data, parent=self, key_name=str(next_version))
        new_ver.put()
        return new_ver

    def delete(self):
        query = FileVersion.all().ancestor(self)
        for ver in query.fetch(1000):
            ver.delete()
        super(DirEntry, self).delete()


class FileVersion(db.Model):
    parent_ = db.ReferenceProperty(DirEntry, collection_name='versions') # This mostly exists to create the back-ref collection
    version = db.IntegerProperty(default=0)
    data = db.BlobProperty()
    last_modified = db.DateTimeProperty(auto_now=True)
    
    @property
    def size(self):
        return len(self.data)

