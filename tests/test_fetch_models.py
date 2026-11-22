"""bin/fetch-models against local file:// URLs."""
import hashlib
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "bin" / "fetch-models"


class FetchModels(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.src = self.tmp / "src"
        self.dest = self.tmp / "dest"
        self.src.mkdir()
        self.data = b"pretend model weights\n" * 100
        self.digest = hashlib.sha256(self.data).hexdigest()
        (self.src / "a.gguf").write_bytes(self.data)

    def tearDown(self):
        subprocess.run(["rm", "-rf", str(self.tmp)], check=True)

    def run_fetch(self, rows, *args):
        lst = self.tmp / "models.list"
        lst.write_text("# comment\n\n" + "".join(" ".join(r) + "\n" for r in rows))
        return subprocess.run(
            [str(SCRIPT), "--list", str(lst), "--dest", str(self.dest), *args],
            capture_output=True, text=True,
        )

    def row(self, kind="live", name="a.gguf", size=None, digest=None, url=None):
        return [kind, name, str(len(self.data) if size is None else size),
                digest or self.digest, url or (self.src / "a.gguf").as_uri()]

    def test_downloads_and_verifies(self):
        r = self.run_fetch([self.row()])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual((self.dest / "a.gguf").read_bytes(), self.data)
        self.assertEqual((self.dest / ".verified" / "a.gguf").read_text().strip(), self.digest)
        self.assertFalse((self.dest / "a.gguf.part").exists())

    def test_verified_file_is_not_fetched_again(self):
        self.assertEqual(self.run_fetch([self.row()]).returncode, 0)
        r = self.run_fetch([self.row(url="file:///nonexistent/a.gguf")])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("a.gguf present", r.stdout)

    def test_file_copied_in_by_hand_is_checked_not_downloaded(self):
        self.dest.mkdir()
        (self.dest / "a.gguf").write_bytes(self.data)
        r = self.run_fetch([self.row(url="file:///nonexistent/a.gguf")])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("a.gguf verified", r.stdout)
        self.assertTrue((self.dest / ".verified" / "a.gguf").exists())

    def test_wrong_checksum_fails_and_leaves_nothing(self):
        r = self.run_fetch([self.row(digest="0" * 64)])
        self.assertEqual(r.returncode, 1)
        self.assertIn("wrong checksum", r.stderr)
        self.assertFalse((self.dest / "a.gguf").exists())
        self.assertFalse((self.dest / "a.gguf.part").exists())

    def test_wrong_size_fails(self):
        r = self.run_fetch([self.row(size=len(self.data) + 1)])
        self.assertEqual(r.returncode, 1)
        self.assertFalse((self.dest / "a.gguf").exists())

    def test_failed_download_fails(self):
        r = self.run_fetch([self.row(url="file:///nonexistent/a.gguf")])
        self.assertEqual(r.returncode, 1)
        self.assertIn("download failed", r.stderr)

    def test_resumes_a_partial_download(self):
        self.dest.mkdir()
        (self.dest / "a.gguf.part").write_bytes(self.data[:500])
        r = self.run_fetch([self.row()])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("resuming", r.stdout)
        self.assertEqual((self.dest / "a.gguf").read_bytes(), self.data)

    def test_only_the_requested_set(self):
        rows = [self.row(kind="dev", name="b.gguf", url="file:///nonexistent/b.gguf"), self.row()]
        r = self.run_fetch(rows)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse((self.dest / "b.gguf").exists())
        r = self.run_fetch(rows, "--dev")
        self.assertEqual(r.returncode, 1)
        self.assertIn("b.gguf download failed", r.stderr)

    def test_other_files_continue_after_a_failure(self):
        rows = [self.row(name="b.gguf", url="file:///nonexistent/b.gguf"), self.row()]
        r = self.run_fetch(rows)
        self.assertEqual(r.returncode, 1)
        self.assertTrue((self.dest / "a.gguf").exists())


if __name__ == "__main__":
    unittest.main()
