"""models.ini, models-dev.ini and models.list agree with each other."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def presets(path):
    """{section: {key: value}} from a llama-server preset file (keys before any section are skipped)."""
    out, section = {}, None
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith(";"):
            continue
        m = re.fullmatch(r"\[(.+)\]", line)
        if m:
            section = out.setdefault(m.group(1), {})
        elif section is not None:
            key, sep, value = line.partition("=")
            assert sep, f"{path.name}: not key = value: {line}"
            section[key.strip()] = value.strip()
    return out


def listed():
    rows = []
    for n, line in enumerate((ROOT / "models.list").read_text().splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        rows.append((n, line.split()))
    return rows


class ModelsList(unittest.TestCase):
    def test_rows_are_well_formed(self):
        names = set()
        for n, cols in listed():
            with self.subTest(line=n):
                self.assertEqual(len(cols), 5, "set file bytes sha256 url")
                kind, name, size, digest, url = cols
                self.assertIn(kind, ("live", "dev"))
                self.assertRegex(size, r"^[1-9][0-9]*$")
                self.assertRegex(digest, r"^[0-9a-f]{64}$")
                self.assertTrue(url.startswith("https://"), url)
                # The saved name may differ from the URL's, e.g. when two repos publish the
                # same file name (Qwen3.6 with and without MTP)
                self.assertTrue(name.endswith(".gguf") and "/" not in name, name)
                self.assertTrue(url.endswith(".gguf"), "url must name a .gguf file")
                self.assertNotIn("/resolve/main/", url, "pin a commit, not main")
                self.assertNotIn((kind, name), names, "listed twice")
                names.add((kind, name))


class PresetsMatchList(unittest.TestCase):
    def check(self, ini, kind):
        sections = presets(ROOT / ini)
        used = set()
        for name, keys in sections.items():
            if name == "*":
                self.assertNotIn("model", keys, f"{ini}: [*] must not name a model")
                continue
            with self.subTest(preset=name):
                self.assertIn("model", keys)
                self.assertTrue(keys["model"].startswith("/models/"), keys["model"])
                used.add(keys["model"].removeprefix("/models/"))
        files = {cols[1] for _, cols in listed() if cols[0] == kind}
        self.assertEqual(used - files, set(), f"{ini} uses files missing from models.list ({kind})")
        self.assertEqual(files - used, set(), f"models.list ({kind}) has files no preset in {ini} uses")

    def test_live(self):
        self.check("models.ini", "live")

    def test_dev(self):
        self.check("models-dev.ini", "dev")


if __name__ == "__main__":
    unittest.main()
