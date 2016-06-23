import os
import webapp2
import jinja2
import string
import re

from google.appengine.ext import db

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
	autoescape=True)

USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
PASSWORD_RE = re.compile(r"^.{3,20}$")
EMAIL_RE = re.compile(r"^[\S]+@[\S]+.[\S]+$")

def validate_username(username):
    if USER_RE.match(username):
    	return username
    else:
    	return None

def validate_password(password, verify):
	if PASSWORD_RE.match(password) and password == verify:
		return password
	else:
		return None

def validate_email(email):
	if EMAIL_RE.match(email):
		return email
	else:
		return None

def validate_email(email):
	return EMAIL_RE.match(email)

class Handler(webapp2.RequestHandler):
	def write(self, *a, **kw):
		self.response.out.write(*a, **kw)

	def render_str(self, template, **params):
		t = jinja_env.get_template(template)
		return t.render(params)

	def render(self, template, **kw):
		self.write(self.render_str(template, **kw))

class BlogPost(db.Model):
	title = db.StringProperty(required = True)
	text = db.TextProperty(required = True)
	created = db.DateTimeProperty(auto_now_add = True)

class MainPage(Handler):
    def get(self):
    	posts = db.GqlQuery("SELECT * FROM BlogPost ORDER BY created DESC")
    	self.render("index.html", posts = posts)

class NewPostPage(Handler):

	def render_new_post(self, title="", text="", error=None):
		self.render("newpost.html", subject = title, content = text, error = error)

	def get(self):
		self.render_new_post()

	def post(self):
		title = self.request.get("subject")
		text = self.request.get("content")

		if title and text:
			post = BlogPost(title = title, text = text)
			post.put()
			post_id = post.key().id()
			self.redirect("/%d" % post_id)
		else:
			self.render_new_post(title = title, text=text, error="We need both a title and text")
		# insert into DB
		# get object key and redirect to permalink page

class PermalinkPage(Handler):

	# TODO: Look up post by id in DB and render
	def get(self, post_id):
		post = BlogPost.get_by_id(int(post_id))
		if post:
			self.render("permalink.html", title = post.title, text = post.text)
		else:
			self.redirect("/")

class SignupPage(Handler):

	def get(self):
		self.render("signup.html")

	def post(self):
		username = self.request.get("username")
		password = self.request.get("password")
		verify = self.request.get("verify")
		email = self.request.get("email")

		valid_username = validate_username(username)
		valid_password = validate_password(password, verify)
		valid_email = validate_email(email)

		has_valid_email = valid_email or (email == '')

		# This is distinctly not how this problem ought to be solved
		# sessions should be used instead of passing the username in the query string
		if valid_username and valid_password and has_valid_email:
			self.redirect("/welcome?username="+username)
		else:
			self.render("signup.html")

class LoginPage(Handler):

	def get(self):
		self.render("login.html")

	#TODO
	def post(self):
		# if successful:
		# 	self.redirect("/welcome")
		# else:
		# 	self.render("login.html")
		pass

class WelcomePage(Handler):
	def get(self):
		username = self.request.get("username")
		self.render("welcome.html", username = username)

app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/newpost', NewPostPage),
    ('/signup', SignupPage),
    ('/login', LoginPage),
    ('/welcome', WelcomePage),
    (r'/(\d+)', PermalinkPage)
], debug=True)

