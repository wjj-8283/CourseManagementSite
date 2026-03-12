import sqlite3
from flask import Flask, render_template, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your-very-secret-key-change-this'  # 请务必修改为随机字符串

# 数据库初始化
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    # 学生课程表
    c.execute('''CREATE TABLE IF NOT EXISTS courses
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  student_name TEXT NOT NULL,
                  start_week INTEGER NOT NULL,
                  end_week INTEGER NOT NULL,
                  week_type TEXT NOT NULL,
                  weekday INTEGER NOT NULL,
                  start_period INTEGER NOT NULL,
                  end_period INTEGER NOT NULL)''')
    # 管理员表 (只存一条记录)
    c.execute('''CREATE TABLE IF NOT EXISTS admin
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  password_hash TEXT NOT NULL)''')
    # 学生记录表（用于判断是否首次使用）
    c.execute('''CREATE TABLE IF NOT EXISTS students
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  student_name TEXT UNIQUE NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    # 预置课表
    c.execute('''CREATE TABLE IF NOT EXISTS preset_courses
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  start_week INTEGER NOT NULL,
                  end_week INTEGER NOT NULL,
                  week_type TEXT NOT NULL,
                  weekday INTEGER NOT NULL,
                  start_period INTEGER NOT NULL,
                  end_period INTEGER NOT NULL)''')
    conn.commit()
    conn.close()

# 调用初始化
init_db()

# ---------- 页面路由 ----------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin')
def admin_page():
    return render_template('admin.html')

@app.route('/preset')
def preset_page():
    return render_template('preset.html')

# ---------- API：对外访问 ----------
@app.route('/api/courses', methods=['GET'])
def get_courses():
    student = request.args.get('student')
    if not student:
        return jsonify({'error': 'Missing student name'}), 400

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    # 检查学生是否存在
    c.execute('SELECT 1 FROM students WHERE student_name = ?', (student,))
    exists = c.fetchone()

    if not exists:
        # 首次使用：获取所有预置课程并插入到该学生名下
        c.execute('SELECT start_week, end_week, week_type, weekday, start_period, end_period FROM preset_courses')
        preset_rows = c.fetchall()
        for row in preset_rows:
            c.execute('''INSERT INTO courses 
                         (student_name, start_week, end_week, week_type, weekday, start_period, end_period)
                         VALUES (?,?,?,?,?,?,?)''',
                      (student, row[0], row[1], row[2], row[3], row[4], row[5]))
        # 记录学生
        c.execute('INSERT INTO students (student_name) VALUES (?)', (student,))
        conn.commit()
        courses = [{
            'startWeek': row[0],
            'endWeek': row[1],
            'weekType': row[2],
            'weekday': row[3],
            'startPeriod': row[4],
            'endPeriod': row[5]
        } for row in preset_rows]
        conn.close()
        return jsonify(courses)
    else:
        # 已有学生：返回其课程
        c.execute('SELECT start_week, end_week, week_type, weekday, start_period, end_period FROM courses WHERE student_name=?', (student,))
        rows = c.fetchall()
        conn.close()
        courses = [{
            'startWeek': row[0],
            'endWeek': row[1],
            'weekType': row[2],
            'weekday': row[3],
            'startPeriod': row[4],
            'endPeriod': row[5]
        } for row in rows]
        return jsonify(courses)

@app.route('/api/courses', methods=['POST'])
def save_courses():
    data = request.json
    student = data.get('student')
    courses = data.get('courses', [])
    if not student:
        return jsonify({'error': 'Missing student name'}), 400

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    # 先删除该学生原有课程
    c.execute('DELETE FROM courses WHERE student_name=?', (student,))
    # 插入新课程
    for crs in courses:
        c.execute('''INSERT INTO courses 
                     (student_name, start_week, end_week, week_type, weekday, start_period, end_period)
                     VALUES (?,?,?,?,?,?,?)''',
                  (student, crs['startWeek'], crs['endWeek'], crs['weekType'],
                   crs['weekday'], crs['startPeriod'], crs['endPeriod']))
    # 确保学生记录存在
    c.execute('INSERT OR IGNORE INTO students (student_name) VALUES (?)', (student,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

# ---------- API：管理员登录、密码设置、数据获取 ----------
@app.route('/api/admin/check_setup', methods=['GET'])
def check_setup():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM admin')
    count = c.fetchone()[0]
    conn.close()
    return jsonify({'setup_done': count > 0})

@app.route('/api/admin/setup', methods=['POST'])
def setup_password():
    data = request.json
    password = data.get('password')
    if not password:
        return jsonify({'error': 'Password required'}), 400

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM admin')
    if c.fetchone()[0] > 0:
        conn.close()
        return jsonify({'error': 'Password already set'}), 400

    password_hash = generate_password_hash(password)
    c.execute('INSERT INTO admin (password_hash) VALUES (?)', (password_hash,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.json
    password = data.get('password')
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT password_hash FROM admin LIMIT 1')
    row = c.fetchone()
    conn.close()
    if row and check_password_hash(row[0], password):
        session['admin_logged_in'] = True
        return jsonify({'status': 'ok'})
    else:
        return jsonify({'error': 'Invalid password'}), 401

@app.route('/api/admin/logout', methods=['POST'])
def admin_logout():
    session.pop('admin_logged_in', None)
    return jsonify({'status': 'ok'})

@app.route('/api/admin/all_courses', methods=['GET'])
def all_courses():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    # 必须查询 id 用于删除
    c.execute('SELECT id, student_name, start_week, end_week, week_type, weekday, start_period, end_period FROM courses ORDER BY student_name')
    rows = c.fetchall()
    conn.close()
    result = {}
    for row in rows:
        course_id = row[0]
        name = row[1]
        course = {
            'id': course_id,
            'startWeek': row[2],
            'endWeek': row[3],
            'weekType': row[4],
            'weekday': row[5],
            'startPeriod': row[6],
            'endPeriod': row[7]
        }
        if name not in result:
            result[name] = []
        result[name].append(course)
    output = [{'name': name, 'courses': courses} for name, courses in result.items()]
    return jsonify(output)

@app.route('/api/admin/query', methods=['POST'])
def query_students():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.json
    week = data.get('week')
    weekdays = data.get('weekdays', [])
    start_period = data.get('startPeriod')
    end_period = data.get('endPeriod')

    if not all([week, weekdays, start_period, end_period]):
        return jsonify({'error': 'Missing parameters'}), 400

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT student_name, start_week, end_week, week_type, weekday, start_period, end_period FROM courses')
    rows = c.fetchall()
    conn.close()

    matched_students = set()
    for row in rows:
        student_name, s_week, e_week, week_type, wday, s_period, e_period = row
        if week < s_week or week > e_week:
            continue
        if week_type == 'odd' and week % 2 == 0:
            continue
        if week_type == 'even' and week % 2 == 1:
            continue
        if wday not in weekdays:
            continue
        if e_period < start_period or s_period > end_period:
            continue
        matched_students.add(student_name)

    return jsonify(list(matched_students))

# ---------- API：预置课表管理 ----------
@app.route('/api/preset_courses', methods=['GET'])
def get_preset_courses():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT id, start_week, end_week, week_type, weekday, start_period, end_period FROM preset_courses ORDER BY id')
    rows = c.fetchall()
    conn.close()
    preset_list = [{
        'id': row[0],
        'startWeek': row[1],
        'endWeek': row[2],
        'weekType': row[3],
        'weekday': row[4],
        'startPeriod': row[5],
        'endPeriod': row[6]
    } for row in rows]
    return jsonify(preset_list)

@app.route('/api/preset_courses', methods=['POST'])
def add_preset_course():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.json
    required = ['startWeek', 'endWeek', 'weekType', 'weekday', 'startPeriod', 'endPeriod']
    if not all(k in data for k in required):
        return jsonify({'error': 'Missing fields'}), 400

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''INSERT INTO preset_courses 
                 (start_week, end_week, week_type, weekday, start_period, end_period)
                 VALUES (?,?,?,?,?,?)''',
              (data['startWeek'], data['endWeek'], data['weekType'],
               data['weekday'], data['startPeriod'], data['endPeriod']))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'}), 201

@app.route('/api/preset_courses/<int:course_id>', methods=['DELETE'])
def delete_preset_course(course_id):
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('DELETE FROM preset_courses WHERE id = ?', (course_id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

# ---------- API：管理员删除课程 ----------
@app.route('/api/admin/course/<int:course_id>', methods=['DELETE'])
def delete_course(course_id):
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('DELETE FROM courses WHERE id = ?', (course_id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

@app.route('/api/admin/student_courses', methods=['DELETE'])
def delete_student_courses():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    student_name = request.args.get('name')
    if not student_name:
        return jsonify({'error': 'Missing student name'}), 400
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('DELETE FROM courses WHERE student_name = ?', (student_name,))
    c.execute('DELETE FROM students WHERE student_name = ?', (student_name,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

# 清空所有预置课程
@app.route('/api/preset_courses/clear', methods=['POST'])
def clear_preset_courses():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('DELETE FROM preset_courses')
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=12345, debug=True)