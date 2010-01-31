from google.appengine.ext import db

class User(db.Model):
    user = db.UserProperty()
    score = db.IntegerProperty(default=0)
    
    @property
    def nickname(self):
        if self.user:
            return self.user.nickname()
        return ''