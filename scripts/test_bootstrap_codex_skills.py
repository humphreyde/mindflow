from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parent / "bootstrap_codex_skills.py"
SPEC = importlib.util.spec_from_file_location("bootstrap_codex_skills", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

MANAGED_LINKS = MODULE.MANAGED_LINKS
apply_bootstrap = MODULE.apply_bootstrap
plan_bootstrap = MODULE.plan_bootstrap
rollback = MODULE.rollback


class BootstrapCodexSkillsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name).resolve()
        self.vault = root / "mindflow"
        self.codex_home = root / ".codex"
        self.skills = self.codex_home / "skills"
        self.skills.mkdir(parents=True)
        for relative in MANAGED_LINKS.values():
            source = self.vault / relative
            source.mkdir(parents=True)
            (source / "SKILL.md").write_text("---\nname: test\n---\n", encoding="utf-8")
        for name in ("AGENTS.md",):
            (self.vault / name).write_text("# test\n", encoding="utf-8")
        for name in ("Papers", "Workbench"):
            (self.vault / name).mkdir()
        self.other = root / "other"
        self.other.mkdir()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def link(self, name: str, target: Path) -> Path:
        path = self.skills / name
        path.symlink_to(target)
        return path

    def legacy_directory(self, name: str, content: str = "legacy\n") -> Path:
        path = self.skills / name
        path.mkdir()
        (path / "legacy.txt").write_text(content, encoding="utf-8")
        return path

    def test_correct_link_is_noop(self) -> None:
        self.link("daily-papers", self.vault / MANAGED_LINKS["daily-papers"])
        self.assertEqual(
            plan_bootstrap(self.vault, self.codex_home)["daily-papers"].action,
            "noop",
        )

    def test_conflicting_directory_is_archived_before_link(self) -> None:
        self.legacy_directory("daily-papers")
        self.assertEqual(
            plan_bootstrap(self.vault, self.codex_home)["daily-papers"].action,
            "archive-and-link",
        )

    def test_missing_canonical_source_fails_closed(self) -> None:
        source = self.vault / MANAGED_LINKS["daily-papers"]
        (source / "SKILL.md").unlink()
        source.rmdir()
        with self.assertRaisesRegex(ValueError, "canonical skill source is missing"):
            plan_bootstrap(self.vault, self.codex_home)

    def test_ordinary_file_conflict_fails_closed(self) -> None:
        (self.skills / "daily-papers").write_text("not a skill directory\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "ordinary file conflict"):
            plan_bootstrap(self.vault, self.codex_home)

    def test_wrong_symlink_is_archived_before_link(self) -> None:
        self.link("daily-papers", self.other)
        self.assertEqual(
            plan_bootstrap(self.vault, self.codex_home)["daily-papers"].action,
            "archive-and-link",
        )

    def test_archive_collision_stops_before_mutation(self) -> None:
        legacy = self.legacy_directory("daily-papers")
        collision = self.codex_home / "skills-legacy/2026-11-03/daily-papers"
        collision.mkdir(parents=True)
        with self.assertRaisesRegex(FileExistsError, "archive path already exists"):
            apply_bootstrap(self.vault, self.codex_home, "2026-11-03")
        self.assertTrue((legacy / "legacy.txt").is_file())
        self.assertFalse(legacy.is_symlink())

    def test_partial_apply_rolls_back_current_transaction(self) -> None:
        original_install = MODULE._install_link
        calls = 0

        def fail_second_install(path: Path, target: Path) -> None:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("injected link failure")
            original_install(path, target)

        with mock.patch.object(MODULE, "_install_link", side_effect=fail_second_install):
            with self.assertRaisesRegex(OSError, "injected link failure"):
                apply_bootstrap(self.vault, self.codex_home, "2026-11-03")

        for name in MANAGED_LINKS:
            self.assertFalse((self.skills / name).exists())
            self.assertFalse((self.skills / name).is_symlink())

    def test_second_apply_is_idempotent(self) -> None:
        manifest = apply_bootstrap(self.vault, self.codex_home, "2026-11-03")
        second = apply_bootstrap(self.vault, self.codex_home, "2026-11-03")
        self.assertEqual(second, manifest)
        for name, relative in MANAGED_LINKS.items():
            self.assertEqual((self.skills / name).resolve(), (self.vault / relative).resolve())

    def test_rollback_stops_if_link_drifted(self) -> None:
        self.legacy_directory("daily-papers")
        manifest = apply_bootstrap(self.vault, self.codex_home, "2026-11-03")
        link = self.skills / "daily-papers"
        link.unlink()
        link.symlink_to(self.other)
        with self.assertRaisesRegex(ValueError, "drift"):
            rollback(manifest, self.codex_home)
        self.assertTrue(
            (self.codex_home / "skills-legacy/2026-11-03/daily-papers").is_dir()
        )

    def test_rollback_rejects_manifest_outside_archive_root(self) -> None:
        manifest = Path(self.temp_dir.name) / "outside-manifest.json"
        manifest.write_text(json.dumps({"operations": []}), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "manifest escapes"):
            rollback(manifest, self.codex_home)

    def test_apply_and_rollback_restore_exact_legacy_tree(self) -> None:
        legacy = self.legacy_directory("daily-papers", "preserve me\n")
        retire = self.legacy_directory("paper-reader", "retire me\n")
        manifest = apply_bootstrap(self.vault, self.codex_home, "2026-11-03")

        self.assertTrue(legacy.is_symlink())
        self.assertFalse(retire.exists())
        rollback(manifest, self.codex_home)

        self.assertFalse(legacy.is_symlink())
        self.assertEqual((legacy / "legacy.txt").read_text(encoding="utf-8"), "preserve me\n")
        self.assertEqual((retire / "legacy.txt").read_text(encoding="utf-8"), "retire me\n")


if __name__ == "__main__":
    unittest.main()
