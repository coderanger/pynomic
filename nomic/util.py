from google.appengine.api import users

from nomic.db import User

def _user(self):
    is_admin = users.is_current_user_admin()
    guser = users.get_current_user()
    if guser:
        user = User.get_by_key_name(guser.user_id())
        if user is None:
            user = User(key_name=guser.user_id(), user=guser)
            user.put()
        url = users.create_logout_url(self.request.uri)
    else:
        user = None
        url = users.create_login_url(self.request.uri)
    return user, is_admin, url

def send_error(handler, msg, *args):
    handler.response.set_status(500)
    msg = msg % args
    handler.response.out.write(template.render('templates/error.html', locals()))