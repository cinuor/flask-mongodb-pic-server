#!/usr/bin/python2
# -*- coding: UTF-8 -*-

import bson.binary
import datetime
import hashlib
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

def save_file(f):
	#content = StringIO(f.read())
	content = StringIO(f.read())
	try:
		mime = Image.open(content).format.lower()
		if mime not in allowed_format:
			raise IOError()
	except IOError:
		flask.abort(403)

	sha1 = hashlib.sha1(content.getvalue()).hexdigest()
	#sha1 = hashlib.sha1(content).hexdigest()
	item = dict(
		content=bson.binary.Binary(content.getvalue()),
		#content=bson.binary.Binary(content),
		mime = mime,
		time = datetime.datetime.utcnow(),
		sha1 = sha1
	)
	try:
		db.files.save(item)
		return item['sha1']
	except Exception as e:
		raise e

@app.route('/')
def index():
	return """
	<!doctype html>
	<html>
		<body>
			<form action='/upload' method='post' enctype='multipart/form-data'>
				<input type='file' name='uploaded_file'>
			    <input type='submit' value='Upload'>
			</form>
		</body>
	</html>
	"""

@app.route('/upload', methods=['POST'])
def upload():
	f = flask.request.files['uploaded_file']
	sha1 = save_file(f)
	url = 'http://localhost:9001/file/%s' %(sha1,)
	return flask.jsonify({'url':url})
	#return flask.redirect('/file/'+str(sha1))

@app.route('/file/<sha1>')
def get_file(sha1):
	import bson.errors
	try:
		f = db.files.find_one({'sha1':sha1})
		if f is None:
			raise bson.errors.InvalidId()
		if flask.request.headers.get('If-Modified-Since') == f['time'].ctime():
			return flask.Response(status=304)
		resp = flask.Response(f['content'], mimetype='image/' + f['mime'])
		resp.headers['Last-Modified'] = f['time'].ctime()
		return resp
	except bson.errors.InvalidId:
		flask.abort(404)

if __name__ == '__main__':
	app.run(port=9001)