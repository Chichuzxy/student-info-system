# -*- coding: utf-8 -*-
"""图形界面版：Tkinter 实现，左边学生列表，右边表单，下方成绩表。

运行：python gui.py

原课程项目的 GUI 版依赖 MySQL，连接不稳时界面会卡住或报错。
这一版把数据层换成 SQLite，并且所有数据库操作都包在 try 里，
出错只弹提示，不会让窗口卡死。
"""

import tkinter as tk
from tkinter import ttk, messagebox

from service import StudentService, ValidationError


class App(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("学生信息管理系统")
        self.geometry("1080x680")
        self.minsize(900, 560)

        self.svc = StudentService()
        self.current_student = None

        self._build_ui()
        self.refresh_students()

    # ==================== 界面搭建 ====================

    def _build_ui(self):
        top = ttk.Frame(self, padding=(10, 8))
        top.pack(fill="x")
        ttk.Label(top, text="关键字：").pack(side="left")
        self.search_var = tk.StringVar()
        entry = ttk.Entry(top, textvariable=self.search_var, width=24)
        entry.pack(side="left", padx=(0, 6))
        entry.bind("<Return>", lambda e: self.refresh_students())
        ttk.Button(top, text="搜索", command=self.refresh_students).pack(side="left")
        ttk.Button(top, text="显示全部", command=self._clear_search).pack(side="left", padx=6)

        body = ttk.Frame(self, padding=(10, 0))
        body.pack(fill="both", expand=True)

        # 左：学生列表
        left = ttk.LabelFrame(body, text="学生列表", padding=6)
        left.pack(side="left", fill="both", expand=True)

        cols = ("student_id", "name", "gender", "class_name", "major")
        self.tree = ttk.Treeview(left, columns=cols, show="headings", height=14)
        for col, title, width in zip(cols, ["学号", "姓名", "性别", "班级", "专业"],
                                     [110, 90, 60, 140, 160]):
            self.tree.heading(col, text=title)
            self.tree.column(col, width=width, anchor="w")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select_student)

        # 右：表单
        right = ttk.LabelFrame(body, text="学生信息", padding=10)
        right.pack(side="left", fill="y", padx=(10, 0), ipadx=6)

        self.form = {}
        self.entries = {}
        fields = [("student_id", "学号"), ("name", "姓名"), ("gender", "性别"),
                  ("class_name", "班级"), ("major", "专业"), ("phone", "电话")]
        for i, (key, label) in enumerate(fields):
            ttk.Label(right, text=label).grid(row=i, column=0, sticky="e", pady=4, padx=(0, 6))
            var = tk.StringVar()
            state = "readonly" if key == "student_id" else "normal"
            entry = ttk.Entry(right, textvariable=var, width=24, state=state)
            entry.grid(row=i, column=1, sticky="w", pady=4)
            self.form[key] = var
            self.entries[key] = entry

        btns = ttk.Frame(right)
        btns.grid(row=len(fields), column=0, columnspan=2, pady=(12, 0))
        ttk.Button(btns, text="新增", command=self.add_student).pack(side="left", padx=3)
        ttk.Button(btns, text="保存修改", command=self.save_student).pack(side="left", padx=3)
        ttk.Button(btns, text="删除", command=self.delete_student).pack(side="left", padx=3)
        ttk.Button(btns, text="清空表单", command=self.clear_form).pack(side="left", padx=3)

        # 下：成绩
        bottom = ttk.LabelFrame(self, text="成绩（选中学生后显示）", padding=6)
        bottom.pack(fill="both", expand=True, padx=10, pady=(8, 6))

        score_cols = ("id", "course_name", "course_type", "regular_score",
                      "final_score", "total", "semester")
        self.score_tree = ttk.Treeview(bottom, columns=score_cols, show="headings", height=8)
        for col, title, width in zip(score_cols,
                                     ["编号", "课程", "类型", "平时", "期末", "加权总分", "学期"],
                                     [60, 200, 70, 70, 70, 90, 120]):
            self.score_tree.heading(col, text=title)
            self.score_tree.column(col, width=width, anchor="center")
        self.score_tree.pack(fill="both", expand=True)

        bar = ttk.Frame(bottom)
        bar.pack(fill="x", pady=(6, 0))
        ttk.Button(bar, text="录入成绩", command=self.add_score).pack(side="left")
        ttk.Button(bar, text="删除成绩", command=self.delete_score).pack(side="left", padx=6)
        ttk.Button(bar, text="成绩单", command=self.show_transcript).pack(side="left")
        ttk.Button(bar, text="班级排名", command=self.show_rank).pack(side="left", padx=6)

        self.status = tk.StringVar(value="就绪")
        ttk.Label(self, textvariable=self.status, anchor="w",
                  relief="sunken", padding=(8, 4)).pack(fill="x", side="bottom")

    # ==================== 学生 ====================

    def _clear_search(self):
        self.search_var.set("")
        self.refresh_students()

    def refresh_students(self):
        try:
            keyword = self.search_var.get().strip()
            rows = self.svc.list_students(keyword or None)
        except Exception as e:
            self._error(e)
            return
        self.tree.delete(*self.tree.get_children())
        for r in rows:
            self.tree.insert("", "end", iid=r["student_id"],
                             values=(r["student_id"], r["name"], r["gender"] or "",
                                     r["class_name"] or "", r["major"] or ""))
        self.status.set(f"共 {len(rows)} 条记录")

    def _on_select_student(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        sid = sel[0]
        try:
            row = self.svc.get_student(sid)
        except Exception as e:
            self._error(e)
            return
        if not row:
            return
        self.current_student = sid
        self.form["student_id"].set(row["student_id"])
        self.form["name"].set(row["name"] or "")
        self.form["gender"].set(row["gender"] or "")
        self.form["class_name"].set(row["class_name"] or "")
        self.form["major"].set(row["major"] or "")
        self.form["phone"].set(row["phone"] or "")
        self.refresh_scores()

    def clear_form(self):
        self.current_student = None
        for key, var in self.form.items():
            var.set("")
        self.entries["student_id"].configure(state="normal")
        self.score_tree.delete(*self.score_tree.get_children())
        self.tree.selection_remove(*self.tree.selection())
        self.status.set("表单已清空，可新增学生")

    def add_student(self):
        sid = self.form["student_id"].get().strip()
        name = self.form["name"].get().strip()
        try:
            self.svc.add_student(sid, name,
                                 gender=self.form["gender"].get().strip() or None,
                                 class_name=self.form["class_name"].get().strip() or None,
                                 major=self.form["major"].get().strip() or None,
                                 phone=self.form["phone"].get().strip() or None)
            self.refresh_students()
            self.status.set(f"已新增：{sid} {name}")
            self.clear_form()
        except ValidationError as e:
            messagebox.showwarning("无法新增", str(e))
        except Exception as e:
            self._error(e)

    def save_student(self):
        if not self.current_student:
            messagebox.showinfo("提示", "请先在左侧选中一个学生")
            return
        try:
            self.svc.update_student(
                self.current_student,
                name=self.form["name"].get().strip(),
                gender=self.form["gender"].get().strip() or None,
                class_name=self.form["class_name"].get().strip() or None,
                major=self.form["major"].get().strip() or None,
                phone=self.form["phone"].get().strip() or None)
            self.refresh_students()
            self.status.set(f"已保存：{self.current_student}")
        except ValidationError as e:
            messagebox.showwarning("无法保存", str(e))
        except Exception as e:
            self._error(e)

    def delete_student(self):
        if not self.current_student:
            messagebox.showinfo("提示", "请先在左侧选中一个学生")
            return
        n = self.svc.count_scores(self.current_student)
        tip = f"\n\n该学生还有 {n} 条成绩记录，会一起删除。" if n else ""
        if not messagebox.askyesno("确认删除", f"确定删除 {self.current_student}？{tip}"):
            return
        try:
            removed = self.svc.delete_student(self.current_student)
            self.refresh_students()
            self.clear_form()
            self.status.set(f"已删除学生，连带删除成绩 {removed} 条")
        except ValidationError as e:
            messagebox.showwarning("无法删除", str(e))
        except Exception as e:
            self._error(e)

    # ==================== 成绩 ====================

    def refresh_scores(self):
        self.score_tree.delete(*self.score_tree.get_children())
        if not self.current_student:
            return
        try:
            rows = self.svc.get_score_rows(self.current_student)
        except Exception as e:
            self._error(e)
            return
        from service import calc_total
        for r in rows:
            total = calc_total(r["course_type"], r["regular_score"], r["final_score"])
            self.score_tree.insert("", "end", iid=str(r["id"]),
                                   values=(r["id"], r["course_name"], r["course_type"],
                                           f"{r['regular_score']:.1f}", f"{r['final_score']:.1f}",
                                           f"{total:.2f}", r["semester"]))

    def add_score(self):
        if not self.current_student:
            messagebox.showinfo("提示", "请先在左侧选中一个学生")
            return
        ScoreDialog(self, self.svc, self.current_student, self.refresh_scores)

    def delete_score(self):
        sel = self.score_tree.selection()
        if not sel:
            messagebox.showinfo("提示", "请先在成绩表里选一条记录")
            return
        if not messagebox.askyesno("确认删除", "确定删除这条成绩记录？"):
            return
        try:
            self.svc.delete_score(int(sel[0]))
            self.refresh_scores()
            self.status.set("成绩记录已删除")
        except Exception as e:
            self._error(e)

    # ==================== 统计 ====================

    def show_transcript(self):
        if not self.current_student:
            messagebox.showinfo("提示", "请先在左侧选中一个学生")
            return
        try:
            data = self.svc.student_summary(self.current_student)
        except Exception as e:
            self._error(e)
            return
        st = data["student"]
        lines = [f"{st['student_id']}  {st['name']}  {st['class_name'] or ''}", ""]
        if data["count"] == 0:
            lines.append("暂无成绩")
        else:
            from service import calc_total
            for r in data["scores"]:
                total = calc_total(r["course_type"], r["regular_score"], r["final_score"])
                lines.append(f"{r['course_name']}　{r['semester']}　加权 {total:.2f}")
            lines += ["", f"加权总分：{data['total']}",
                      f"平均分：{data['average']}", f"科目数：{data['count']}"]
        TextDialog(self, "成绩单", "\n".join(lines))

    def show_rank(self):
        try:
            rows = self.svc.class_rank()
        except Exception as e:
            self._error(e)
            return
        if not rows:
            messagebox.showinfo("提示", "还没有成绩数据")
            return
        lines = [f"{i}. {r['student_id']}　加权总分 {r['total']:.2f}"
                 for i, r in enumerate(rows, 1)]
        TextDialog(self, "班级排名", "\n".join(lines))

    # ==================== 工具 ====================

    def _error(self, exc):
        self.status.set(f"操作失败：{exc}")
        messagebox.showerror("操作失败", f"{type(exc).__name__}: {exc}")


class ScoreDialog(tk.Toplevel):
    """录入成绩的小窗口。"""

    def __init__(self, master, svc, student_id, on_done):
        super().__init__(master)
        self.title(f"录入成绩 - {student_id}")
        self.geometry("360x300")
        self.resizable(False, False)
        self.svc = svc
        self.student_id = student_id
        self.on_done = on_done

        self.vars = {}
        rows = [("course_name", "课程名", ""), ("course_type", "类型 exam/test", "exam"),
                ("regular_score", "平时成绩", ""), ("final_score", "期末成绩", ""),
                ("semester", "学期", "2025-2026-1")]
        for i, (key, label, default) in enumerate(rows):
            ttk.Label(self, text=label).grid(row=i, column=0, sticky="e", padx=8, pady=8)
            var = tk.StringVar(value=default)
            ttk.Entry(self, textvariable=var, width=20).grid(row=i, column=1, pady=8)
            self.vars[key] = var

        ttk.Label(self, text="考试课：平时40% + 期末60%\n考查课：平时60% + 期末40%",
                  foreground="#777").grid(row=len(rows), column=0, columnspan=2, pady=(0, 8))
        ttk.Button(self, text="保存", command=self.save).grid(row=len(rows) + 1, column=0,
                                                              columnspan=2, pady=6)

    def save(self):
        try:
            total = self.svc.add_score(
                self.student_id,
                self.vars["course_name"].get().strip(),
                self.vars["course_type"].get().strip().lower(),
                float(self.vars["regular_score"].get()),
                float(self.vars["final_score"].get()),
                self.vars["semester"].get().strip())
            messagebox.showinfo("已保存", f"加权总分 {total}")
            self.on_done()
            self.destroy()
        except ValidationError as e:
            messagebox.showwarning("无法保存", str(e))
        except ValueError:
            messagebox.showwarning("无法保存", "平时成绩和期末成绩要填数字")
        except Exception as e:
            messagebox.showerror("操作失败", f"{type(e).__name__}: {e}")


class TextDialog(tk.Toplevel):
    """只读文本窗口，用于成绩单和排名。"""

    def __init__(self, master, title, content):
        super().__init__(master)
        self.title(title)
        self.geometry("420x420")
        text = tk.Text(self, wrap="word", padx=12, pady=12)
        text.insert("1.0", content)
        text.configure(state="disabled")
        text.pack(fill="both", expand=True)


if __name__ == "__main__":
    App().mainloop()
