from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.mindflow_paths import resolve_output, resolve_vault_root


class MindFlowPathTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.vault = root / "mindflow"
        for name in ("skills", "Papers", "Workbench"):
            (self.vault / name).mkdir(parents=True, exist_ok=True)
        (self.vault / "AGENTS.md").write_text("# test\n", encoding="utf-8")
        self.script = self.vault / "skills/1-literature/daily-papers/fetch.py"
        self.script.parent.mkdir(parents=True)
        self.script.write_text("# fixture\n", encoding="utf-8")
        self.home = root / "home"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_resolves_from_real_file_behind_symlink(self) -> None:
        link = self.home / ".codex/skills/daily-papers"
        link.parent.mkdir(parents=True)
        link.symlink_to(self.script.parent)
        self.assertEqual(
            resolve_vault_root(link / "fetch.py"), self.vault.resolve()
        )

    def test_output_rejects_absolute_and_parent_paths(self) -> None:
        for value in ("/tmp/out", "../notes", "Workbench/../../notes"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                resolve_output(self.vault, value)

    def test_output_accepts_only_contained_relative_path(self) -> None:
        self.assertEqual(
            resolve_output(self.vault, "Workbench/daily/.candidates.json"),
            (self.vault / "Workbench/daily/.candidates.json").resolve(),
        )

    def test_missing_sentinel_fails_closed(self) -> None:
        (self.vault / "AGENTS.md").unlink()
        with self.assertRaisesRegex(ValueError, "cannot resolve MindFlow"):
            resolve_vault_root(self.script)


if __name__ == "__main__":
    unittest.main()
