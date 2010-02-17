import logging

from google.appengine.ext import db
from google.appengine.api import memcache

File = __NomicFile__

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
    path = db.StringProperty()
    diff = db.TextProperty()
    state = db.StringProperty()
    # Valid states:
    # private
    # published
    # applied
    vote_total = db.IntegerProperty(default=0)
    
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


class Vote(db.Model):
    """Storage for a single vote by a single user on a single proposal.
    
    Index
      key_name: The user_id of the user that voted.
      parent:   The proposal this is a vote for.
      
    Properties
      vote: The value of 1 for like, -1 for dislike.
    """
    vote = db.IntegerProperty(default=0)