import string
import random
import hashlib

with open('secret', 'r') as f:
    secret = f.read()


def make_salt():
    return string.join(random.sample(string.ascii_letters, 20), '')


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
