import datetime
import hashlib
import jinja2
import os
import random
import re
import string
import webapp2

from google.appengine.ext import ndb

import crypto
from models import BlogPost, User, Comment, Like
import validators

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir),
                               autoescape=True)

BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404

# ----- Handlers -----


class Handler(webapp2.RequestHandler):
    """Base Handler class containing rendering and authentication methods"""

    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    def get_user(self):
        user_cookie = self.request.cookies.get("user")
        if user_cookie:
            user_id, user_hash = crypto.extract_user_id_hash(user_cookie)
            if user_id:
                user_id = int(user_id)
                user = User.get_by_id(user_id)
                real_hashed_pw = crypto.unsalt(user.hashed_password)
                if user_hash == real_hashed_pw:
                    return user
        return None

    def set_user(self, user):
        header = '%s=%s|%s; Path=/' % (
            'user', user.id(), crypto.unsalt(user.hashed_password))

        self.response.headers.add_header('Set-Cookie', str(header))

    def clear_user(self):
        self.response.headers.add_header('Set-Cookie', 'user=; Path=/')

    def register_user(self, username, password, email):
        hashed_password = crypto.make_pw_hash(username, password)
        user = User(
            username=username,
            hashed_password=hashed_password,
            email=email)
        user.put()
        return user


class MainPage(Handler):
    """Handler for the main index page displaying all posts"""

    def get(self):
        posts = BlogPost.query().order(-BlogPost.created)
        user = self.get_user()
        if user:
            like_models = Like.query(Like.user_id == user.id())
            likes = [like.post_id for like in like_models]
        else:
            likes = []

        print('likes %s' % likes)

        self.render('index.html', posts=posts, user=user, likes=likes)


class NewPostPage(Handler):
    """Handler for creating new blog posts"""

    def render_new_post(self, title='', text='', user=None, params={}):
        self.render('newpost.html',
                    title=title,
                    text=text,
                    user=user,
                    params=params)

    def get(self):
        user = self.get_user()
        if not user:
            return self.redirect('/signup')
        self.render_new_post(user=self.get_user())

    def post(self):
        user = self.get_user()
        if not user:
            return self.redirect('/signup')

        params = {}

        title = self.request.get('title')
        params['missing_title'] = not title

        text = self.request.get('text')
        params['missing_text'] = not text

        if title and text:
            post = BlogPost(
                title=title,
                text=text,
                author_name=user.username,
                author_id=user.id())
            post.put()
            post_id = post.key.id()
            return self.redirect('/posts/%d' % post_id)
        else:
            self.render_new_post(
                title=title,
                text=text,
                user=user,
                params=params)


class PageHandler(Handler):
    """Base Handler for single post pages such as Permalink and Edit"""

    def get_comments(self, post_id):
        comments = Comment.query(
            Comment.post_id == post_id).order(-Comment.created)
        return comments

    def get_liked(self, post_id, user=None):
        if user:
            like_models = Like.query(
                Like.user_id == user.id(),
                Like.post_id == post_id).fetch()
            if len(like_models) > 0:
                return True
        return False


class PermalinkPage(PageHandler):
    """Handler for rendering a single blog post with comments"""

    def get(self, post_id_str):
        post_id = int(post_id_str)

        blog_post = BlogPost.get_by_id(post_id)

        if blog_post:
            user = self.get_user()
            comments = self.get_comments(blog_post.id())
            liked = self.get_liked(blog_post.id(), user)
            self.render('permalink.html',
                        blog_post=blog_post,
                        user=user,
                        comments=comments,
                        liked=liked)
        else:
            return self.redirect('/')


class EditPage(PageHandler):
    """Handler for rendering an editable blog post with comments"""

    def render_edit_post(self, blog_post, user, comments, params={}):
        self.render('edit.html',
                    blog_post=blog_post,
                    user=user,
                    comments=comments,
                    params=params)

    def get(self, post_id):
        user = self.get_user()
        blog_post = BlogPost.get_by_id(int(post_id))

        if not user:
            return self.redirect('/signup')
        if not blog_post:
            response.set_status(NOT_FOUND)
        if blog_post.author_id != user.id():
            response.set_status(FORBIDDEN)

        comments = self.get_comments(blog_post.id())

        self.render_edit_post(
            blog_post=blog_post,
            user=user,
            comments=comments,
            params={})

    def post(self, post_id):
        user = self.get_user()
        blog_post = BlogPost.get_by_id(int(post_id))

        if not user:
            return self.redirect('/signup')
        if not blog_post:
            response.set_status(NOT_FOUND)
        if blog_post.author_id != user.id():
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
            return self.redirect('/posts/%d' % int(post_id))
        else:
            self.render_edit_post(
                blog_post=blog_post,
                user=user,
                params=params)


