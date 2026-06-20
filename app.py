from flask import Flask, render_template, request, redirect, url_for

# This special configuration tells Flask to look for HTML and CSS in the current main folder
app = Flask(__name__, template_folder='.', static_folder='.', static_url_path='')

# We will use a dictionary to act as our "database" in server memory
tasks_db = {}
task_id_counter = 1
subtask_id_counter = 1

@app.route('/')
def index():
    # Pass the tasks to the HTML page
    return render_template('index.html', tasks=tasks_db.values())

@app.route('/add', methods=['POST'])
def add():
    global task_id_counter
    title = request.form.get('title', '').strip()
    if title:
        tasks_db[str(task_id_counter)] = {
            'id': str(task_id_counter), 
            'title': title, 
            'completed': False, 
            'subtasks': {}
        }
        task_id_counter += 1
    return redirect(url_for('index'))

@app.route('/delete/<task_id>', methods=['POST'])
def delete(task_id):
    tasks_db.pop(task_id, None)
    return redirect(url_for('index'))

@app.route('/edit/<task_id>', methods=['POST'])
def edit(task_id):
    new_title = request.form.get('new_title', '').strip()
    if new_title and task_id in tasks_db:
        tasks_db[task_id]['title'] = new_title
    return redirect(url_for('index'))

@app.route('/add_sub/<task_id>', methods=['POST'])
def add_sub(task_id):
    global subtask_id_counter
    sub_title = request.form.get('sub_title', '').strip()
    if sub_title and task_id in tasks_db:
        tasks_db[task_id]['subtasks'][str(subtask_id_counter)] = {
            'id': str(subtask_id_counter), 
            'title': sub_title, 
            'completed': False
        }
        subtask_id_counter += 1
    return redirect(url_for('index'))

@app.route('/delete_sub/<task_id>/<sub_id>', methods=['POST'])
def delete_sub(task_id, sub_id):
    if task_id in tasks_db:
        tasks_db[task_id]['subtasks'].pop(sub_id, None)
    return redirect(url_for('index'))

@app.route('/edit_sub/<task_id>/<sub_id>', methods=['POST'])
def edit_sub(task_id, sub_id):
    new_title = request.form.get('new_title', '').strip()
    if new_title and task_id in tasks_db and sub_id in tasks_db[task_id]['subtasks']:
        tasks_db[task_id]['subtasks'][sub_id]['title'] = new_title
    return redirect(url_for('index'))

@app.route('/toggle_sub/<task_id>/<sub_id>', methods=['POST'])
def toggle_sub(task_id, sub_id):
    if task_id in tasks_db and sub_id in tasks_db[task_id]['subtasks']:
        current = tasks_db[task_id]['subtasks'][sub_id]['completed']
        tasks_db[task_id]['subtasks'][sub_id]['completed'] = not current
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
