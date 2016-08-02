import re

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
