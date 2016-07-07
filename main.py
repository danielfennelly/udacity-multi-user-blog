import os
import webapp2
import jinja2
import string
import re
import random
import hashlib
import datetime

from google.appengine.ext import ndb

import validators

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
	autoescape=True)

FORBIDDEN = 403
NOT_FOUND = 404

# ----- Crypto -----

with open('secret', 'r') as f:
	secret = f.read()

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

# ----- Models -----

class BlogPost(ndb.Model):
	title = ndb.StringProperty(required = True)
	text = ndb.TextProperty(required = True)
	user_id = ndb.StringProperty(required = True)
	created = ndb.DateTimeProperty(auto_now_add = True)

	def id(self):
		return self.key.id()


class User(ndb.Model):
	# Assume username is id in model
	hashed_password = ndb.StringProperty(required = True)
	email = ndb.StringProperty(required = False)
	created = ndb.DateTimeProperty(auto_now_add = True)

	def id(self):
		return self.key.id()

# ----- Handlers -----

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
		header = '%s=%s|%s; Path=/' % ('user_id', user.id(), unsalt(user.hashed_password))
		self.response.headers.add_header('Set-Cookie', str(header))

	def clear_user(self):
		self.response.headers.add_header('Set-Cookie', 'user_id=; Path=/')

	def register_user(self, username, password, email):
		hashed_password = make_pw_hash(username, password)
		user = User(
			id = username,
			hashed_password = hashed_password,
			email = email)
		user.put()
		return user

class MainPage(Handler):

    def get(self):
    	posts = BlogPost.query().order(-BlogPost.created)
    	user = self.get_user()
    	self.render('index.html', posts = posts, user = user)

class NewPostPage(Handler):

	def render_new_post(self, title= '', text= '', user = None, params = {}):
		self.render('newpost.html', title = title, text = text, user = user, params = params)

	def get(self):
		user = self.get_user()
		if not user:
			self.redirect('/signup')
		self.render_new_post(user = self.get_user())

	def post(self):
		user = self.get_user()
		if not user:
			self.redirect('/signup')

		params = {}

		title = self.request.get('title')
		params['missing_title'] = not title

		text = self.request.get('text')
		params['missing_text'] = not text

		if title and text:
			post = BlogPost(title = title, text = text, user_id = user.id())
			post.put()
			post_id = post.key.id()
			self.redirect('/posts/%d' % post_id)
		else:
			self.render_new_post(
				title  = title,
				text   = text,
				user   = user,
				params = params)

class EditPage(Handler):

	def render_edit_post(self, blog_post, user, params = {}):
		self.render('edit.html', blog_post = blog_post, user = user, params = params)

	def get(self, post_id):
		user = self.get_user()
		blog_post = BlogPost.get_by_id(int(post_id))

		if not user:
			self.redirect('/signup')
		if not blog_post:
			response.set_status(NOT_FOUND)
		if blog_post.user_id != user.id():
			response.set_status(FORBIDDEN)

		self.render_edit_post(
			blog_post = blog_post,
			user   = user,
			params = {})

	def post(self, post_id):
		user = self.get_user()
		blog_post = BlogPost.get_by_id(int(post_id))

		if not user:
			self.redirect('/signup')
		if not blog_post:
			response.set_status(NOT_FOUND)
		if blog_post.user_id != user.id():
			response.set_status(FORBIDDEN)

		params = {}

		title = self.request.get('title')
		params['missing_title'] = not title

		text = self.request.get('text')
		params['missing_text'] = not text

		if title and text:
			blog_post.title = title
			blog_post.text = text
			blog_post.put()
			self.redirect('/posts/%d' % int(post_id))
		else:
			self.render_edit_post(
				blog_post = blog_post,
				user   = user,
				params = params)

class PermalinkPage(Handler):

	def get(self, post_id):
		blog_post = BlogPost.get_by_id(int(post_id))
		if blog_post:
			user = self.get_user()
			self.render('permalink.html', blog_post = blog_post, user = user)
		else:
			self.redirect('/')

class DeletePage(Handler):

	def post(self, post_id):
		blog_post = BlogPost.get_by_id(int(post_id))
		user = self.get_user()

		if (blog_post.user_id == user.id()):
			blog_post.key.delete()
			self.redirect('/')
		else:
			response.set_status(FORBIDDEN)

class SignupPage(Handler):

	def validate_params(self, request):
		username = request.get('username')
		password = request.get('password')
		verify   = request.get('verify')
		email    = request.get('email')

		params = {}
		valid_form_data = True

		valid_username = validators.validate_username(username)
		if valid_username:
			params['username'] = valid_username
		else:
			params['invalid_username'] = True
			valid_form_data = False

		valid_password = validators.validate_password(password, verify)
		if valid_password:
			params['password'] = valid_password
		else:
			params['invalid_password'] = True
			valid_form_data = False

		valid_email = validators.validate_email(email)
		if valid_email or (email == ''):
			params['email'] = valid_email
		else:
			params['invalid_email'] = True
			valid_form_data = False

		if valid_username:
			existing_user = User.get_by_id(params['username'])
			if existing_user:
				params['user_already_exists'] = True
				valid_form_data = False

		return (params, valid_form_data)

	def get(self):
		if self.get_user():
			self.redirect('/welcome')
		else:
			self.render('signup.html')

	def post(self):
		params, valid_post = self.validate_params(self.request)

		if valid_post:
			user = self.register_user(
				params['username'],
				params['password'],
				params['email'])
			self.set_user(user)
			self.redirect('/welcome')
		else:
			self.render('signup.html', params = params)

class LoginPage(Handler):

	def get(self):
		user = self.get_user()
		if user:
			self.redirect('/welcome')
		else:
			self.render('login.html')

	def post(self):
		username = self.request.get('username')
		password = self.request.get('password')

		user = User.get_by_id(username)
		params = {}

		if user and valid_pw(username, password, user.hashed_password):
			self.set_user(user)	
			self.redirect('/welcome')
		else:
			params['login_failure'] = True

		self.render('login.html', params = params)

class WelcomePage(Handler):
	def get(self):
		user = self.get_user()
		if user:
			self.render('welcome.html', user = user)
		else:
			self.redirect('/login')

class LogoutPage(Handler):
	def logout(self):
		self.clear_user()
		self.redirect('/signup')

	def get(self):
		self.logout()

	def post(self):
		self.logout()

# ----- App Config -----

app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/newpost', NewPostPage),
    ('/signup', SignupPage),
    ('/welcome', WelcomePage),
    ('/login', LoginPage),
    ('/logout', LogoutPage),
    (r'/posts/(\d+)', PermalinkPage),
    (r'/posts/(\d+)/delete', DeletePage),
    (r'/posts/(\d+)/edit', EditPage)
], debug=True)

