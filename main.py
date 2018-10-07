from flask import *
from flaskext.mysql import MySQL
from pymysql.err import Error as DatabaseError
import re, os, hashlib, sys, datetime
from functools import wraps
from json import dumps as jdumps

app = Flask(__name__)
app.config.from_pyfile('config.conf.py')

mysql = MySQL()
mysql.init_app(app)
db = mysql.connect()

if not db:
	raise Exception("db not loaded")

def error(template, message, **kwargs):
	return render_template(template, error_message='Error: '+message, **kwargs);

with db as cursor:
	cursor.execute('SELECT label FROM storage_condition');
	storage_condition = [i[0] for i in cursor.fetchall()];
	cursor.execute('SELECT label FROM storage_location');
	storage_location = [i[0] for i in cursor.fetchall()];
	cursor.execute('SELECT label FROM category');
	category = [i[0] for i in cursor.fetchall()];

@app.route('/')
def index():
	return render_template('index.html');

@app.errorhandler(404)
def error404(e):
	return render_template('404.html'), 404;
	
def username_exists(username):
	with db as cursor:
		cursor = mysql.get_db().cursor()
		cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
		return cursor.rowcount != 0
	
def register_user(username, password):
	with db as cursor:
		salt = os.urandom(16)
		password_hash = hashlib.pbkdf2_hmac('sha512', password.encode('utf-8'), salt, 1000, dklen=64)
		cursor.execute('INSERT INTO users (username, pw_hash, salt) VALUES (%s, %s, %s)', (username, password_hash, salt))
		return cursor.lastrowid
		
def begin_session(username, user_id):
	session['username'] = username
	session['user_id'] = user_id
	session.permanent = True
	
@app.route('/register', methods=['GET', 'POST'])
def register():
	if request.method != 'POST':
		return render_template('register.html')
	else:
		username = request.form['username'];
		if username == "":
			return error('register.html', 'Username is empty')
		if not re.match(r'^[A-Za-z0-9_\-]', username):
			return error('register.html', 'Username may only contain alphanumeric characters, hyphens, and underscores')
		if username_exists(username):
			return error('register.html', 'Username is already registered', username=username)
		password = request.form['password'];
		if password == "":
			return error('register.html', 'Password is empty', username=username)
		if password != request.form['password_confirm']:
			return error('register.html', 'Passwords do not match', username=username)
		user_id = register_user(username, password)
		begin_session(username, user_id)
		return render_template('success.html')
		
@app.route('/logout')
def logout():
	session.clear()
	return render_template('logout.html')
	
class LoginError(Exception):
	pass
	
def do_login(username, password):
	with db as cursor:
		cursor.execute('SELECT id, pw_hash, salt FROM users WHERE username = %s', (username,))
		row = cursor.fetchone();
		if row is None:
			raise LoginError('There is no user with that name')
		user_id, pw_hash, salt = row
		computed_hash = hashlib.pbkdf2_hmac('sha512', password.encode('utf-8'), salt, 1000, dklen=64)
		if pw_hash != computed_hash:
			raise LoginError("Incorrect password")
		return user_id
	
@app.route('/login', methods=['GET', 'POST'])
def login():
	if request.method != 'POST':
		return render_template('login.html', redirect=request.args.get('redirect', 'pantry'))
	try:
		user_id = do_login(request.form['username'], request.form['password'])
		begin_session(request.form['username'], user_id)
		return redirect(request.form['redirect'])
	except LoginError as e:
		return error('login.html', str(e))
		
def require_login(f):
	@wraps(f)
	def new_f(*args, **kwargs):
		if not session['username'] or not username_exists(session['username']):
			return redirect(url_for('login', redirect=url_for(f.__name__, **kwargs)))
		return f(*args, **kwargs)
	return new_f
			
def get_items(user_id):
	columns = ['description', 'product_name', 'date_purchased', 'expiration', 'storage_condition', 'storage_location', 'category']
	with db as cursor:
		cursor.execute('SELECT ' + ','.join(columns) +' FROM items WHERE user_id = %s', (user_id,))
		rows = cursor.fetchall()
		new = []
		for i, row in enumerate(rows):
			new_row = {}
			for j, column in enumerate(columns):
				new_row[column] = row[j]
			new.append(new_row)
		return new
		
def product_name(product_id):
	with db as cursor:
		db.execute('SELECT label FROM product WHERE id = %s', (product_id,))
		return db.fetchone()
		
@app.route('/pantry')
@require_login
def pantry():
	items = get_items(session['user_id'])
	for i, item in enumerate(items):
		new_item = {}
		new_item['type'] = item['product_name']
		new_item['condition'] = storage_condition[item['storage_condition']-1]
		new_item['location'] = storage_location[item['storage_location']-1]
		new_item['days'] = (item['expiration'] - datetime.datetime.now()).days
		new_item['category'] = category[item['category']-1]
		new_item['comments'] = item['description']
		items[i] = new_item
	return render_template('pantry.html', items=items)
	
@app.route('/add', methods=['POST'])
@require_login
def add():
	try:
		with db as cursor:
			cursor.execute('INSERT INTO items (date_added, user_id, category, description, product_name, date_purchased, expiration, storage_condition, storage_location) VALUES (now(), %s, %s, %s, %s, now(), now(), %s, %s)',
			(session['user_id'], int(request.form['category']), request.form['comments'], request.form['type'], int(request.form['condition']), int(request.form['location'])));
	except (KeyError) as e:
		abort(400)
	return redirect(url_for('pantry'));
	
	
def json(f):
	@wraps(f)
	def new_f(*args, **kwargs):
		return jdumps(f(*args, **kwargs))
	return new_f
		
def params(*p):
	def params_(f):
		@wraps(f)
		def new_f(*args, **kwargs):
			try:
				for param in p:
					kwargs[p] = request.args[p]
				return f(*args, **kwargs)
			except KeyError:
				abort(400)
		return new_f
	return params_

@app.route('/api/username_exists')
@json
@params('name')
def check_name(name):
	return username_exists(name)

@app.route('/api/suggestions')
@json
@params('prefix')
def suggestions(prefix):
	with db as cursor:
		cursor.execute('SELECT label FROM product WHERE category = %s AND label LIKE "%s\\% LIMIT 10', (category, prefix))
		return cursor.fetchall()
		
if __name__ == '__main__':
	app.run(host='127.0.0.1', port=5000)
	
	
	
		
	


			
