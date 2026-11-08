# -*- coding: utf-8 -*-
"""SQLite 数据访问层。

原课程项目用的是 MySQL + pymysql，但 MySQL 服务不稳定（连接会掉），
而且换个机器就要重装数据库。这里换成 SQLite：单文件、零依赖、不可能掉线。
表结构沿用原设计（students / scores），字段名和加权规则都没改。
"""

import os
import sqlite3

DEFAULT_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "student.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    student_id TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    gender     TEXT,
    birth_date TEXT,
    phone      TEXT,
    dormitory  TEXT,
    campus     TEXT,
    college    TEXT,
    major      TEXT,
    class_name TEXT
);

CREATE TABLE IF NOT EXISTS scores (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id    TEXT NOT NULL,
    course_name   TEXT NOT NULL,
    course_type   TEXT NOT NULL CHECK (course_type IN ('exam', 'test')),
    regular_score REAL NOT NULL,
    final_score   REAL NOT NULL,
    semester      TEXT NOT NULL,
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_scores_student ON scores(student_id);
CREATE INDEX IF NOT EXISTS idx_scores_course  ON scores(course_name);
"""


class Database:
    """封装连接、建表和事务。用上下文管理器保证异常时回滚。"""

    def __init__(self, path=DEFAULT_DB):
        self.path = path
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        # 外键约束默认是关的，必须显式打开，否则级联删除不生效
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def execute(self, sql, params=()):
        cur = self.conn.execute(sql, params)
        self.conn.commit()
        return cur

    def query(self, sql, params=()):
        return self.conn.execute(sql, params).fetchall()

    def query_one(self, sql, params=()):
        return self.conn.execute(sql, params).fetchone()

    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type:
            self.conn.rollback()
        self.close()
        return False
