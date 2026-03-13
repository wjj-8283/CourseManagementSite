import sqlite3
import time
import os
import shutil
from flask import Flask, render_template, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash

# 确保 backup 目录存在
os.makedirs('backup', exist_ok=True)
def copy_file(src, dst):
    try:
        # 检查源文件是否存在
        if os.path.exists(src):
            # 复制文件
            shutil.copy2(src, dst)
            print(f"文件 {src} 复制到 {dst} 成功")
        else:
            print(f"源文件 {src} 不存在")
    except Exception as e:
        print(f"文件复制失败: {e}")

def backup_db(action):
    current_time = time.strftime('%Y%m%d%H%M%S', time.localtime())
    sep = os.sep
    backup_file = f"backup{sep}database_backup_{current_time}_{action}.db"
    copy_file('database.db', backup_file)

app = Flask(__name__)
app.secret_key = 'ka9wjdpmxmjaipodadjkfsaoidaspoas0dialksajkn2kjoijau9sjdjkhshdakjd'  # 请务必修改为随机字符串

# 数据库初始化
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    # 修改 students 表，添加 password_hash 字段
    c.execute('''CREATE TABLE IF NOT EXISTS students
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  student_name TEXT UNIQUE NOT NULL,
                  password_hash TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # 如果表已存在但缺少 password_hash 列，则添加
    c.execute("PRAGMA table_info(students)")
    columns = [col[1] for col in c.fetchall()]
    if 'password_hash' not in columns:
        c.execute("ALTER TABLE students ADD COLUMN password_hash TEXT")

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
    ua = request.headers.get('User-Agent', '').lower()
    if 'mobile' in ua or 'android' in ua or 'iphone' in ua:
        return render_template('index_mobile.html')
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
    c.execute('SELECT password_hash FROM students WHERE student_name = ?', (student,))
    row = c.fetchone()
    if row is None:
        # 首次使用：创建学生记录（无密码），并插入预置课程
        c.execute('INSERT INTO students (student_name) VALUES (?)', (student,))
        c.execute('SELECT start_week, end_week, week_type, weekday, start_period, end_period FROM preset_courses')
        preset_rows = c.fetchall()
        for pr in preset_rows:
            c.execute('''INSERT INTO courses 
                         (student_name, start_week, end_week, week_type, weekday, start_period, end_period)
                         VALUES (?,?,?,?,?,?,?)''',
                      (student, pr[0], pr[1], pr[2], pr[3], pr[4], pr[5]))
        conn.commit()
        has_password = False
        courses = [{
            'startWeek': pr[0], 'endWeek': pr[1], 'weekType': pr[2],
            'weekday': pr[3], 'startPeriod': pr[4], 'endPeriod': pr[5]
        } for pr in preset_rows]
    else:
        has_password = row[0] is not None
        # 获取该学生的课程
        c.execute('SELECT start_week, end_week, week_type, weekday, start_period, end_period FROM courses WHERE student_name=?', (student,))
        rows = c.fetchall()
        courses = [{
            'startWeek': r[0], 'endWeek': r[1], 'weekType': r[2],
            'weekday': r[3], 'startPeriod': r[4], 'endPeriod': r[5]
        } for r in rows]
    conn.close()
    return jsonify({'courses': courses, 'has_password': has_password})



@app.route('/api/courses', methods=['POST'])
def save_courses():
    data = request.json
    student = data.get('student')
    courses = data.get('courses', [])
    if not student:
        return jsonify({'error': 'Missing student name'}), 400

    # 验证当前会话是否已认证为该学生
    if session.get('student_name') != student:
        return jsonify({'error': 'Unauthorized, please login first'}), 401

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('DELETE FROM courses WHERE student_name=?', (student,))
    for crs in courses:
        c.execute('''INSERT INTO courses 
                     (student_name, start_week, end_week, week_type, weekday, start_period, end_period)
                     VALUES (?,?,?,?,?,?,?)''',
                  (student, crs['startWeek'], crs['endWeek'], crs['weekType'],
                   crs['weekday'], crs['startPeriod'], crs['endPeriod']))
    c.execute('INSERT OR IGNORE INTO students (student_name) VALUES (?)', (student,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

@app.route('/api/student/load_preset', methods=['POST'])
def student_load_preset():
    data = request.json
    student = data.get('name')
    if not student:
        return jsonify({'error': 'Missing student name'}), 400
    # 验证会话
    if session.get('student_name') != student:
        return jsonify({'error': 'Unauthorized'}), 401
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    # 检查学生是否存在
    c.execute('SELECT 1 FROM students WHERE student_name = ?', (student,))
    if not c.fetchone():
        conn.close()
        return jsonify({'error': 'Student not found'}), 404
    # 获取所有预置课程
    c.execute('SELECT start_week, end_week, week_type, weekday, start_period, end_period FROM preset_courses')
    preset_rows = c.fetchall()
    # 为当前学生插入这些课程
    for row in preset_rows:
        c.execute('''INSERT INTO courses 
                     (student_name, start_week, end_week, week_type, weekday, start_period, end_period)
                     VALUES (?,?,?,?,?,?,?)''',
                  (student, row[0], row[1], row[2], row[3], row[4], row[5]))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok', 'count': len(preset_rows)})

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
    backup_db(f"delete_course_{course_id}")
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('DELETE FROM courses WHERE id = ?', (course_id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

@app.route('/api/admin/student', methods=['DELETE'])
def delete_student():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    student_name = request.args.get('name')
    if not student_name:
        return jsonify({'error': 'Missing student name'}), 400
    backup_db(f"delete_student_{student_name}")
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('DELETE FROM courses WHERE student_name = ?', (student_name,))
    c.execute('DELETE FROM students WHERE student_name = ?', (student_name,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

@app.route('/api/admin/student2', methods=['DELETE'])
def delete_student_courses():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    student_name = request.args.get('name')
    if not student_name:
        return jsonify({'error': 'Missing student name'}), 400
    backup_db(f"delete_student_courses_{student_name}")
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('DELETE FROM courses WHERE student_name = ?', (student_name,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})


# 清空所有预置课程
@app.route('/api/preset_courses/clear', methods=['POST'])
def clear_preset_courses():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    backup_db(f"clear_preset_courses")
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('DELETE FROM preset_courses')
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

# ---------- 页面路由：备份还原 ----------
@app.route('/backup_restore')
def backup_restore():
    return render_template('backup_restore.html')
# ---------- API：数据库备份与还原 ----------
@app.route('/api/backup/list', methods=['GET'])
def list_backups():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        files = os.listdir('backup')
        backup_files = [f for f in files if f.endswith('.db') and f.startswith('database_backup_')]
        backup_files.sort(reverse=True)  # 最新的在前
        return jsonify(backup_files)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/backup/create', methods=['POST'])
def create_backup():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        backup_db('manual')  # 使用已有函数
        return jsonify({'status': 'ok', 'message': '备份创建成功'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/backup/restore', methods=['POST'])
def restore_backup():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.json
    filename = data.get('filename')
    if not filename:
        return jsonify({'error': 'Missing filename'}), 400
    
    # 安全校验：防止路径遍历
    if '..' in filename or '/' in filename or '\\' in filename:
        return jsonify({'error': 'Invalid filename'}), 400
    
    backup_path = os.path.join('backup', filename)
    if not os.path.exists(backup_path):
        return jsonify({'error': 'Backup file not found'}), 404
    
    try:
        # 在还原前先自动备份当前数据库（以防万一）
        backup_db('before_restore')
        # 复制备份文件到当前数据库
        copy_file(backup_path, 'database.db')
        return jsonify({'status': 'ok', 'message': '还原成功'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/backup/<filename>', methods=['DELETE'])
def delete_backup(filename):
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    if '..' in filename or '/' in filename or '\\' in filename:
        return jsonify({'error': 'Invalid filename'}), 400
    
    backup_path = os.path.join('backup', filename)
    if not os.path.exists(backup_path):
        return jsonify({'error': 'Backup file not found'}), 404
    
    try:
        os.remove(backup_path)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
# ---------- API：学生密码管理 ----------
@app.route('/api/student/check_auth', methods=['GET'])
def check_student_auth():
    name = request.args.get('name')
    if not name:
        return jsonify({'error': 'Missing name'}), 400
    authenticated = session.get('student_name') == name
    return jsonify({'authenticated': authenticated})

@app.route('/api/student/login', methods=['POST'])
def student_login():
    data = request.json
    name = data.get('name')
    password = data.get('password')
    if not name or not password:
        return jsonify({'error': 'Missing name or password'}), 400
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT password_hash FROM students WHERE student_name = ?', (name,))
    row = c.fetchone()
    conn.close()
    if row and row[0] and check_password_hash(row[0], password):
        session['student_name'] = name
        return jsonify({'status': 'ok'})
    else:
        return jsonify({'error': 'Invalid password or user not found'}), 401

@app.route('/api/student/set_password', methods=['POST'])
def set_student_password():
    data = request.json
    name = data.get('name')
    new_password = data.get('new_password')
    old_password = data.get('old_password')  # 如果已有密码则必须提供
    if not name or not new_password:
        return jsonify({'error': 'Missing name or new password'}), 400
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT password_hash FROM students WHERE student_name = ?', (name,))
    row = c.fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'Student not found'}), 404
    current_hash = row[0]
    if current_hash:
        # 已有密码，验证旧密码
        if not old_password or not check_password_hash(current_hash, old_password):
            conn.close()
            return jsonify({'error': 'Old password is incorrect'}), 401
    # 设置新密码
    new_hash = generate_password_hash(new_password)
    c.execute('UPDATE students SET password_hash = ? WHERE student_name = ?', (new_hash, name))
    conn.commit()
    conn.close()
    # 自动登录
    session['student_name'] = name
    return jsonify({'status': 'ok'})

@app.route('/api/student/logout', methods=['POST'])
def student_logout():
    session.pop('student_name', None)
    return jsonify({'status': 'ok'})

@app.route('/api/admin/reset_password', methods=['POST'])
def admin_reset_password():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.json
    student_name = data.get('name')
    if not student_name:
        return jsonify({'error': 'Missing student name'}), 400
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    # 检查学生是否存在
    c.execute('SELECT 1 FROM students WHERE student_name = ?', (student_name,))
    if not c.fetchone():
        conn.close()
        return jsonify({'error': 'Student not found'}), 404
    # 将密码哈希置为NULL
    c.execute('UPDATE students SET password_hash = NULL WHERE student_name = ?', (student_name,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=12345, debug=True)
