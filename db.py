from google.appengine.ext import db

class File(db.Model):
    name = db.StringProperty()
    data = db.TextProperty()
    version = db.IntegerProperty()
    last_modified = db.DateTimeProperty(auto_now=True)

    @property
    def size(self):
        return len(self.data)
    
    @classmethod
    def from_path(cls, path):
        return cls.get_by_key_name(path)
        