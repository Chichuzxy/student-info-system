# 学生信息管理系统（Python）

Python 应用技术课程的综合作业。原版是 MySQL + pymysql，命令行版能正常跑，
图形界面版在数据库连接不稳定时会卡住或报错。本版做了重构：

- 数据层从 MySQL 换成 **SQLite**：单文件、零依赖，不会出现连接超时、掉线、忘记开服务
- 所有数据库操作都包了异常边界，出错只弹提示，不会让窗口卡死
- 拆成数据层 / 业务层 / 命令行 / 图形界面四层，业务层不碰输入输出，可以直接跑单元测试
- 补了 **31 条单元测试**，覆盖加权规则、输入校验、重复约束、级联删除、统计与排名

## 功能

- 学生管理：新增、查询（学号/姓名/班级/专业模糊搜索）、修改、删除（级联删除其成绩）
- 成绩管理：录入、修改（自动重算加权总分）、删除、按学生/课程/学期查询
- 统计：学生成绩单（各科加权分 + 总分 + 平均分）、班级排名
- 两种界面：命令行菜单版（cli.py）和图形界面版（gui.py）

## 加权规则

| 课程类型 | 平时 | 期末 |
|---|---|---|
| 考试课 exam | 40% | 60% |
| 考查课 test | 60% | 40% |

规则写在 `service.py` 的 `WEIGHTS` 字典里，改权重只改这一处。

## 表结构

```
students  student_id(PK), name, gender, birth_date, phone,
          dormitory, campus, college, major, class_name

scores    id(PK), student_id(FK → students, ON DELETE CASCADE),
          course_name, course_type(exam/test), regular_score,
          final_score, semester
```

外键带级联删除：删学生时他的成绩一起删。SQLite 的外键约束默认关闭，
`db.py` 里显式执行 `PRAGMA foreign_keys = ON` 才生效——这一点踩过坑。

## 目录

```
db.py         数据访问层：连接、建表、查询封装
service.py    业务层：校验、加权计算、级联删除、统计
cli.py        命令行界面
gui.py        图形界面（Tkinter）
tests.py      31 条单元测试
student.db    运行后自动生成
```

## 运行

需要 Python 3.8+，只用标准库，不需要 pip install。

```bash
python tests.py     # 跑 31 条测试
python cli.py       # 命令行版
python gui.py       # 图形界面版
```

Windows 下也可以直接双击 `run-tests.bat` / `run-cli.bat` / `run-gui.bat`。

## 测试结果

```
Ran 31 tests in 0.010s

OK
```

覆盖内容：
- 加权规则：考试课 40/60、考查课 60/40、两位小数四舍五入、非法课程类型报错
- 学生：增查、重复学号、空学号、空姓名、按姓名/班级搜索、修改、修改时空名被拒、未知字段被过滤
- 成绩：加权返回值、成绩越界（101 / -1）、非数字输入、学号不存在、同学期重复课程、
  跨学期同名课程允许、改期末后总分重算、删除不存在的记录
- 级联与统计：删学生连带删成绩、成绩单总分与平均分、无成绩学生、排名顺序、中文往返不乱码

## 相对原版的改动

1. **MySQL → SQLite**：原版依赖本地 MySQL 服务，GUI 版连接不稳定时会卡界面。
   换成 SQLite 后没有网络连接、没有服务依赖，也方便换机器复现。
2. **一个类 809 行 → 四层拆分**：原版 `UserInterface` 类里同时做菜单、输入校验、
   SQL 拼接和打印。现在校验在 service、SQL 在 db、界面在 cli/gui。
3. **补测试**：原版没有任何自动化测试，本版 31 条，全部可复现。

## 已知限制

- 单用户本地程序，没有并发控制，不适合多个人同时写
- 没有导出 Excel/PDF 的功能（原版也没有）
- GUI 只做了基础表单，没有做批量导入
