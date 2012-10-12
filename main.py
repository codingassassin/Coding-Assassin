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
	return "%s|%s|%s"%(username, hmac.new(SECRET, "%s%s"%(username, salt)).hexdigest(), salt)

def convertToJson(post):
	return {"created": post.created.strftime("%a %b  %d %H:%M:%S %Y"), "content": str(post.post), "subject": str(post.subject)}


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
		self.render("index.html")
		
class JsonBlogPage(Handler):
	def get(self):
		pass

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
								('/blog/newpost', NewpostPage),
								('/blog/([0-9]+)', PermaPage),
								('/blog/([0-9]+).json', JsonPermaPage)],
								debug=True)