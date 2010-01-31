from google.appengine.ext import db

class File(db.Model):
    name = db.StringProperty()
    data = db.TextProperty()
    version = db.IntegerProperty()
    last_modified = db.DateTimeProperty(auto_now=True)

