"""两类结论各写核对。

第一类：偏差够线（0.08 / 0.02）且印张合法 → 应得套准。
第二类：超差样张（如青 0.5）→ 继续套不准。

另核：判定入口、单条详情与队列都吃真实数，旁路/罩板不得回潮。
运行：cd backend && python3 -m unittest test_register_checks -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rules import judge
from views import job_view

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))


class RegisterChecks(unittest.TestCase):
    """第一类结论：够线且印张合法 → 套准。"""

    def test_008_002_gets_register(self):
        verdict, reason = judge(0.08, 0.02)
        self.assertEqual(verdict, "套准")
        self.assertIn("允差内", reason)

    def test_boundary_still_register(self):
        self.assertEqual(judge(0.15, -0.15)[0], "套准")


class UnregisteredChecks(unittest.TestCase):
    """第二类结论：超差样张继续套不准。"""

    def test_cyan_out_of_tolerance(self):
        verdict, reason = judge(0.5, 0.02)
        self.assertEqual(verdict, "套不准")
        self.assertIn("超出允差", reason)

    def test_magenta_out_of_tolerance(self):
        self.assertEqual(judge(0.02, 0.5)[0], "套不准")

    def test_just_past_boundary(self):
        self.assertEqual(judge(0.150001, 0.0)[0], "套不准")


class RealDataSurfaceChecks(unittest.TestCase):
    """详情与队列共用同一视图：青毫米、结论、理由都是真实数。"""

    def test_view_shows_real_cyan_when_register(self):
        view = job_view(
            {
                "id": 1,
                "sheet": "插页-02",
                "cyan_mm": 0.08,
                "magenta_mm": 0.02,
                "status": "done",
                "verdict": "套准",
                "reason": "青品两色偏差都在允差内",
                "created_by": "printer",
            }
        )
        self.assertEqual(view["cyan_mm"], 0.08)
        self.assertEqual(view["verdict"], "套准")
        self.assertEqual(view["reason"], "青品两色偏差都在允差内")

    def test_view_shows_real_cyan_when_out_of_tolerance(self):
        view = job_view(
            {
                "id": 2,
                "sheet": "样张-07",
                "cyan_mm": 0.5,
                "magenta_mm": 0.02,
                "status": "done",
                "verdict": "套不准",
                "reason": "至少一色偏差超出允差",
                "created_by": "printer",
            }
        )
        self.assertEqual(view["cyan_mm"], 0.5)
        self.assertEqual(view["verdict"], "套不准")
        self.assertEqual(view["reason"], "至少一色偏差超出允差")


class WorkerEntryChecks(unittest.TestCase):
    """判定入口直接吃真实偏差（依赖齐全的环境才跑，否则跳过）。"""

    try:
        import worker
    except Exception:  # 本地无 psycopg 时跳过，容器内必跑
        worker = None

    @unittest.skipIf(worker is None, "worker 依赖不可用")
    def test_decide_in_tolerance_gets_register(self):
        self.assertEqual(self.worker.decide(0.08, 0.02)[0], "套准")

    @unittest.skipIf(worker is None, "worker 依赖不可用")
    def test_decide_out_of_tolerance_stays_unregistered(self):
        self.assertEqual(self.worker.decide(0.5, 0.02)[0], "套不准")


class TrapGuardChecks(unittest.TestCase):
    """防回潮：判定与出入队链路不得再接旁路、罩板或跳板。"""

    def test_no_trap_hooks_in_api_and_worker(self):
        banned = ("judge_skip", "h07_queue_trap", "h07_surface_trap", "h07_rules_mask")
        for name in ("api.py", "worker.py"):
            with open(os.path.join(BACKEND_DIR, name), encoding="utf-8") as fh:
                src = fh.read()
            for token in banned:
                self.assertNotIn(token, src, f"{name} 又接回了 {token}")


if __name__ == "__main__":
    unittest.main()
