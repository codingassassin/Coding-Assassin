#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import webapp2
import os
import jinja2
import re
import hmac
import random
import string
import json

from google.appengine.ext import db


SECRET="silenda"
def make_salt():
	 return ''.join(random.choice(string.letters) for x in xrange(5))
def make_pass(username, salt=''):
	if salt=='':
		salt=make_salt()
	return "%s|%s"%(hmac.new(SECRET, "%s%s"%(username, salt)).hexdigest(), salt)
def make_hash(username, salt=''):
	if salt=='':
		salt=make_salt()
	return "%s|%s|%s"%(username, 
					hmac.new(SECRET, "%s%s"%(username, salt)).hexdigest(), 
					salt)

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
								autoescape = True)


class User(db.Model):
	username = db.StringProperty(required = True)
	password = db.StringProperty(required = True)
	email = db.StringProperty(required = False)

class Post(db.Model):
	subject = db.StringProperty(required = True)
	post = db.TextProperty(required = True)
	created = db.DateTimeProperty(auto_now_add = True)

class Handler(webapp2.RequestHandler):
	def write(self, *a, **kw):
		self.response.out.write(*a, **kw)
	
	def renderStr(self, template, **params):
		t = jinja_env.get_template(template)
		return t.render(**params)
		
	def render(self, template, **kw):
		self.write(self.renderStr(template, **kw))
		
class MainPage(Handler):
	def get(self):
		self.redirect("/blog")
	
class BlogPage(Handler):
	def get(self):
		posts = db.GqlQuery("SELECT * FROM Post ORDER BY created DESC LIMIT 10")
		self.render("frontblog.html", posts=posts)
		
class JsonBlogPage(Handler):
	def get(self):
		self.response.headers['Content-Type'] = "application/json"
		posts = db.GqlQuery("SELECT * FROM Post ORDER BY created DESC LIMIT 10")
		lstr = []
		for p in posts:
			lstr.append(convertToJson(p))
		self.write(json.dumps(lstr))

class LoginPage(Handler):
	def renderPage(self, username='', password='', error=''):
		self.render("login.html",username=username, password=password, error=error)
	def get(self):
		self.renderPage()
	def post(self):
		username = self.request.get("username")
		password = self.request.get("password")
		usr = db.GqlQuery("SELECT * FROM User WHERE username =\'%s\'"%username)
		usr = usr.get()
		
		if  not (username and password) or not usr:
			self.renderPage(error="Invalid login")
			
		else:
			dbPass = usr.password
			dbSalt = dbPass.split('|')[1]
			if usr.password != make_pass(password, dbSalt):
				self.renderPage(error="Invalid login")
			else:
				cookiestr = make_hash(str(username))
				self.response.headers.add_header('Set-Cookie',
										'username=%s;Path=/'%cookiestr)
				self.redirect("/blog/welcome")
			
class LogoutPage(Handler):
	def get(self):
		self.response.headers['Set-Cookie']='username=;Path=/'
		self.redirect("/blog/signup")


class SignupPage(Handler):
	USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
	PASS_RE = re.compile(r"^.{3,20}$")
	EMAIL_RE = re.compile(r"^[\S]+@[\S]+\.[\S]+$")

	def valid_username(self, username):
		return username and self.USER_RE.match(username)
	def valid_password(self, password):
		return password and self.PASS_RE.match(password)
	def valid_email(self, email):
		if (not email) or self.EMAIL_RE.match(email):
			return True
		else:
			return False
	
	def renderPage(self,username='', errorusr='',
						password='', errorpass='',
						verify='', errorvrfy='',
						email='', erroremail=''):
		self.render("signup.html",username=username, errorusr=errorusr,
									password=password, errorpass=errorpass,
									verify=verify, errorvrfy=errorvrfy,
									email=email, erroremail=erroremail)
	def get(self):
		self.renderPage()
	def post(self):
		error_there = False
		
		username = self.request.get("username")
		password = self.request.get("password")
		verify = self.request.get("verify")
		email = self.request.get("email")
		
		params = dict(username = username, email = email)
		
		if not self.valid_username(username):
			params['errorusr']='That is not a valid username.'
			error_there = True
		
		if not self.valid_password(password):
			params['errorpass']='That was not a valid password.'
			error_there = True
		elif verify != password:
			params['errorvrfy']='Your passwords did not match.'
			error_there = True
		
		if not self.valid_email(email):
			params['erroremail']='That is not a valid email.'
			error_there = True
		
		if error_there:
			self.renderPage(**params)
		else:
			user = User(username=username, password=make_pass(password), email=email)
			user.put()
			cookiestr = make_hash(str(username))
			self.response.headers.add_header('Set-Cookie',
									'username=%s;Path=/'%cookiestr)
			self.redirect("/blog/welcome")
		
class WelcomePage(Handler):
	def get(self):
		cookiestr = self.request.cookies.get("username")
		cookieprts = str(cookiestr).split('|')
		if cookiestr and cookiestr == make_hash(cookieprts[0], cookieprts[2]):
			self.render('welcome.html',username=cookieprts[0])
		else:
			self.redirect('/blog/signup')

class NewpostPage(Handler):
	def renderFront(self, subject="", content="", error=""):
		self.render("newpost.html", subject=subject, content=content, error=error)
	def get(self):
		self.renderFront()
	def post(self):
		subject = self.request.get("subject")
		content = self.request.get("content")
		
		if subject and content:
			p = Post(subject=subject, post=content)
			p.put()
			postId = str(p.key().id())
			self.redirect("/blog/%s"%postId)
		else:
			error = "subject and content please!"
			self.renderFront(subject, content, error)
		
class PermaPage(Handler):
	def get(self, postId):
		p = Post.get_by_id(int(postId))
		if p:
			self.render("permapage.html", post=p)
		else:
			self.error(404)
			
def convertToJson(post):
	return {"created": post.created.strftime("%a %b  %d %H:%M:%S %Y"), "content": str(post.post), "subject": str(post.subject)}	
class JsonPermaPage(Handler):
	def get(self, postId):
		self.response.headers['Content-Type'] = "application/json"
		p = Post.get_by_id(int(postId))
		if p:
			self.write(json.dumps(convertToJson(p)))
		else:
			self.error(404)

app = webapp2.WSGIApplication([('/',MainPage),
								('/blog', BlogPage),
								('/blog/.json', JsonBlogPage),
								('/blog/login',LoginPage),
								('/blog/logout',LogoutPage),
								('/blog/signup', SignupPage),
								('/blog/welcome', WelcomePage),
								('/blog/newpost', NewpostPage),
								('/blog/([0-9]+)', PermaPage),
								('/blog/([0-9]+).json', JsonPermaPage)],
								debug=True)