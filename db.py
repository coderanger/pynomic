from google.appengine.ext import db

class File(db.Model):
    path = db.StringProperty()
    data = db.TextProperty()
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