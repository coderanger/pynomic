from google.appengine.ext import db

File = __NomicFile__

class User(db.Model):
    user = db.UserProperty()
    score = db.IntegerProperty(default=0)
