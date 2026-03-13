# 课程表管理系统 / Course Schedule Management System

[English](#english) | [中文](#chinese)

---

## 中文

### 项目简介
这是一个基于 Flask 和 SQLite 的课程表管理系统，支持多用户课程管理、管理员后台、预置课表、白名单控制、数据库备份还原等功能。学生可以创建个人课程表，管理员可查看所有学生课程并进行管理。

### 主要功能
#### 对外访问页面 (`/`)
- 学生输入姓名加载个人课程，首次使用自动获取预置课程。
- 支持设置密码、登录验证，保护课程数据安全。
- 添加课程时选择起止周、单双周、星期、节次。
- 课程列表按星期和节次自动排序。
- 已登录且无课程时，可一键加载预置课程。
- 移动端自动适配 (`/index_mobile.html`)，移除网格辅助选课，优化触摸操作。

#### 管理后台 (`/admin`)
- 首次访问需设置管理员密码，后续登录验证。
- 查看所有学生的课程列表，支持按姓名、课程详情展示。
- 按周数、星期、节次查询有课学生。
- 删除单个课程或某学生所有课程。
- 重置指定学生的密码（清空密码，下次登录需重新设置）。
- 入口链接至预置课表管理、白名单管理、备份还原。

#### 预置课表管理 (`/preset`)
- 管理员登录后可增删预置课程。
- 预置课程将自动分配给首次使用的学生。
- 列表按星期和节次排序，支持一键清空所有预置课程。

#### 白名单管理 (`/whitelist`)
- 启用/禁用白名单功能。
- 添加/移除白名单人员。
- 白名单外的学生无法加载课程（返回 403 错误）。

#### 数据库备份还原 (`/backup_restore`)
- 创建数据库备份（手动或还原前自动备份）。
- 查看备份文件列表，支持还原、删除。
- 所有操作需管理员登录。

### 技术栈
- 后端：Python Flask, SQLite, Werkzeug (密码哈希)
- 前端：HTML, CSS, JavaScript (原生，无框架)
- 会话管理：Flask session

### 安装与运行
1. 克隆项目或下载源码。
2. 安装依赖：
   ```bash
   pip install flask werkzeug
   ```
3. 运行应用：
   ```bash
   python app.py
   ```
4. 访问地址：
   - 对外页面：`http://127.0.0.1:12345/`
   - 管理后台：`http://127.0.0.1:12345/admin`
   - 预置课表：`http://127.0.0.1:12345/preset`(无法直接访问，需要从/admin进入)
   - 白名单管理：`http://127.0.0.1:12345/whitelist`(无法直接访问，需要从/admin进入)
   - 备份还原：`http://127.0.0.1:12345/backup_restore`(无法直接访问，需要从/admin进入)

首次运行会自动创建 `database.db` 和 `backup` 目录。

### 配置说明
- 修改 `app.secret_key` 为强随机字符串（生产环境必须）。
- 默认监听 `0.0.0.0:12345`，可在 `app.run()` 中调整。

### 注意事项
- 所有操作均需保持 Flask 应用运行。
- 删除课程或重置密码不可逆，请谨慎操作。
- 白名单启用后，只有名单内用户可访问。

---

## English

### Introduction
This is a course schedule management system built with Flask and SQLite. It supports multi-user course management, an admin dashboard, preset courses, whitelist control, database backup and restore. Students can create their personal schedules, and administrators can view and manage all students' courses.

### Features
#### Public Access Page (`/`)
- Students enter their name to load personal courses; first-time users automatically receive preset courses.
- Password protection: set password, login verification to secure course data.
- Add courses with start/end weeks, odd/even weeks, weekday, and period range.
- Course list automatically sorted by weekday and period.
- Logged-in users with no courses can load preset courses with one click.
- Mobile-friendly version (`/index_mobile.html`) with simplified interface (no grid selection, optimized for touch).

#### Admin Dashboard (`/admin`)
- First visit: set admin password; subsequent visits require login.
- View all students' courses in a table.
- Query students with courses by week, weekday(s), and period range.
- Delete a single course or all courses of a student.
- Reset a student's password (clear password hash, forcing them to set a new one on next login).
- Links to Preset Course Management, Whitelist Management, and Backup & Restore.

#### Preset Course Management (`/preset`)
- Admin can add/delete preset courses.
- Preset courses are automatically assigned to first-time students.
- List sorted by weekday and period; supports clearing all preset courses.

#### Whitelist Management (`/whitelist`)
- Enable/disable whitelist feature.
- Add/remove names from whitelist.
- Students not in the whitelist receive a 403 error when loading courses.

#### Database Backup & Restore (`/backup_restore`)
- Create database backups (manual or automatic before restore).
- View list of backup files; restore or delete backups.
- All operations require admin login.

### Tech Stack
- Backend: Python Flask, SQLite, Werkzeug (password hashing)
- Frontend: HTML, CSS, JavaScript (vanilla, no frameworks)
- Session management: Flask session

### Installation & Running
1. Clone the project or download the source code.
2. Install dependencies:
   ```bash
   pip install flask werkzeug
   ```
3. Run the application:
   ```bash
   python app.py
   ```
4. Access URLs:
   - Public page: `http://127.0.0.1:12345/`
   - Admin dashboard: `http://127.0.0.1:12345/admin`
   - Preset courses: `http://127.0.0.1:12345/preset`
   - Whitelist management: `http://127.0.0.1:12345/whitelist`
   - Backup & restore: `http://127.0.0.1:12345/backup_restore`

The first run will automatically create `database.db` and the `backup` directory.

### Configuration
- Change `app.secret_key` to a strong random string (required for production).
- Default host is `0.0.0.0:12345`; modify `app.run()` if needed.

### Notes
- The Flask application must be running for all operations.
- Deleting courses or resetting passwords is irreversible; proceed with caution.
- When whitelist is enabled, only listed users can access the system.

---

## 许可证 / License
MIT License
