# -*- coding: utf-8 -*-
"""自测用例（标准库 unittest，零外部依赖）。

覆盖：加权规则、输入校验、重复约束、级联删除、统计、排名、字段白名单。
运行：python tests.py
"""

import unittest

from db import Database
from service import StudentService, ValidationError, calc_total


class TestCalcTotal(unittest.TestCase):

    def test_exam_weight_40_60(self):
        self.assertEqual(calc_total("exam", 80, 90), 86.0)

    def test_test_weight_60_40(self):
        self.assertEqual(calc_total("test", 80, 90), 84.0)

    def test_rounds_to_two_decimals(self):
        self.assertEqual(calc_total("exam", 83, 91), 87.8)

    def test_invalid_course_type(self):
        with self.assertRaises(ValidationError):
            calc_total("final", 80, 90)


class ServiceTestBase(unittest.TestCase):

    def setUp(self):
        self.db = Database(":memory:")
        self.svc = StudentService(self.db)
        self.svc.add_student("2025001", "张三", gender="男", class_name="24区块链2", major="区块链技术应用")
        self.svc.add_student("2025002", "李四", gender="女", class_name="24区块链2", major="区块链技术应用")

    def tearDown(self):
        self.db.close()


class TestStudent(ServiceTestBase):

    def test_add_and_get(self):
        s = self.svc.get_student("2025001")
        self.assertEqual(s["name"], "张三")
        self.assertEqual(s["class_name"], "24区块链2")

    def test_duplicate_student_id_rejected(self):
        with self.assertRaises(ValidationError):
            self.svc.add_student("2025001", "王五")

    def test_blank_student_id_rejected(self):
        with self.assertRaises(ValidationError):
            self.svc.add_student("   ", "王五")

    def test_blank_name_rejected(self):
        with self.assertRaises(ValidationError):
            self.svc.add_student("2025003", "  ")

    def test_search_by_name(self):
        self.assertEqual(len(self.svc.list_students("张")), 1)

    def test_search_by_class(self):
        self.assertEqual(len(self.svc.list_students("24区块链2")), 2)

    def test_search_no_match(self):
        self.assertEqual(len(self.svc.list_students("不存在的班级")), 0)

    def test_update_name(self):
        self.svc.update_student("2025001", name="张三丰")
        self.assertEqual(self.svc.get_student("2025001")["name"], "张三丰")

    def test_update_rejects_blank_name(self):
        with self.assertRaises(ValidationError):
            self.svc.update_student("2025001", name="")

    def test_update_ignores_unknown_field(self):
        # 不在白名单里的字段要被静默过滤，不能拼进 SQL
        self.svc.update_student("2025001", name="张三封", not_a_column="x")
        row = self.svc.get_student("2025001")
        self.assertIsNotNone(row)
        self.assertEqual(row["name"], "张三封")


class TestScore(ServiceTestBase):

    def test_add_score_returns_weighted_total(self):
        total = self.svc.add_score("2025001", "Java程序设计", "exam", 80, 90, "2025-2026-1")
        self.assertEqual(total, 86.0)

    def test_score_saved(self):
        self.svc.add_score("2025001", "Java程序设计", "exam", 80, 90, "2025-2026-1")
        rows = self.svc.list_scores("2025001")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["course_name"], "Java程序设计")

    def test_score_for_missing_student_rejected(self):
        with self.assertRaises(ValidationError):
            self.svc.add_score("9999999", "Java程序设计", "exam", 80, 90, "2025-2026-1")

    def test_score_out_of_range_rejected(self):
        with self.assertRaises(ValidationError):
            self.svc.add_score("2025001", "Java程序设计", "exam", 101, 90, "2025-2026-1")

    def test_score_negative_rejected(self):
        with self.assertRaises(ValidationError):
            self.svc.add_score("2025001", "Java程序设计", "exam", -1, 90, "2025-2026-1")

    def test_score_non_number_rejected(self):
        with self.assertRaises(ValidationError):
            self.svc.add_score("2025001", "Java程序设计", "exam", "八十", 90, "2025-2026-1")

    def test_duplicate_course_same_semester_rejected(self):
        self.svc.add_score("2025001", "Java程序设计", "exam", 80, 90, "2025-2026-1")
        with self.assertRaises(ValidationError):
            self.svc.add_score("2025001", "Java程序设计", "exam", 70, 80, "2025-2026-1")

    def test_same_course_other_semester_allowed(self):
        self.svc.add_score("2025001", "Java程序设计", "exam", 80, 90, "2025-2026-1")
        self.svc.add_score("2025001", "Java程序设计", "exam", 85, 88, "2025-2026-2")
        self.assertEqual(len(self.svc.list_scores("2025001")), 2)

    def test_update_final_score_recalculates_total(self):
        self.svc.add_score("2025001", "Java程序设计", "exam", 80, 90, "2025-2026-1")
        score_id = self.svc.list_scores("2025001")[0]["id"]
        new_total = self.svc.update_score(score_id, final_score=100)
        self.assertEqual(new_total, 92.0)

    def test_delete_score(self):
        self.svc.add_score("2025001", "Java程序设计", "exam", 80, 90, "2025-2026-1")
        score_id = self.svc.list_scores("2025001")[0]["id"]
        self.svc.delete_score(score_id)
        self.assertEqual(len(self.svc.list_scores("2025001")), 0)

    def test_delete_missing_score_rejected(self):
        with self.assertRaises(ValidationError):
            self.svc.delete_score(999)


class TestCascadeAndStats(ServiceTestBase):

    def test_delete_student_cascades_scores(self):
        self.svc.add_score("2025001", "Java程序设计", "exam", 80, 90, "2025-2026-1")
        self.svc.add_score("2025001", "数据库", "test", 85, 88, "2025-2026-1")
        removed = self.svc.delete_student("2025001")
        self.assertEqual(removed, 2)
        self.assertIsNone(self.svc.get_student("2025001"))
        self.assertEqual(len(self.svc.list_scores("2025001")), 0)

    def test_delete_missing_student_rejected(self):
        with self.assertRaises(ValidationError):
            self.svc.delete_student("8888888")

    def test_student_summary_total_and_average(self):
        self.svc.add_score("2025001", "Java程序设计", "exam", 80, 90, "2025-2026-1")   # 86.0
        self.svc.add_score("2025001", "数据库", "test", 85, 88, "2025-2026-1")         # 86.2
        s = self.svc.student_summary("2025001")
        self.assertEqual(s["count"], 2)
        self.assertEqual(s["total"], 172.2)
        self.assertEqual(s["average"], 86.1)

    def test_student_summary_without_scores(self):
        s = self.svc.student_summary("2025002")
        self.assertEqual(s["count"], 0)
        self.assertEqual(s["total"], 0.0)
        self.assertEqual(s["average"], 0.0)

    def test_class_rank_order(self):
        self.svc.add_score("2025001", "Java程序设计", "exam", 90, 95, "2025-2026-1")  # 93.0
        self.svc.add_score("2025002", "Java程序设计", "exam", 70, 75, "2025-2026-1")  # 73.0
        rank = self.svc.class_rank()
        self.assertEqual(rank[0]["student_id"], "2025001")
        self.assertEqual(rank[1]["student_id"], "2025002")

    def test_chinese_text_roundtrip(self):
        self.svc.add_score("2025001", "区块链技术及应用", "exam", 88, 92, "2025-2026-2")
        row = self.svc.list_scores("2025001")[0]
        self.assertEqual(row["course_name"], "区块链技术及应用")
        self.assertEqual(row["student_name"], "张三")


if __name__ == "__main__":
    unittest.main(verbosity=2)
