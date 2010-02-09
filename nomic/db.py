from google.appengine.ext import db

File = __NomicFile__

class User(db.Model):
    user = db.UserProperty()
    score = db.IntegerProperty(default=0)

class Proposal(db.Model):
    user = db.UserProperty(auto_current_user_add=True)
    path = db.StringProperty()
    diff = db.TextProperty()
    state = db.StringProperty()
    # Valid states:
    # private
    # published
    # applied

