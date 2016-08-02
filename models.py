from google.appengine.ext import ndb

class BlogPost(ndb.Model):
	title = ndb.StringProperty(required = True)
	text = ndb.TextProperty(required = True)
	author_name = ndb.StringProperty(required = True)
	author_id = ndb.IntegerProperty(required = True)
	created = ndb.DateTimeProperty(auto_now_add = True)

	likes = ndb.IntegerProperty(default = 0)
	comments = ndb.IntegerProperty(default = 0)

	def id(self):
		return self.key.id()

class User(ndb.Model):
	username = ndb.StringProperty(required = True)
	hashed_password = ndb.StringProperty(required = True)
	email = ndb.StringProperty(required = False)
	created = ndb.DateTimeProperty(auto_now_add = True)

	def id(self):
		return self.key.id()

class Comment(ndb.Model):
	post_id = ndb.IntegerProperty(required = True)
	user_id = ndb.IntegerProperty(required = True)
	user_name = ndb.StringProperty(required = True)
	created = ndb.DateTimeProperty(auto_now_add = True)
	text = ndb.TextProperty(required = True)

class Like(ndb.Model):
	post_id = ndb.IntegerProperty(required = True)
	user_id = ndb.IntegerProperty(required = True)
