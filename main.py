import os
import webapp2
import jinja2
import string
import re
import random
import hashlib

from google.appengine.ext import ndb

import validators

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
	autoescape=True)

# NB: This is not ideal cryptographic practice.
def make_salt():
	return string.join(random.sample(string.ascii_letters, 20),'')

def make_pw_hash(name, pw, salt=None):
    if not salt:
        salt = make_salt()
    h = hashlib.sha256(name + pw + salt).hexdigest()
    return '%s,%s' % (h, salt)

def unsalt(hash_and_salt):
	hashed, salt = hash_and_salt.split(',')
	return hashed

def valid_pw(name, pw, h):
	salt = h.split(',')[1]
	return h == make_pw_hash(name, pw, salt)

class BlogPost(ndb.Model):
	title = ndb.StringProperty(required = True)
	text = ndb.TextProperty(required = True)
	created = ndb.DateTimeProperty(auto_now_add = True)

class User(ndb.Model):
	# Assume username is id in model
	hashed_password = ndb.StringProperty(required = True)
	email = ndb.StringProperty(required = False)
	created = ndb.DateTimeProperty(auto_now_add = True)

class Handler(webapp2.RequestHandler):
	def write(self, *a, **kw):
		self.response.out.write(*a, **kw)

	def render_str(self, template, **params):
		t = jinja_env.get_template(template)
		return t.render(params)

	def render(self, template, **kw):
		self.write(self.render_str(template, **kw))

	def get_user(self):
		user_id = self.request.cookies.get("user_id")
		if user_id:
			print('cookie %s' % user_id)
			username, user_hash = user_id.split("|") # FRAGILE, DON'T TRUST COOKIE VALUES
			if username:
				user = User.get_by_id(username)
				real_hashed_pw = unsalt(user.hashed_password)
				if user_hash == real_hashed_pw:
					return user
		return None

	def set_user(self, user):
		header = '%s=%s|%s; Path=/' % ('user_id', user.key.id(), unsalt(user.hashed_password))
		self.response.headers.add_header('Set-Cookie', str(header))

	def clear_user(self):
		self.response.headers.add_header('Set-Cookie', 'user_id=; Path=/')

class MainPage(Handler):

    def get(self):
    	posts = BlogPost.query().order(-BlogPost.created)
    	self.render("index.html", posts = posts, user = self.get_user())

class NewPostPage(Handler):

	def render_new_post(self, title= "", text= "", user = None, error = None):
		self.render("newpost.html", subject = title, content = text, user = user, error = error)

	def get(self):
		self.render_new_post(user = self.get_user())

	def post(self):
		title = self.request.get("subject")
		text = self.request.get("content")

		if title and text:
			post = BlogPost(title = title, text = text)
			post.put()
			post_id = post.key().id()
			self.redirect("/posts/%d" % post_id)
		else:
			self.render_new_post(
				title = title,
				text=text,
				user = self.get_user(),
				error="We need both a title and text")

class PermalinkPage(Handler):

	def get(self, post_id):
		post = BlogPost.get_by_id(int(post_id))
		if post:
			self.render("permalink.html", title = post.title, text = post.text)
		else:
			self.redirect("/")

class SignupPage(Handler):

	def register_user(self, username, password, email):
		hashed_password = make_pw_hash(username, password)
		user = User(
			id = username,
			hashed_password = hashed_password,
			email = email)
		user.put()
		return user

	def get(self):
		if self.get_user():
			self.redirect("/welcome")
		else:
			self.render("signup.html")

	def post(self):
		username = self.request.get("username")
		password = self.request.get("password")
		verify = self.request.get("verify")
		email = self.request.get("email")

		valid_username = validators.validate_username(username)
		valid_password = validators.validate_password(password, verify)
		valid_email = validators.validate_email(email)

		has_valid_email = valid_email or (email == '')

		existing_user = User.get_by_id(valid_username)

		if existing_user:
			error = 'A user already exists with that username.'
			print(error)
			self.render('signup.html', error = error)
		elif valid_username and valid_password and has_valid_email:
			user = self.register_user(valid_username, valid_password, valid_email)
			self.set_user(user)
			self.redirect("/welcome")
		else:
			# TODO: add error messages
			print('Invalid form data')
			self.render('signup.html')

class LoginPage(Handler):

	def get(self):
		user = self.get_user()
		if user:
			self.redirect('/welcome')
		else:
			self.render("login.html")

	#TODO
	def post(self):
		username = self.request.get("username")
		password = self.request.get("password")

		user = User.get_by_id(username)

		if user:
			if valid_pw(username, password, user.hashed_password):
				self.set_user(user)	
				self.redirect('/welcome')
			else:
				error = 'Password was incorrect.'
				print(error)
				self.render('login.html', error = error)
		else:
			error = 'That user does not exist.'
			print(error)
			self.render('login.html', error)

class WelcomePage(Handler):
	def get(self):
		user = self.get_user()
		if user:
			self.render('welcome.html', user = user)
		else:
			self.redirect('/login')

class LogoutPage(Handler):
	def get(self):
		self.render('logout.html', user = self.get_user())

	def post(self):
		self.clear_user()
		self.redirect('/signup')

app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/newpost', NewPostPage),
    ('/signup', SignupPage),
    ('/login', LoginPage),
    ('/welcome', WelcomePage),
    ('/logout', LogoutPage),
    (r'/posts/(\d+)', PermalinkPage)
], debug=True)

