import os
from flask import Flask, render_template, request, redirect, send_from_directory, session
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# DB setup
def init_db():
    conn = sqlite3.connect('notes.db')
    c = conn.cursor()
    # Ensure the column 'type' exists, add if not
    c.execute("PRAGMA table_info(notes)")
    columns = [col[1] for col in c.fetchall()]
    if 'type' not in columns:
        try:
            c.execute("ALTER TABLE notes ADD COLUMN type TEXT")
        except:
            pass  # Ignore if already exists or locked

    # Create table if not exists
    c.execute('''CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        subject TEXT,
        year TEXT,
        semester TEXT,
        description TEXT,
        filename TEXT,
        uploaded_at TEXT,
        type TEXT
    )''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    selected_year = request.args.get('year', 'all')
    selected_subject = request.args.get('subject', 'all')

    conn = sqlite3.connect('notes.db')
    c = conn.cursor()

    # Dropdown data
    c.execute("SELECT DISTINCT year FROM notes ORDER BY year")
    available_years = [row[0] for row in c.fetchall()]

    c.execute("SELECT DISTINCT subject FROM notes ORDER BY subject")
    available_subjects = [row[0] for row in c.fetchall()]

    # Build query
    query = "SELECT * FROM notes WHERE 1=1"
    params = []

    if selected_year != 'all':
        query += " AND year = ?"
        params.append(selected_year)

    if selected_subject != 'all':
        query += " AND subject = ?"
        params.append(selected_subject)

    query += " ORDER BY year, semester, uploaded_at DESC"
    c.execute(query, tuple(params))
    notes = c.fetchall()
    conn.close()

    return render_template('index.html',
                           notes=notes,
                           is_admin=session.get('admin'),
                           selected_year=selected_year,
                           selected_subject=selected_subject,
                           available_years=available_years,
                           available_subjects=available_subjects)

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    valid_passwords = ['test', 'password']  # Replace in production

    if request.method == 'POST':
        password = request.form['password']
        if password in valid_passwords:
            session['admin'] = True
            return redirect('/')
        else:
            return "<h3>Incorrect password. <a href='/admin'>Try again</a></h3>"
    return render_template('admin_login.html')

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect('/')

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if not session.get('admin'):
        return redirect('/admin')

    if request.method == 'POST':
        title = request.form['title']
        subject = request.form['subject']
        note_type = request.form['type']
        year = request.form['year']
        semester = request.form['semester']
        description = request.form['description']
        file = request.files['file']

        if file and file.filename.endswith('.pdf'):
            filename = f"{year}_{semester}_{file.filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            conn = sqlite3.connect('notes.db')
            c = conn.cursor()
            c.execute("""INSERT INTO notes 
                         (title, subject, year, semester, description, filename, uploaded_at, type) 
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                      (title, subject, year, semester, description, filename,
                       datetime.now().strftime("%Y-%m-%d %H:%M:%S"), note_type))
            conn.commit()
            conn.close()
            return redirect('/')

    return render_template('upload.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/delete/<int:note_id>', methods=['POST'])
def delete_note(note_id):
    if not session.get('admin'):
        return redirect('/admin')

    conn = sqlite3.connect('notes.db')
    c = conn.cursor()
    c.execute("SELECT filename FROM notes WHERE id = ?", (note_id,))
    result = c.fetchone()

    if result:
        filename = result[0]
        c.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        conn.commit()

        try:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Error deleting file: {e}")

    conn.close()
    return redirect('/')

if __name__ == '__main__':
    init_db()
    app.run(debug=True)

   # app.run(host='0.0.0.0', port=5000, debug=True)
