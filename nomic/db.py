import logging

from google.appengine.ext import db
from google.appengine.ext.db import polymodel
from google.appengine.api import memcache

File = None
DirEntry = __NomicDirEntry__

class User(db.Model):
    user = db.UserProperty()
    last_login = db.DateTimeProperty()
    score = db.IntegerProperty(default=0)
    
    def nickname(self):
        if not self.user:
            return ''
        return self.user.nickname()
    
    def email(self):
        if not self.user:
            return ''
        return self.user.email()

    def user_id(self):
        if not self.user:
            return ''
        return self.user.user_id()

class Proposal(db.Model):
    user = db.UserProperty(auto_current_user_add=True)
    title = db.StringProperty()
    state = db.StringProperty()
    # Valid states:
    # private
    # published
    # applied
    vote_total = db.IntegerProperty(default=0)
    
    @property
    def changes(self):
        return Change.all().ancestor(self).fetch(1000)
    
    def get_vote(self, user):
        """Returns the value of a users vote on this proposal a value in [-1, 0, 1]."""
        val = 0
        if user:
            memcachekey = 'vote|' + user.user_id() + '|' + str(self.key().id())
            val = memcache.get(memcachekey)
            if val is not None:
                return val
            vote = Vote.get_by_key_name(key_names=user.user_id(), parent=self)
            if vote is not None:
                val = vote.vote
                memcache.set(memcachekey, val)
        return val
    
    def set_vote(self, user, newvote):
        if user is None:
            return

        def txn():
            vote = Vote.get_by_key_name(key_names=user.user_id(), parent=self)
            if vote is None:
                vote = Vote(key_name=user.user_id(), parent=self)
            if vote.vote == newvote:
                return
            self.vote_total = self.vote_total - vote.vote + newvote
            vote.vote = newvote
            db.put([vote, self])
            memcache.set('vote|' + user.user_id() + '|' + str(self.key().id()), vote.vote)

        db.run_in_transaction(txn)
        logging.debug('Proposal[%s] Recording %s voting %s', self.key().id(), user.email(), newvote)


class Change(polymodel.PolyModel):
    """Storage for a single change.
    
    Index
      parent:   The proposal this change is part of.
      
    Properties:
      path: The path to the file this is a diff for.
    """
    path = db.StringProperty()
    created = db.DateTimeProperty(auto_now_add=True)


class PatchChange(Change):
    """Storage for a single diff.
    
    Index
      parent:   The proposal this change is part of.
      
    Properties:
      path: The path to the file this is a diff for.
      diff: The text of the diff.
    """
    diff = db.TextProperty()
    
    def apply(self):
        from nomic.patch import fromstring
        patch = fromstring(self.diff)
        patch.apply()


class BinaryChange(Change):
    """Storage for a single binary change.
    
    Index
      parent:   The proposal this change is part of.
      
    Properties:
      path: The path to the file this is a diff for.
      data: The new data for the file.
    """
    data = db.BlobProperty()
    
    def apply(self):
        file = File.from_path(self.path)
        file.new_version(self.data)


class Vote(db.Model):
    """Storage for a single vote by a single user on a single proposal.
    
    Index
      key_name: The user_id of the user that voted.
      parent:   The proposal this is a vote for.
      
    Properties
      vote: The value of 1 for like, -1 for dislike.
    """
    vote = db.IntegerProperty(default=0)
