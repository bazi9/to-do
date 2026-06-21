import sqlite3
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, template_folder='.', static_folder='.', static_url_path='')
app.secret_key = 'super_secret_key_change_me_later'
DB_FILE = 'todo.db'

# --- DATABASE SETUP ---
def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0
        )''')
        
        try:
            conn.execute('ALTER TABLE users ADD COLUMN email TEXT DEFAULT ""')
        except sqlite3.OperationalError:
            pass 

        conn.execute('''CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            completed INTEGER DEFAULT 0
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS subtasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            completed INTEGER DEFAULT 0
        )''')
        
        conn.execute('''CREATE TABLE IF NOT EXISTS keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subtask_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            completed INTEGER DEFAULT 0
        )''')
        
        admin = conn.execute('SELECT * FROM users WHERE username = ?', ('baziboo',)).fetchone()
        if not admin:
            pwd = generate_password_hash('Ionut91.')
            conn.execute('INSERT INTO users (username, password, is_admin) VALUES (?, ?, 1)', ('baziboo', pwd))
        conn.commit()

init_db()

# --- AUTHENTICATION MIDDLEWARE ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('welcome'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or not session.get('is_admin'):
            flash('Admin privileges required to view that page.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# --- PUBLIC & AUTH ROUTES ---
@app.route('/welcome')
def welcome():
    if 'user_id' in session:
        return redirect(url_for('index'))
    return render_template('welcome.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        
        with get_db() as conn:
            user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
            if user:
                flash('Username already exists. Please login or choose another.', 'danger')
            elif username and password:
                hashed_pw = generate_password_hash(password)
                conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_pw))
                conn.commit()
                flash('Registration successful! Please log in.', 'success')
                return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        
        with get_db() as conn:
            user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
            if user and check_password_hash(user['password'], password):
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['is_admin'] = user['is_admin']
                return redirect(url_for('index'))
            else:
                flash('Invalid username or password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('welcome'))

# --- ADMIN ROUTES ---
@app.route('/users')
@admin_required
def manage_users():
    with get_db() as conn:
        users_raw = conn.execute('SELECT * FROM users ORDER BY id ASC').fetchall()
        users = []
        
        for u in users_raw:
            user_dict = dict(u)
            tasks_raw = conn.execute('SELECT * FROM tasks WHERE user_id = ?', (u['id'],)).fetchall()
            
            user_dict['task_count'] = len(tasks_raw)
            completed_tasks = 0
            
            for t in tasks_raw:
                task_dict = dict(t)
                subtasks_raw = conn.execute('SELECT * FROM subtasks WHERE task_id = ?', (t['id'],)).fetchall()
                
                subtasks = []
                for st in subtasks_raw:
                    st_dict = dict(st)
                    keywords = conn.execute('SELECT completed FROM keywords WHERE subtask_id = ?', (st['id'],)).fetchall()
                    
                    kw_total = len(keywords)
                    kw_completed = sum(1 for kw in keywords if kw['completed'])
                    
                    if kw_total > 0 and kw_completed == kw_total:
                        st_dict['completed'] = 1
                        
                    subtasks.append(st_dict)
                    
                total_subtasks = len(subtasks)
                completed_subtasks = sum(1 for st in subtasks if st['completed'])
                
                if total_subtasks > 0 and completed_subtasks == total_subtasks:
                    task_dict['completed'] = 1
                    
                if task_dict.get('completed') == 1:
                    completed_tasks += 1
                    
            user_dict['completed_task_count'] = completed_tasks
            users.append(user_dict)
            
    return render_template('admin_users.html', users=users, username=session['username'])

@app.route('/admin/promote/<int:target_id>', methods=['POST'])
@admin_required
def promote_user(target_id):
    with get_db() as conn:
        conn.execute('UPDATE users SET is_admin = 1 WHERE id = ?', (target_id,))
        conn.commit()
    flash('User successfully promoted to Admin.', 'success')
    return redirect(url_for('manage_users'))

@app.route('/admin/demote/<int:target_id>', methods=['POST'])
@admin_required
def demote_user(target_id):
    with get_db() as conn:
        target_user = conn.execute('SELECT username FROM users WHERE id = ?', (target_id,)).fetchone()
        if target_user and target_user['username'] == 'baziboo':
            flash('SECURITY ALERT: The master owner account cannot be demoted.', 'danger')
            return redirect(url_for('manage_users'))
            
        conn.execute('UPDATE users SET is_admin = 0 WHERE id = ?', (target_id,))
        conn.commit()
    flash('Admin privileges revoked successfully.', 'warning')
    return redirect(url_for('manage_users'))

@app.route('/admin/delete/<int:target_id>', methods=['POST'])
@admin_required
def delete_user(target_id):
    if target_id == session['user_id']:
        flash('You cannot delete your own admin account!', 'danger')
        return redirect(url_for('manage_users'))
        
    with get_db() as conn:
        target_user = conn.execute('SELECT username FROM users WHERE id = ?', (target_id,)).fetchone()
        if target_user and target_user['username'] == 'baziboo':
            flash('SECURITY ALERT: The master owner account cannot be deleted.', 'danger')
            return redirect(url_for('manage_users'))
            
        conn.execute('DELETE FROM users WHERE id = ?', (target_id,))
        conn.execute('DELETE FROM tasks WHERE user_id = ?', (target_id,))
        conn.execute('DELETE FROM keywords WHERE subtask_id IN (SELECT id FROM subtasks WHERE task_id NOT IN (SELECT id FROM tasks))')
        conn.execute('DELETE FROM subtasks WHERE task_id NOT IN (SELECT id FROM tasks)')
        conn.commit()
    flash('User and all their tasks have been deleted.', 'success')
    return redirect(url_for('manage_users'))

# --- APP ROUTES ---
@app.route('/')
@login_required
def index():
    user_id = session['user_id']
    is_admin = session['is_admin']
    
    with get_db() as conn:
        user_info = conn.execute('SELECT email FROM users WHERE id = ?', (user_id,)).fetchone()
        email = user_info['email'] if user_info['email'] else "No email added yet"
        total_tasks_count = conn.execute('SELECT COUNT(*) FROM tasks WHERE user_id = ?', (user_id,)).fetchone()[0]

        tasks_raw = conn.execute('''
            SELECT tasks.*, users.username FROM tasks 
            JOIN users ON tasks.user_id = users.id 
            WHERE tasks.user_id = ?
        ''', (user_id,)).fetchall()
            
        tasks = []
        total_tasks_completed = 0 
        
        for t in tasks_raw:
            task_dict = dict(t)
            subtasks_raw = conn.execute('SELECT * FROM subtasks WHERE task_id = ?', (t['id'],)).fetchall()
            
            subtasks = []
            for st in subtasks_raw:
                st_dict = dict(st)
                keywords = conn.execute('SELECT * FROM keywords WHERE subtask_id = ?', (st['id'],)).fetchall()
                st_dict['keywords'] = [dict(kw) for kw in keywords]
                
                st_dict['kw_total'] = len(keywords)
                st_dict['kw_completed'] = sum(1 for kw in keywords if kw['completed'])
                
                if st_dict['kw_total'] > 0 and st_dict['kw_completed'] == st_dict['kw_total']:
                    st_dict['completed'] = 1
                
                subtasks.append(st_dict)
                
            task_dict['subtasks'] = subtasks
            task_dict['total_subtasks'] = len(task_dict['subtasks'])
            task_dict['completed_subtasks'] = sum(1 for st in task_dict['subtasks'] if st['completed'])
            
            if task_dict['total_subtasks'] > 0 and task_dict['completed_subtasks'] == task_dict['total_subtasks']:
                task_dict['completed'] = 1
                
            if task_dict.get('completed') == 1:
                total_tasks_completed += 1
            
            tasks.append(task_dict)
            
    return render_template(
        'index.html', 
        tasks=tasks, 
        username=session['username'], 
        is_admin=is_admin,
        email=email,
        total_tasks_count=total_tasks_count,
        total_tasks_completed=total_tasks_completed 
    )

@app.route('/update_email', methods=['POST'])
@login_required
def update_email():
    new_email = request.form.get('email', '').strip()
    if new_email:
        with get_db() as conn:
            conn.execute('UPDATE users SET email = ? WHERE id = ?', (new_email, session['user_id']))
            conn.commit()
    return redirect(url_for('index'))

@app.route('/add', methods=['POST'])
@login_required
def add():
    title = request.form.get('title', '').strip().capitalize()
    if title:
        with get_db() as conn:
            conn.execute('INSERT INTO tasks (user_id, title) VALUES (?, ?)', (session['user_id'], title))
            conn.commit()
    return redirect(url_for('index'))

@app.route('/delete/<int:task_id>', methods=['POST'])
@login_required
def delete(task_id):
    with get_db() as conn:
        task = conn.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone()
        if task and task['user_id'] == session['user_id']:
            conn.execute('DELETE FROM keywords WHERE subtask_id IN (SELECT id FROM subtasks WHERE task_id = ?)', (task_id,))
            conn.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
            conn.execute('DELETE FROM subtasks WHERE task_id = ?', (task_id,))
            conn.commit()
    return redirect(url_for('index'))

@app.route('/edit/<int:task_id>', methods=['POST'])
@login_required
def edit(task_id):
    new_title = request.form.get('new_title', '').strip().capitalize()
    if new_title:
        with get_db() as conn:
            task = conn.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone()
            if task and task['user_id'] == session['user_id']:
                conn.execute('UPDATE tasks SET title = ? WHERE id = ?', (new_title, task_id))
                conn.commit()
    return redirect(url_for('index'))

@app.route('/add_sub/<int:task_id>', methods=['POST'])
@login_required
def add_sub(task_id):
    sub_title = request.form.get('sub_title', '').strip().capitalize()
    if sub_title:
        with get_db() as conn:
            task = conn.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone()
            if task and task['user_id'] == session['user_id']:
                conn.execute('INSERT INTO subtasks (task_id, title) VALUES (?, ?)', (task_id, sub_title))
                conn.commit()
    return redirect(url_for('index'))

@app.route('/delete_sub/<int:task_id>/<int:sub_id>', methods=['POST'])
@login_required
def delete_sub(task_id, sub_id):
    with get_db() as conn:
        task = conn.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone()
        if task and task['user_id'] == session['user_id']:
            conn.execute('DELETE FROM keywords WHERE subtask_id = ?', (sub_id,))
            conn.execute('DELETE FROM subtasks WHERE id = ?', (sub_id,))
            conn.commit()
    return redirect(url_for('index'))

@app.route('/edit_sub/<int:task_id>/<int:sub_id>', methods=['POST'])
@login_required
def edit_sub(task_id, sub_id):
    new_title = request.form.get('new_title', '').strip().capitalize()
    if new_title:
        with get_db() as conn:
            task = conn.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone()
            if task and task['user_id'] == session['user_id']:
                conn.execute('UPDATE subtasks SET title = ? WHERE id = ?', (new_title, sub_id))
                conn.commit()
    return redirect(url_for('index'))

@app.route('/toggle_sub/<int:task_id>/<int:sub_id>', methods=['POST'])
@login_required
def toggle_sub(task_id, sub_id):
    with get_db() as conn:
        task = conn.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone()
        if task and task['user_id'] == session['user_id']:
            subtask = conn.execute('SELECT completed FROM subtasks WHERE id = ?', (sub_id,)).fetchone()
            new_status = 0 if subtask['completed'] else 1
            conn.execute('UPDATE subtasks SET completed = ? WHERE id = ?', (new_status, sub_id))
            conn.commit()
    return redirect(url_for('index'))

# --- KEYWORD ROUTES ---
@app.route('/add_keyword/<int:sub_id>', methods=['POST'])
@login_required
def add_keyword(sub_id):
    title = request.form.get('title', '').strip().lower()
    if title:
        with get_db() as conn:
            conn.execute('INSERT INTO keywords (subtask_id, title) VALUES (?, ?)', (sub_id, title))
            conn.commit()
    return redirect(url_for('index'))

@app.route('/toggle_keyword/<int:keyword_id>', methods=['POST'])
@login_required
def toggle_keyword(keyword_id):
    with get_db() as conn:
        kw = conn.execute('SELECT completed FROM keywords WHERE id = ?', (keyword_id,)).fetchone()
        if kw:
            new_status = 0 if kw['completed'] else 1
            conn.execute('UPDATE keywords SET completed = ? WHERE id = ?', (new_status, keyword_id))
            conn.commit()
    return redirect(url_for('index'))

@app.route('/edit_keyword/<int:keyword_id>', methods=['POST'])
@login_required
def edit_keyword(keyword_id):
    new_title = request.form.get('new_title', '').strip().lower()
    if new_title:
        with get_db() as conn:
            conn.execute('UPDATE keywords SET title = ? WHERE id = ?', (new_title, keyword_id))
            conn.commit()
    return redirect(url_for('index'))

@app.route('/delete_keyword/<int:keyword_id>', methods=['POST'])
@login_required
def delete_keyword(keyword_id):
    with get_db() as conn:
        conn.execute('DELETE FROM keywords WHERE id = ?', (keyword_id,))
        conn.commit()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)