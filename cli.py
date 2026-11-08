# -*- coding: utf-8 -*-
"""命令行版：菜单驱动的学生信息与成绩管理。

运行：python cli.py
"""

import sys

from service import StudentService, ValidationError

MENU = """
================ 学生信息管理系统 ================
  1. 学生管理
  2. 成绩管理
  3. 统计与排名
  0. 退出
=================================================="""


def ask(prompt, default=None):
    value = input(prompt).strip()
    if not value and default is not None:
        return default
    return value


def pause():
    input("\n回车继续...")


class App:

    def __init__(self):
        self.svc = StudentService()

    def run(self):
        while True:
            print(MENU)
            choice = ask("请选择：")
            try:
                if choice == "1":
                    self.student_menu()
                elif choice == "2":
                    self.score_menu()
                elif choice == "3":
                    self.stat_menu()
                elif choice == "0":
                    print("已退出。")
                    return
                else:
                    print("无效选项，请重新输入。")
            except ValidationError as e:
                print(f"[输入有误] {e}")
            except KeyboardInterrupt:
                print("\n已退出。")
                return
            except Exception as e:                      # 兜底，避免直接崩栈
                print(f"[操作失败] {type(e).__name__}: {e}")

    # ---------------- 学生 ----------------

    def student_menu(self):
        while True:
            print("""
--- 学生管理 ---
  1. 新增学生
  2. 查询学生
  3. 修改学生
  4. 删除学生
  5. 全部学生
  0. 返回""")
            choice = ask("请选择：")
            if choice == "1":
                self.add_student()
            elif choice == "2":
                self.query_student()
            elif choice == "3":
                self.modify_student()
            elif choice == "4":
                self.delete_student()
            elif choice == "5":
                self.list_students()
            elif choice == "0":
                return
            else:
                print("无效选项。")

    def add_student(self):
        print("\n新增学生（学号、姓名为必填）")
        sid = ask("学号：")
        name = ask("姓名：")
        gender = ask("性别（男/女，可空）：")
        cls = ask("班级（可空）：")
        major = ask("专业（可空）：")
        phone = ask("电话（可空）：")
        self.svc.add_student(sid, name, gender=gender or None, class_name=cls or None,
                             major=major or None, phone=phone or None)
        print(f"已添加：{sid} {name}")
        pause()

    def query_student(self):
        kw = ask("\n输入学号/姓名/班级关键字（直接回车看全部）：")
        rows = self.svc.list_students(kw or None)
        if not rows:
            print("没有匹配的学生。")
        else:
            self._print_students(rows)
        pause()

    def list_students(self):
        rows = self.svc.list_students()
        if not rows:
            print("\n还没有学生记录。")
        else:
            self._print_students(rows)
        pause()

    def modify_student(self):
        sid = ask("\n要修改的学号：")
        row = self.svc.get_student(sid)
        if not row:
            print("学号不存在。")
            pause()
            return
        print(f"当前：{row['student_id']} {row['name']} {row['class_name'] or ''}")
        print("留空表示不改。")
        fields = {}
        for key, label in [("name", "姓名"), ("gender", "性别"), ("class_name", "班级"),
                           ("major", "专业"), ("phone", "电话")]:
            v = ask(f"{label}：")
            if v:
                fields[key] = v
        if fields:
            self.svc.update_student(sid, **fields)
            print("已修改。")
        else:
            print("没有改动。")
        pause()

    def delete_student(self):
        sid = ask("\n要删除的学号：")
        row = self.svc.get_student(sid)
        if not row:
            print("学号不存在。")
            pause()
            return
        n = self.svc.count_scores(sid)
        tip = f"（会同时删除 {n} 条成绩记录）" if n else ""
        if ask(f"确认删除 {row['name']} {tip}？输入 y 确认：").lower() != "y":
            print("已取消。")
            pause()
            return
        removed = self.svc.delete_student(sid)
        print(f"已删除，连带删除成绩 {removed} 条。")
        pause()

    # ---------------- 成绩 ----------------

    def score_menu(self):
        while True:
            print("""
--- 成绩管理 ---
  1. 录入成绩
  2. 查询成绩
  3. 修改成绩
  4. 删除成绩
  0. 返回""")
            choice = ask("请选择：")
            if choice == "1":
                self.add_score()
            elif choice == "2":
                self.query_scores()
            elif choice == "3":
                self.modify_score()
            elif choice == "4":
                self.delete_score()
            elif choice == "0":
                return
            else:
                print("无效选项。")

    def add_score(self):
        print("\n录入成绩（考试课：平时40%+期末60%；考查课：平时60%+期末40%）")
        sid = ask("学号：")
        course = ask("课程名：")
        ctype = ask("课程类型 exam=考试 / test=考查：").lower()
        regular = float(ask("平时成绩："))
        final = float(ask("期末成绩："))
        semester = ask("学期（如 2025-2026-1）：")
        total = self.svc.add_score(sid, course, ctype, regular, final, semester)
        print(f"已录入，加权总分 {total}")
        pause()

    def query_scores(self):
        sid = ask("\n学号（直接回车查全部）：")
        course = ask("课程名关键字（可空）：")
        rows = self.svc.list_scores(sid or None, course or None)
        if not rows:
            print("没有成绩记录。")
        else:
            print(f"\n{'学号':<10}{'姓名':<8}{'课程':<20}{'类型':<6}{'平时':>6}{'期末':>6}{'总分':>8}  {'学期'}")
            print("-" * 82)
            for r in rows:
                total = self._total(r)
                print(f"{r['student_id']:<10}{r['student_name']:<8}{r['course_name']:<20}"
                      f"{r['course_type']:<6}{r['regular_score']:>6.1f}{r['final_score']:>6.1f}"
                      f"{total:>8.2f}  {r['semester']}")
        pause()

    def modify_score(self):
        sid = ask("\n学号：")
        rows = self.svc.list_scores(sid)
        if not rows:
            print("该学生没有成绩记录。")
            pause()
            return
        for r in rows:
            print(f"  [{r['id']}] {r['course_name']} {r['semester']} "
                  f"平时{r['regular_score']} 期末{r['final_score']} 总分{self._total(r)}")
        score_id = int(ask("要修改的记录编号："))
        regular = ask("新平时成绩（留空不改）：")
        final = ask("新期末成绩（留空不改）：")
        total = self.svc.update_score(
            score_id,
            regular_score=float(regular) if regular else None,
            final_score=float(final) if final else None)
        print(f"已修改，新加权总分 {total}")
        pause()

    def delete_score(self):
        score_id = int(ask("\n要删除的成绩记录编号："))
        self.svc.delete_score(score_id)
        print("已删除。")
        pause()

    # ---------------- 统计 ----------------

    def stat_menu(self):
        while True:
            print("""
--- 统计与排名 ---
  1. 学生成绩单（含加权总分与平均分）
  2. 班级排名
  0. 返回""")
            choice = ask("请选择：")
            if choice == "1":
                self.transcript()
            elif choice == "2":
                self.rank()
            elif choice == "0":
                return
            else:
                print("无效选项。")

    def transcript(self):
        sid = ask("\n学号：")
        data = self.svc.student_summary(sid)
        st = data["student"]
        print(f"\n{st['student_id']}  {st['name']}  {st['class_name'] or ''}  {st['major'] or ''}")
        if not data["count"]:
            print("（暂无成绩）")
        else:
            print(f"\n{'课程':<20}{'类型':<6}{'平时':>6}{'期末':>6}{'总分':>8}  {'学期'}")
            print("-" * 60)
            for r in data["scores"]:
                print(f"{r['course_name']:<20}{r['course_type']:<6}{r['regular_score']:>6.1f}"
                      f"{r['final_score']:>6.1f}{self._total(r):>8.2f}  {r['semester']}")
            print("-" * 60)
            print(f"加权总分 {data['total']}　平均分 {data['average']}　科目数 {data['count']}")
        pause()

    def rank(self):
        semester = ask("\n学期（直接回车统计全部）：")
        rows = self.svc.class_rank(semester or None)
        if not rows:
            print("没有成绩数据。")
        else:
            print(f"\n{'名次':<6}{'学号':<12}{'加权总分'}")
            print("-" * 32)
            for i, r in enumerate(rows, 1):
                print(f"{i:<6}{r['student_id']:<12}{r['total']:.2f}")
        pause()

    # ---------------- 工具 ----------------

    @staticmethod
    def _total(row):
        from service import calc_total
        return calc_total(row["course_type"], row["regular_score"], row["final_score"])

    @staticmethod
    def _print_students(rows):
        print(f"\n{'学号':<10}{'姓名':<8}{'性别':<5}{'班级':<14}{'专业':<18}{'电话'}")
        print("-" * 74)
        for r in rows:
            print(f"{r['student_id']:<10}{r['name']:<8}{r['gender'] or '':<5}"
                  f"{(r['class_name'] or ''):<14}{(r['major'] or ''):<18}{r['phone'] or ''}")


if __name__ == "__main__":
    try:
        App().run()
    except Exception as e:
        print(f"启动失败：{e}")
        sys.exit(1)
