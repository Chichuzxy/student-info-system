# -*- coding: utf-8 -*-
"""业务逻辑层：学生与成绩的增删改查、加权总分计算、级联删除。

这一层不碰输入输出，也不碰界面，所以单元测试可以直接调用。
"""

from db import Database


class ValidationError(ValueError):
    """输入不合法的统一异常。"""


# 加权规则（沿用原项目的设定）
# 考试课：平时 40% + 期末 60%
# 考查课：平时 60% + 期末 40%
WEIGHTS = {
    "exam": (0.4, 0.6),
    "test": (0.6, 0.4),
}


def calc_total(course_type, regular, final):
    """按课程类型算加权总分，保留两位小数。"""
    if course_type not in WEIGHTS:
        raise ValidationError(f"课程类型只能是 exam 或 test，收到 {course_type!r}")
    w_regular, w_final = WEIGHTS[course_type]
    return round(regular * w_regular + final * w_final, 2)


def _check_score(value, name):
    if not isinstance(value, (int, float)):
        raise ValidationError(f"{name}必须是数字")
    if not 0 <= value <= 100:
        raise ValidationError(f"{name}必须在 0-100 之间，收到 {value}")
    return float(value)


class StudentService:

    def __init__(self, db=None):
        self.db = db or Database()

    # ---------------- 学生 ----------------

    def add_student(self, student_id, name, gender=None, birth_date=None, phone=None,
                    dormitory=None, campus=None, college=None, major=None, class_name=None):
        if not student_id or not str(student_id).strip():
            raise ValidationError("学号不能为空")
        if not name or not str(name).strip():
            raise ValidationError("姓名不能为空")
        if self.get_student(student_id):
            raise ValidationError(f"学号 {student_id} 已存在")
        self.db.execute(
            """INSERT INTO students
               (student_id, name, gender, birth_date, phone, dormitory, campus, college, major, class_name)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (str(student_id).strip(), name.strip(), gender, birth_date, phone,
             dormitory, campus, college, major, class_name),
        )
        return True

    def get_student(self, student_id):
        return self.db.query_one("SELECT * FROM students WHERE student_id = ?", (student_id,))

    def list_students(self, keyword=None):
        if keyword:
            like = f"%{keyword}%"
            return self.db.query(
                """SELECT * FROM students
                   WHERE student_id LIKE ? OR name LIKE ? OR class_name LIKE ? OR major LIKE ?
                   ORDER BY student_id""", (like, like, like, like))
        return self.db.query("SELECT * FROM students ORDER BY student_id")

    def update_student(self, student_id, **fields):
        allowed = {"name", "gender", "birth_date", "phone", "dormitory",
                   "campus", "college", "major", "class_name"}
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            raise ValidationError("没有可更新的字段")
        if "name" in updates and not str(updates["name"]).strip():
            raise ValidationError("姓名不能为空")
        sets = ", ".join(f"{k} = ?" for k in updates)
        self.db.execute(f"UPDATE students SET {sets} WHERE student_id = ?",
                        (*updates.values(), student_id))
        return True

    def delete_student(self, student_id):
        """删学生，同时级联删掉他的成绩。返回被连带删除的成绩条数。"""
        if not self.get_student(student_id):
            raise ValidationError(f"学号 {student_id} 不存在")
        count = self.count_scores(student_id)
        self.db.execute("DELETE FROM students WHERE student_id = ?", (student_id,))
        return count

    # ---------------- 成绩 ----------------

    def add_score(self, student_id, course_name, course_type, regular_score,
                  final_score, semester):
        if not self.get_student(student_id):
            raise ValidationError(f"学号 {student_id} 不存在，不能录成绩")
        if not course_name or not str(course_name).strip():
            raise ValidationError("课程名不能为空")
        if not semester or not str(semester).strip():
            raise ValidationError("学期不能为空")
        regular = _check_score(regular_score, "平时成绩")
        final = _check_score(final_score, "期末成绩")
        total = calc_total(course_type, regular, final)

        dup = self.db.query_one(
            """SELECT id FROM scores
               WHERE student_id = ? AND course_name = ? AND semester = ?""",
            (student_id, course_name.strip(), semester.strip()))
        if dup:
            raise ValidationError(f"{student_id} 的《{course_name}》在 {semester} 已有成绩记录")

        self.db.execute(
            """INSERT INTO scores
               (student_id, course_name, course_type, regular_score, final_score, semester)
               VALUES (?,?,?,?,?,?)""",
            (student_id, course_name.strip(), course_type, regular, final, semester.strip()))
        return total

    def list_scores(self, student_id=None, course_name=None, semester=None):
        sql = """SELECT s.*, st.name AS student_name
                 FROM scores s JOIN students st ON st.student_id = s.student_id
                 WHERE 1 = 1"""
        params = []
        if student_id:
            sql += " AND s.student_id = ?"
            params.append(student_id)
        if course_name:
            sql += " AND s.course_name LIKE ?"
            params.append(f"%{course_name}%")
        if semester:
            sql += " AND s.semester = ?"
            params.append(semester)
        sql += " ORDER BY s.student_id, s.semester, s.course_name"
        return self.db.query(sql, tuple(params))

    def get_score_rows(self, student_id):
        return self.db.query(
            """SELECT * FROM scores WHERE student_id = ?
               ORDER BY semester, course_name""", (student_id,))

    def count_scores(self, student_id):
        row = self.db.query_one("SELECT COUNT(*) AS n FROM scores WHERE student_id = ?",
                                (student_id,))
        return row["n"]

    def update_score(self, score_id, regular_score=None, final_score=None,
                     course_name=None, semester=None, course_type=None):
        row = self.db.query_one("SELECT * FROM scores WHERE id = ?", (score_id,))
        if not row:
            raise ValidationError(f"成绩记录 {score_id} 不存在")

        course_type = course_type or row["course_type"]
        regular = row["regular_score"] if regular_score is None else _check_score(regular_score, "平时成绩")
        final = row["final_score"] if final_score is None else _check_score(final_score, "期末成绩")
        total = calc_total(course_type, regular, final)

        self.db.execute(
            """UPDATE scores
               SET course_name = ?, course_type = ?, regular_score = ?, final_score = ?, semester = ?
               WHERE id = ?""",
            (course_name or row["course_name"], course_type, regular, final,
             semester or row["semester"], score_id))
        return total

    def delete_score(self, score_id):
        if not self.db.query_one("SELECT id FROM scores WHERE id = ?", (score_id,)):
            raise ValidationError(f"成绩记录 {score_id} 不存在")
        self.db.execute("DELETE FROM scores WHERE id = ?", (score_id,))
        return True

    # ---------------- 统计 ----------------

    def student_summary(self, student_id):
        """一个学生：基本信息 + 各科成绩 + 加权总分 + 平均分。"""
        student = self.get_student(student_id)
        if not student:
            raise ValidationError(f"学号 {student_id} 不存在")
        rows = self.get_score_rows(student_id)
        totals = [calc_total(r["course_type"], r["regular_score"], r["final_score"]) for r in rows]
        return {
            "student": student,
            "scores": rows,
            "total": round(sum(totals), 2) if totals else 0.0,
            "average": round(sum(totals) / len(totals), 2) if totals else 0.0,
            "count": len(rows),
        }

    def class_rank(self, semester=None):
        """按加权总分排名（只统计有成绩的学生）。"""
        sql = """SELECT student_id, SUM(
                     CASE course_type
                       WHEN 'exam' THEN regular_score * 0.4 + final_score * 0.6
                       ELSE regular_score * 0.6 + final_score * 0.4
                     END) AS total
                 FROM scores"""
        params = ()
        if semester:
            sql += " WHERE semester = ?"
            params = (semester,)
        sql += " GROUP BY student_id ORDER BY total DESC"
        return self.db.query(sql, params)
