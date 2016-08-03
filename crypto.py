import string
import random
import hashlib
import re

# TODO: unused so far? Review crypto notes
with open('secret', 'r') as f:
    secret = f.read()

COOKIE_PATTERN = re.compile('\w+\|\w+')


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


def extract_user_id_hash(cookie):
    match = COOKIE_PATTERN.match(cookie)
    if match:
        user_id, user_hash = match.group().split("|")
        return (user_id, user_hash)
    else:
        return (None, None)