class CommentHandler(Handler):
    """Handler for the comments POST endpoint"""

    def post(self, post_id):
        blog_post = BlogPost.get_by_id(int(post_id))
        user = self.get_user()
        text = self.request.get('text')

        if blog_post and user and text:
            comment = Comment(
                post_id=blog_post.id(),
                user_id=user.id(),
                user_name=user.username,
                text=text)
            comment.put()
            blog_post.comments = blog_post.comments + 1
            blog_post.put()
            return self.redirect('/posts/%s' % post_id)
        elif not user:
            response.set_status(FORBIDDEN)
        elif not blog_post:
            response.set_status(NOT_FOUND)
        else:
            response.set_status(BAD_REQUEST)


class CommentDeleteHandler(Handler):
    """Handler for comment deletion endpoint"""

    def post(self, post_id, comment_id):

        blog_post = BlogPost.get_by_id(int(post_id))
        comment = Comment.get_by_id(int(comment_id))
        user = self.get_user()

        if comment and user and blog_post:
            entities_exist = True
        else:
            entities_exist = False

        if entities_exist and comment.user_id == user.id():
            comment.key.delete()
            blog_post.comments = blog_post.comments - 1
            blog_post.put()
            return self.redirect('/posts/%s' % post_id)
        elif entities_exist:
            response.set_status(FORBIDDEN)
        else:
            response.set_status(NOT_FOUND)


class CommentEditPage(PageHandler):
    """Handler for comment editing page"""

    def get(self, post_id, comment_id):
        blog_post = BlogPost.get_by_id(int(post_id))
        comment = Comment.get_by_id(int(comment_id))
        user = self.get_user()

        if comment and user and blog_post:
            entities_exist = True
        else:
            entities_exist = False

    def post(self, post_id, comment_id):
        blog_post = BlogPost.get_by_id(int(post_id))
        comment = Comment.get_by_id(int(comment_id))
        user = self.get_user()

        if comment and user and blog_post:
            entities_exist = True
        else:
            entities_exist = False


class LikeHandler(Handler):
    """Handler for the like/unlike POST endpoint"""

    def post(self, post_id):
        blog_post = BlogPost.get_by_id(int(post_id))
        user = self.get_user()

        if not blog_post:
            response.set_status(NOT_FOUND)
        elif not user:
            response.set_status(FORBIDDEN)
        elif (user.id() == blog_post.author_id):
            response.set_status(BAD_REQUEST)
        else:
            existing_like = Like.query(
                Like.post_id == blog_post.id(),
                Like.user_id == user.id()).fetch()

            if existing_like:
                like = existing_like[0]
                like.key.delete()
                blog_post.likes = blog_post.likes - 1
                blog_post.put()
            else:
                new_like = Like(user_id=user.id(), post_id=blog_post.id())
                new_like.put()
                blog_post.likes = blog_post.likes + 1
                blog_post.put()
            return self.redirect('/posts/%s' % post_id)


class DeleteHandler(Handler):
    """Handler for the delete page POST endpoint"""

    def post(self, post_id):
        blog_post = BlogPost.get_by_id(int(post_id))
        user = self.get_user()

        if (blog_post.author_id == user.id()):
            blog_post.key.delete()
            self.redirect('/')
        else:
            response.set_status(FORBIDDEN)


class SignupPage(Handler):
    """Handler for the user signup page"""

    def validate_params(self, request):
        username = request.get('username')
        password = request.get('password')
        verify = request.get('verify')
        email = request.get('email')

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
            existing_user = User.get_user(params['username'])
            if existing_user:
                params['user_already_exists'] = True
                params['username'] = None
                valid_form_data = False

        return (params, valid_form_data)

    def get(self):
        if self.get_user():
            return self.redirect('/welcome')
        else:
            self.render('signup.html', params={})

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
            self.render('signup.html', params=params)


class LoginPage(Handler):
    """Handler for the user login page"""

    def get(self):
        user = self.get_user()
        if user:
            return self.redirect('/welcome')
        else:
            self.render('login.html', params={})

    def post(self):
        username = self.request.get('username')
        password = self.request.get('password')

        user = User.get_user(username)

        params = {}

        if user and crypto.valid_pw(username, password, user.hashed_password):
            self.set_user(user)
            self.redirect('/welcome')
        else:
            params['login_failure'] = True

        self.render('login.html', username=username, params=params)


class WelcomePage(Handler):
    """Handler for the user welcome page"""

    def get(self):
        user = self.get_user()
        if user:
            self.render('welcome.html', user=user)
        else:
            return self.redirect('/login')


class LogoutHandler(Handler):
    """Handler for the logout endpoint"""

    def logout(self):
        self.clear_user()
        return self.redirect('/signup')

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
    ('/logout', LogoutHandler),
    (r'/posts/(\d+)', PermalinkPage),
    (r'/posts/(\d+)/delete', DeleteHandler),
    (r'/posts/(\d+)/edit', EditPage),
    (r'/posts/(\d+)/comment', CommentHandler),
    (r'/posts/(\d+)/comments/(\d+)/delete', CommentDeleteHandler),
    (r'/posts/(\d+)/comments/(\d+)/edit', CommentEditPage),
    (r'/posts/(\d+)/like', LikeHandler)
], debug=True)
