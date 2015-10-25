#!/usr/bin/python2
# -*- coding: UTF-8 -*-

import bson.binary
import datetime
import hashlib
import bson.errors
try:
	from StringIO import StringIO
except ImportError:
	from io import BytesIO as StringIO


import flask
import pymongo
from PIL import Image

app = flask.Flask(__name__)
app.debug = True
db = pymongo.MongoClient('localhost',27017).test
allowed_format = ['jpeg','gif', 'png']


@app.route('/')
def index():
	return """
	<!doctype html>
	<html>
		<body>
			<form action='/upload' method='post' enctype='multipart/form-data'>
				<input type='file' name='uploadedfile'>
			    <input type='submit' value='Upload'>
			</form>
		</body>
	</html>
	"""

@app.route('/update/<sha1>')
def test(sha1):
	return """
	<!doctype html>
	<html>
		<body>
			<form action='/update/%s' method='post' enctype='multipart/form-data'>
				<input type='file' name='updatedfile'>
			    <input type='submit' value='Update'>
			</form>
		</body>
	</html>
	""" %(sha1,)

#remove image
@app.route('/remove/<sha1>')
def remove(sha1):
	try:
		imageitem = db.files.find_one({'sha1':sha1})
		if imageitem is None:
			raise bson.errors.InvalidId()
		result = db.files.remove({'sha1':sha1})
		return flask.jsonify({'operation':result['ok']})
	except bson.errors.InvalidId:
		flask.abort(404)

#get image
@app.route('/image/<sha1>')
def download(sha1):
	try:
		imageitem = db.files.find_one({'sha1':sha1})
		if imageitem is None:
			raise bson.errors.InvalidId()
		if flask.request.headers.get('If-Modified-Since') == imageitem['time'].ctime():
			return flask.Response(status=304)
		resp = flask.Response(imageitem['content'], mimetype='image/' + imageitem['mime'])
		resp.headers['Last-Modified'] = imageitem['time'].ctime()
		return resp
	except bson.errors.InvalidId:
		flask.abort(404)

#upload image
@app.route('/upload', methods=['POST'])
def upload():
	uploadedfile = flask.request.files['uploadedfile']
	try:
		sha1 = save_file(uploadedfile)
		return flask.jsonify({'imageid':sha1})
	except Exception as e:
		flask.abort(400)

#update image
@app.route('/update/<sha1>', methods=['POST'])
def update(sha1):
	updatedfile = flask.request.files['updatedfile']
	try:
		update_file(sha1, updatedfile)
		return flask.jsonify({'imageid':sha1})
	except Exception as e:
		flask.abort(404)



#check image type
def formate_check(content):
	global allowed_format
	try:
		mime = Image.open(content).format.lower()
		if mime not in allowed_format:
			raise IOError()
		return mime
	except IOError:
		raise IOError

#from the request get the file content
def get_content(_file):
	return StringIO(_file.read())

def save_file(uploadedfile):
	content = get_content(uploadedfile)
	mime = formate_check(content)
	sha1 = hashlib.sha1(content.getvalue()).hexdigest()
	imageitem = dict(
		content=bson.binary.Binary(content.getvalue()),
		mime = mime,
		time = datetime.datetime.utcnow(),
		sha1 = sha1
	)
	try:
		db.files.save(imageitem)
		return imageitem['sha1']
	except pymongo.errors.WriteError:
		raise pymongo.errors.WriteError

def update_file(sha1, updatedfile):
	imageitem = db.files.find_one({'sha1':sha1})
	if imageitem is None:
		raise bson.errors.InvalidId()
	content = get_content(updatedfile)
	formate_check(content)
	try:
		db.files.update({'sha1':sha1}, {'$set':{'content':bson.binary.Binary(content.getvalue()),'time':datetime.datetime.utcnow()}})
	except Exception as e:
		raise e

if __name__ == '__main__':
	app.run(port=9001)