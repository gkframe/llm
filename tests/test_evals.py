"""The eval suite: task files are complete, hidden tests pass their reference solutions,
code extraction and blinding work. No network, no model calls."""
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True   # keep evals/ free of __pycache__
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "evals"))

import blind  # noqa: E402
import run  # noqa: E402
import score  # noqa: E402


class Tasks(unittest.TestCase):
    def setUp(self):
        self.tasks = run.load_tasks()

    def test_counts_and_ids(self):
        cats = {}
        for t in self.tasks:
            cats.setdefault(t["category"], []).append(t["id"])
        self.assertEqual({c: len(v) for c, v in cats.items()},
                         {"coding": 12, "creative": 6, "playground": 6, "chat": 12})
        ids = [t["id"] for t in self.tasks]
        self.assertEqual(len(ids), len(set(ids)))

    def test_coding_levels(self):
        levels = sorted(t["level"] for t in self.tasks if t["category"] == "coding")
        self.assertEqual(levels, ["easy"] * 4 + ["hard"] * 4 + ["medium"] * 4)

    def test_fields(self):
        for t in self.tasks:
            if t["category"] == "playground":
                for key in ("system", "prompt", "schema", "check"):
                    self.assertTrue(t.get(key), (t["id"], key))
                self.assertIn("== Now ==", t["prompt"])
            elif t["category"] in ("creative", "chat"):
                self.assertTrue(t.get("prompt") or t.get("messages"), t["id"])
                self.assertTrue(t.get("check"), t["id"])
            else:
                for f in ("test.py", "reference.py"):
                    self.assertTrue(os.path.exists(os.path.join(t["dir"], f)), (t["id"], f))

    def test_request_bodies(self):
        for t in self.tasks:
            body = run.request_body(t, "m")
            self.assertEqual(body["model"], "m")
            if t["category"] == "playground":
                self.assertEqual(body["chat_template_kwargs"], {"enable_thinking": False})
                self.assertEqual(body["thinking_budget_tokens"], 0)
                self.assertEqual(body["response_format"]["json_schema"]["schema"], t["schema"])
            else:
                self.assertNotIn("chat_template_kwargs", body)
                self.assertEqual(body["max_tokens"], 16384)


class HiddenTests(unittest.TestCase):
    def test_references_pass(self):
        for t in run.load_tasks():
            if t["category"] != "coding":
                continue
            with open(os.path.join(t["dir"], "reference.py"), encoding="utf-8") as fh:
                result = score.run_tests(t["dir"], fh.read())
            self.assertTrue(result["passed"], (t["id"], result))
            self.assertGreater(result["ran"], 0)

    def test_wrong_answer_fails(self):
        t = next(t for t in run.load_tasks() if t["id"] == "e_roman")
        result = score.run_tests(t["dir"], "def int_to_roman(n):\n    return 'I' * n\n")
        self.assertFalse(result["passed"])
        self.assertGreater(result["failed"], 0)

    def test_syntax_error_fails(self):
        t = next(t for t in run.load_tasks() if t["id"] == "e_roman")
        self.assertFalse(score.run_tests(t["dir"], "def int_to_roman(n)\n")["passed"])


class Extraction(unittest.TestCase):
    def test_last_python_block(self):
        text = "x\n```python\nold = 1\n```\nbetter:\n```python\nnew = 2\n```\n"
        self.assertEqual(score.extract_code(text), "new = 2\n")

    def test_other_fences(self):
        self.assertEqual(score.extract_code("```\na = 1\n```"), "a = 1\n")
        self.assertEqual(score.extract_code("```py\nb = 2\n```\n```text\nout\n```"), "b = 2\n")
        self.assertEqual(score.extract_code("plain = 3"), "plain = 3")

    def test_auto_checks(self):
        tasks = {t["id"]: t for t in run.load_tasks()}
        good = json.dumps([{"tip": "a", "why": "b"}] * 5)
        self.assertTrue(score.auto_checks(tasks["format_json_tips"], good)["json_only_5"])
        self.assertFalse(score.auto_checks(tasks["format_json_tips"],
                                           "```json\n" + good + "\n```")["json_only_5"])
        pg = tasks["ww_vote"]
        ok = json.dumps({k: "x" for k in pg["schema"]["required"]})
        self.assertTrue(score.auto_checks(pg, ok)["valid_json"])
        self.assertFalse(score.auto_checks(pg, "{}")["valid_json"])


class Blinding(unittest.TestCase):
    def test_round_trip(self):
        tmp = tempfile.mkdtemp()
        try:
            for model in ("m1", "m2"):
                with open(os.path.join(tmp, f"{model}.jsonl"), "w") as fh:
                    for s in (0, 1):
                        fh.write(json.dumps({"task": "fact_canberra", "category": "chat",
                                             "sample": s, "model": model,
                                             "content": f"{model} answer {s}"}) + "\n")
            blind.export(tmp, seed=1)
            packet = open(os.path.join(tmp, "blind", "fact_canberra.md")).read()
            key = json.load(open(os.path.join(tmp, "blind", "key.json")))["fact_canberra"]
            self.assertEqual(sorted(key), ["A", "B", "C", "D"])
            # score m1's answers 5 and m2's 1, by label
            judg = {"fact_canberra": {lab: {"correct": 5 if w["model"] == "m1" else 1}
                                      for lab, w in key.items()}}
            with open(os.path.join(tmp, "judgments.json"), "w") as fh:
                json.dump(judg, fh)
            blind.unblind(tmp)
            summary = json.load(open(os.path.join(tmp, "summary.json")))["by_model"]
            self.assertEqual(summary["m1"]["chat"], 5)
            self.assertEqual(summary["m2"]["all"], 1)
            # the packet shows the answers but never the model names
            self.assertNotIn('"model"', packet)
            for lab in key:
                self.assertIn(f"### {lab}", packet)
        finally:
            shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main()
