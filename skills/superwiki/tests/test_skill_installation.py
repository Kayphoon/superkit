"""End-to-end behavior tests for the skill-only installation path.

These tests exercise the real ``superwiki-init`` (team and personal modes) and
``skills.sh`` scripts in isolated temporary directories.  They assert filesystem behavior (symlinks,
preserved content, rejected options) rather than script text.
"""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
INIT_SCRIPT = REPO_ROOT / "superwiki-init"
BASH = "/bin/bash"

RUNTIME_LINKS = (
    (".agents", ".agents/skills"),
    (".opencode", ".opencode/skills"),
    (".claude", ".claude/skills"),
    (".cursor", ".cursor/skills"),
)

# ``skills.sh`` links SuperWiki only into the agent-compatible skill dir.
GLOBAL_SKILL_DIRS = (Path(".agents") / "skills",)

# Runtime-specific global skill dirs that ``skills.sh`` must never create links in.
OTHER_GLOBAL_SKILL_DIRS = (
    Path(".config") / "opencode" / "skills",
    Path(".claude") / "skills",
    Path(".codex") / "skills",
    Path(".cursor") / "skills",
)


def make_dist(root: Path) -> Path:
    """Create an installable copy of the real SuperWiki skill."""
    dist = root / "dist"
    dist.mkdir(parents=True)
    for name in ("superwiki-init", "skills.sh", "SKILL.md", "VERSION"):
        shutil.copy2(REPO_ROOT / name, dist / name)
    for name in ("references", "templates", "agents"):
        shutil.copytree(REPO_ROOT / name, dist / name)
    return dist


def clean_env(home: Path) -> dict:
    env = os.environ.copy()
    for key in ("CODEX_HOME", "OPENCODE_CONFIG_DIR"):
        env.pop(key, None)
    env["HOME"] = str(home)
    return env


def tree_snapshot(root: Path) -> dict:
    """Capture directories, files (bytes) and symlink targets below ``root``."""
    snapshot = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if path.is_symlink():
            snapshot[rel] = ("link", os.readlink(path))
        elif path.is_dir():
            snapshot[rel] = ("dir",)
        else:
            snapshot[rel] = ("file", path.read_bytes())
    return snapshot


class InstallerTestCase(unittest.TestCase):
    def sandbox(self) -> Path:
        root = Path(tempfile.mkdtemp(prefix="superwiki-install-"))
        self.addCleanup(shutil.rmtree, root, True)
        return root

    def run_script(self, script: Path, *args, cwd: Path, home: Path):
        return subprocess.run(
            [BASH, str(script), *[str(arg) for arg in args]],
            cwd=str(cwd),
            env=clean_env(home),
            capture_output=True,
            text=True,
        )

    def assert_link_to(self, link: Path, target: Path) -> None:
        self.assertTrue(link.is_symlink(), f"{link} is not a symlink")
        self.assertEqual(
            Path(os.path.realpath(link)),
            Path(os.path.realpath(target)),
            f"{link} resolves to {os.path.realpath(link)}, expected {os.path.realpath(target)}",
        )


ENTRY = "superwiki-auto"
TEMPLATE_VERSION = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()


def git_init(path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(path)], check=True)


def git_status(path: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(path), "status", "--porcelain", "--untracked-files=all"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def frontmatter(skill_file: Path) -> dict:
    try:
        import yaml
    except ImportError:  # pragma: no cover - depends on the host
        raise unittest.SkipTest("PyYAML is not installed")
    text = skill_file.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{skill_file} has no frontmatter"
    return yaml.safe_load(text.split("---\n", 2)[1])


class ProjectInitializerTests(InstallerTestCase):
    def init(self, *args, cwd: Path, home: Path):
        return self.run_script(INIT_SCRIPT, *args, cwd=cwd, home=home)

    def new_project(self, name: str = "project", git: bool = True):
        root = self.sandbox()
        project = root / name
        project.mkdir()
        if git:
            git_init(project)
        return root, project

    def test_mode_is_required_before_any_write(self):
        for flags in ((), ("--team", "--personal"), ("--personal", "--team")):
            with self.subTest(flags=flags):
                root, project = self.new_project(git=False)
                proc = self.init(*flags, project, cwd=root, home=root / "home")
                self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
                self.assertEqual(list(project.iterdir()), [])

    def test_team_mode_keeps_knowledge_in_agents_skills(self):
        root, project = self.new_project()

        proc = self.init("--team", project, cwd=root, home=root / "home")

        self.assertEqual(proc.returncode, 0, proc.stderr)
        skills = project / ".agents" / "skills"
        self.assertTrue(skills.is_dir())
        self.assertFalse(skills.is_symlink())
        entry = skills / ENTRY
        for rel in (
            "SKILL.md",
            "references/writing.md",
            "references/review.md",
            "references/local.md",
        ):
            self.assertTrue((entry / rel).is_file(), rel)
        self.assertFalse(os.path.lexists(project / ".wiki"))
        self.assertFalse(os.path.lexists(project / ".claude"))
        self.assertIn(
            "/.wiki/staging.md",
            (project / ".gitignore").read_text(encoding="utf-8").splitlines(),
        )
        status = git_status(project)
        self.assertIn(".agents/skills/superwiki-auto/SKILL.md", status)
        self.assertIn(".gitignore", status)

    def test_team_mode_optional_runtime_links_point_at_agents_skills(self):
        root, project = self.new_project()

        proc = self.init(
            "--team", "--claude", "--cursor", project, cwd=root, home=root / "home"
        )

        self.assertEqual(proc.returncode, 0, proc.stderr)
        skills = project / ".agents" / "skills"
        self.assert_link_to(project / ".claude" / "skills", skills)
        self.assert_link_to(project / ".cursor" / "skills", skills)
        self.assertFalse(os.path.lexists(project / ".opencode"))

    def test_personal_mode_links_runtimes_and_leaves_git_status_clean(self):
        root, project = self.new_project()

        proc = self.init("--personal", project, cwd=root, home=root / "home")

        self.assertEqual(proc.returncode, 0, proc.stderr)
        store = project / ".wiki" / "skills"
        self.assertTrue((store / ENTRY / "SKILL.md").is_file())
        for _, link_path in RUNTIME_LINKS:
            self.assert_link_to(project / link_path, store)
        self.assertEqual(git_status(project), "")
        self.assertFalse(os.path.lexists(project / ".gitignore"))
        exclude = (project / ".git" / "info" / "exclude").read_text(encoding="utf-8")
        self.assertIn("/.wiki/", exclude.splitlines())

    def test_personal_mode_selected_runtime_only(self):
        root, project = self.new_project(git=False)

        proc = self.init("--personal", "--claude", project, cwd=root, home=root / "home")

        self.assertEqual(proc.returncode, 0, proc.stderr)
        store = project / ".wiki" / "skills"
        self.assert_link_to(project / ".claude" / "skills", store)
        for runtime_dir, _ in RUNTIME_LINKS:
            if runtime_dir != ".claude":
                self.assertFalse(os.path.lexists(project / runtime_dir), runtime_dir)

    def test_rendered_entry_is_a_valid_auto_skill(self):
        for mode, wiki_dir in (("team", ".agents/skills"), ("personal", ".wiki/skills")):
            with self.subTest(mode=mode):
                root, project = self.new_project()
                proc = self.init(f"--{mode}", project, cwd=root, home=root / "home")
                self.assertEqual(proc.returncode, 0, proc.stderr)

                entry = project / wiki_dir / ENTRY
                meta = frontmatter(entry / "SKILL.md")
                self.assertEqual(meta["name"], ENTRY)
                self.assertFalse(meta["name"].startswith("wiki-"))
                self.assertNotIn("disable-model-invocation", meta)
                self.assertTrue(1 <= len(meta["description"].strip()) <= 1024)
                self.assertIn(wiki_dir, meta["description"])
                self.assertEqual(meta["metadata"]["superwiki-mode"], mode)
                self.assertEqual(
                    str(meta["metadata"]["superwiki-template"]), TEMPLATE_VERSION
                )
                for path in entry.rglob("*"):
                    if path.is_file():
                        self.assertNotIn("{{", path.read_text(encoding="utf-8"), path)

    def test_rerun_upgrades_template_and_preserves_local_rules_and_modules(self):
        root, project = self.new_project()
        home = root / "home"
        self.assertEqual(self.init("--team", project, cwd=root, home=home).returncode, 0)
        fresh = (project / ".agents" / "skills" / ENTRY / "SKILL.md").read_bytes()

        skills = project / ".agents" / "skills"
        local = skills / ENTRY / "references" / "local.md"
        local.write_text("项目专属规则\n", encoding="utf-8")
        module = skills / "wiki-foo" / "SKILL.md"
        module.parent.mkdir()
        module.write_text("---\nname: wiki-foo\n---\n", encoding="utf-8")
        entry = skills / ENTRY / "SKILL.md"
        entry.write_text(
            fresh.decode("utf-8").replace(TEMPLATE_VERSION, "2000.01.01"),
            encoding="utf-8",
        )

        proc = self.init("--team", project, cwd=root, home=home)

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("2000.01.01 -> " + TEMPLATE_VERSION, proc.stdout)
        self.assertEqual(entry.read_bytes(), fresh)
        self.assertEqual(local.read_text(encoding="utf-8"), "项目专属规则\n")
        self.assertEqual(module.read_text(encoding="utf-8"), "---\nname: wiki-foo\n---\n")
        gitignore = (project / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertEqual(gitignore.count("/.wiki/staging.md"), 1)

    def test_mode_switch_is_refused_without_changes(self):
        for first, second in (("team", "personal"), ("personal", "team")):
            with self.subTest(first=first, second=second):
                root, project = self.new_project()
                home = root / "home"
                self.assertEqual(
                    self.init(f"--{first}", project, cwd=root, home=home).returncode, 0
                )
                before = tree_snapshot(project)

                proc = self.init(f"--{second}", project, cwd=root, home=home)

                self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
                self.assertEqual(tree_snapshot(project), before)

    def test_team_mode_refuses_symlinked_agents_skills(self):
        root, project = self.new_project(git=False)
        outside = root / "outside-skills"
        outside.mkdir()
        (project / ".agents").mkdir()
        (project / ".agents" / "skills").symlink_to(outside)

        proc = self.init("--team", project, cwd=root, home=root / "home")

        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertEqual(list(outside.iterdir()), [])
        self.assertFalse(os.path.lexists(project / ".wiki"))

    def test_any_conflict_aborts_before_writing_anything(self):
        root, project = self.new_project(git=False)
        outside = root / "outside-skills"
        outside.mkdir()
        (project / ".claude").mkdir()
        (project / ".claude" / "skills").write_text("user owned\n", encoding="utf-8")
        (project / ".agents").mkdir()
        (project / ".agents" / "skills").symlink_to(outside)
        before = tree_snapshot(project)

        proc = self.init("--personal", project, cwd=root, home=root / "home")

        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn(".claude/skills", proc.stderr)
        self.assertIn(".agents/skills", proc.stderr)
        self.assertEqual(tree_snapshot(project), before)
        self.assertEqual(list(outside.iterdir()), [])

        # Narrowing to a runtime without a conflict succeeds.
        proc = self.init("--personal", "--opencode", project, cwd=root, home=root / "home")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assert_link_to(project / ".opencode" / "skills", project / ".wiki" / "skills")

    def test_team_mode_conflicting_runtime_entry_aborts(self):
        root, project = self.new_project()
        (project / ".claude" / "skills").mkdir(parents=True)
        before = tree_snapshot(project)

        proc = self.init("--team", "--claude", project, cwd=root, home=root / "home")

        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertEqual(tree_snapshot(project), before)

    def test_legacy_layouts_block_the_other_mode(self):
        cases = (
            ("team", ".wiki/skills/wiki-old"),
            ("team", ".agents/skills/superwiki"),
            ("personal", ".agents/skills/wiki-old"),
            ("personal", ".agents/skills/superwiki"),
        )
        for mode, legacy in cases:
            with self.subTest(mode=mode, legacy=legacy):
                root, project = self.new_project()
                (project / legacy).mkdir(parents=True)
                (project / legacy / "SKILL.md").write_text("legacy\n", encoding="utf-8")
                before = tree_snapshot(project)

                proc = self.init(f"--{mode}", project, cwd=root, home=root / "home")

                self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
                self.assertEqual(tree_snapshot(project), before)

    def test_legacy_same_mode_layouts_upgrade_in_place(self):
        for mode, legacy in (("team", ".agents/skills/wiki-old"), ("personal", ".wiki/skills/wiki-old")):
            with self.subTest(mode=mode):
                root, project = self.new_project()
                (project / legacy).mkdir(parents=True)
                module = project / legacy / "SKILL.md"
                module.write_text("legacy\n", encoding="utf-8")

                proc = self.init(f"--{mode}", project, cwd=root, home=root / "home")

                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertEqual(module.read_text(encoding="utf-8"), "legacy\n")
                self.assertTrue((module.parent.parent / ENTRY / "SKILL.md").is_file())

    def test_upgrade_removes_files_dropped_from_the_template(self):
        root, project = self.new_project()
        home = root / "home"
        self.assertEqual(self.init("--team", project, cwd=root, home=home).returncode, 0)
        entry = project / ".agents" / "skills" / ENTRY
        stale = entry / "references" / "retired.md"
        stale.write_text("old template file\n", encoding="utf-8")
        (entry / "old-dir").mkdir()
        (entry / "old-dir" / "x.md").write_text("x\n", encoding="utf-8")

        proc = self.init("--team", project, cwd=root, home=home)

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertFalse(stale.exists())
        self.assertFalse((entry / "old-dir").exists())
        self.assertTrue((entry / "references" / "local.md").is_file())

    def test_projects_in_a_repo_subdirectory_get_ignore_rules(self):
        for mode in ("team", "personal"):
            with self.subTest(mode=mode):
                root = self.sandbox()
                repo = root / "repo"
                project = repo / "packages" / "app"
                project.mkdir(parents=True)
                git_init(repo)

                proc = self.init(f"--{mode}", project, cwd=root, home=root / "home")
                self.assertEqual(proc.returncode, 0, proc.stderr)
                (project / ".wiki").mkdir(exist_ok=True)
                (project / ".wiki" / "staging.md").write_text("draft\n", encoding="utf-8")

                status = git_status(repo)
                self.assertNotIn("staging.md", status)
                if mode == "personal":
                    self.assertEqual(status, "")
                else:
                    self.assertIn("packages/app/.agents/skills/superwiki-auto/SKILL.md", status)

    def test_staging_cleanup_rule_matches_the_mode(self):
        expected = {"team": "已被提交", "personal": "已写入正式模块"}
        for mode, wiki_dir in (("team", ".agents/skills"), ("personal", ".wiki/skills")):
            with self.subTest(mode=mode):
                root, project = self.new_project()
                self.assertEqual(
                    self.init(f"--{mode}", project, cwd=root, home=root / "home").returncode, 0
                )
                writing = (project / wiki_dir / ENTRY / "references" / "writing.md").read_text(
                    encoding="utf-8"
                )
                self.assertIn(expected[mode], writing)
                other = expected["personal" if mode == "team" else "team"]
                self.assertNotIn(other, writing)

    def test_paths_with_spaces_stay_functional(self):
        for mode, wiki_dir in (("team", ".agents/skills"), ("personal", ".wiki/skills")):
            with self.subTest(mode=mode):
                root, project = self.new_project("project with spaces")
                workdir = root / "work dir"
                workdir.mkdir()

                proc = self.init(f"--{mode}", project, cwd=workdir, home=root / "home")

                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertTrue((project / wiki_dir / ENTRY / "SKILL.md").is_file())

    def test_non_git_project_gets_no_ignore_files(self):
        for mode in ("team", "personal"):
            with self.subTest(mode=mode):
                root, project = self.new_project(git=False)
                proc = self.init(f"--{mode}", project, cwd=root, home=root / "home")
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertFalse(os.path.lexists(project / ".gitignore"))
                self.assertFalse(os.path.lexists(project / ".git"))

    def test_stale_hook_option_is_rejected_before_any_write(self):
        for args in (("--hook",), ("--team", "--hook", "project"), ("project", "--hook")):
            with self.subTest(args=args):
                root, project = self.new_project(git=False)
                resolved = tuple(project if arg == "project" else arg for arg in args)

                proc = self.init(*resolved, cwd=root, home=root / "home")

                self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
                self.assertEqual(list(project.iterdir()), [])
                self.assertFalse((root / ".wiki").exists())


class UninitializedProjectSafetyTests(InstallerTestCase):
    """Zero-footprint invariant: invalid or aborted runs write nothing."""

    def assert_zero_footprint(self, root: Path, project: Path) -> None:
        self.assertFalse(os.path.lexists(project / ".wiki"))
        for runtime_dir, _ in RUNTIME_LINKS:
            self.assertFalse(os.path.lexists(project / runtime_dir), runtime_dir)
        self.assertFalse(os.path.lexists(project / ".gitignore"))
        self.assertEqual(list(root.rglob("staging.md")), [])
        self.assertEqual(list(root.rglob(".wiki")), [])
        self.assertEqual(list(root.rglob(ENTRY)), [])

    def test_rejected_options_and_invalid_commands_leave_no_footprint(self):
        cases = (
            ("--hook",),
            ("--team", "--hook", "project"),
            ("project", "--hook"),
            ("--team", "--bogus", "project"),
            ("-x", "project"),
            ("--wiki", "project"),
            ("--team", "project", "other"),
            ("project",),
            ("--team", "--personal", "project"),
        )
        for args in cases:
            with self.subTest(args=args):
                root = self.sandbox()
                project = root / "project"
                project.mkdir()
                other = root / "other"
                other.mkdir()
                home = root / "home"
                targets = {"project": project, "other": other}
                resolved = tuple(targets.get(arg, arg) for arg in args)

                proc = self.run_script(INIT_SCRIPT, *resolved, cwd=root, home=home)

                self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
                self.assert_zero_footprint(root, project)
                self.assertEqual(list(project.iterdir()), [])
                self.assertEqual(list(other.iterdir()), [])
                self.assertFalse(home.exists())

    def test_aborted_or_help_runs_create_nothing(self):
        root = self.sandbox()
        home = root / "home"
        home.mkdir()

        missing = root / "not-a-project"
        proc = self.run_script(INIT_SCRIPT, "--team", missing, cwd=root, home=home)
        self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertFalse(missing.exists())
        self.assertEqual(sorted(path.name for path in root.iterdir()), ["home"])

        file_project = root / "afile"
        file_project.write_bytes(b"keep\n")
        proc = self.run_script(INIT_SCRIPT, "--personal", file_project, cwd=root, home=home)
        self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(file_project.read_bytes(), b"keep\n")
        self.assertEqual(list(root.rglob(".wiki")), [])

        project = root / "project"
        project.mkdir()
        for args in (("-h",), ("--help",), ("--team", "-h")):
            with self.subTest(args=args):
                proc = self.run_script(INIT_SCRIPT, *args, project, cwd=root, home=home)
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                self.assertIn("用法", proc.stdout)
                self.assert_zero_footprint(root, project)
                self.assertEqual(list(project.iterdir()), [])
                self.assertEqual(list(home.iterdir()), [])

    def test_failed_run_preserves_existing_user_content_exactly(self):
        root = self.sandbox()
        project = root / "project"
        (project / "src").mkdir(parents=True)
        (project / "README.md").write_bytes(b"keep me\n")
        (project / "src" / "main.py").write_bytes(b"print('hi')\n")
        (project / ".claude").mkdir()
        (project / ".claude" / "settings.json").write_bytes(b'{"theme": "dark"}\n')
        before = tree_snapshot(project)

        for args in (
            ("--hook", project),
            ("--team", "--bogus", project),
            ("--team", project, "extra"),
            (project,),
        ):
            with self.subTest(args=args):
                proc = self.run_script(INIT_SCRIPT, *args, cwd=root, home=root / "home")
                self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
                self.assertEqual(tree_snapshot(project), before)

    def test_no_target_run_only_touches_the_resolved_cwd(self):
        root = self.sandbox()
        called_from = root / "cwd-project"
        called_from.mkdir()
        sibling = root / "sibling-project"
        sibling.mkdir()
        home = root / "home"
        home.mkdir()

        proc = self.run_script(INIT_SCRIPT, "--personal", cwd=called_from, home=home)

        self.assertEqual(proc.returncode, 0, proc.stderr)
        store = called_from / ".wiki" / "skills"
        self.assertTrue((store / ENTRY / "SKILL.md").is_file())
        for _, link_path in RUNTIME_LINKS:
            self.assert_link_to(called_from / link_path, store)
        self.assertEqual(list(sibling.iterdir()), [])
        self.assertEqual(list(home.iterdir()), [])
        self.assertFalse(os.path.lexists(root / ".agents"))
        self.assertFalse(os.path.lexists(root / ".wiki"))


class GlobalSkillInvocationTests(unittest.TestCase):
    def test_global_skill_is_user_invoked_in_every_runtime(self):
        meta = frontmatter(REPO_ROOT / "SKILL.md")
        self.assertEqual(meta["name"], "superwiki")
        self.assertIs(meta["disable-model-invocation"], True)
        try:
            import yaml
        except ImportError:  # pragma: no cover
            raise unittest.SkipTest("PyYAML is not installed")
        policy = yaml.safe_load(
            (REPO_ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        )["policy"]
        self.assertIs(policy["allow_implicit_invocation"], False)

    def test_template_is_not_discoverable_as_a_skill(self):
        self.assertEqual(list((REPO_ROOT / "templates").rglob("SKILL.md")), [])

    def test_template_entry_name_differs_from_global_skill(self):
        text = (REPO_ROOT / "templates" / ENTRY / "SKILL.md.tmpl").read_text(encoding="utf-8")
        self.assertIn(f"name: {ENTRY}\n", text)
        self.assertNotIn("disable-model-invocation", text)


class GlobalInstallerTests(InstallerTestCase):
    def test_global_install_creates_only_superwiki_skill_link(self):
        root = self.sandbox()
        # Use spaces in the install source to exercise quoting.
        dist = make_dist(root / "install dir with spaces")
        home = root / "home"
        home.mkdir()

        proc = self.run_script(dist / "skills.sh", cwd=root, home=home)

        self.assertEqual(proc.returncode, 0, proc.stderr)

        for skills_dir in GLOBAL_SKILL_DIRS:
            installed = home / skills_dir
            superwiki_link = installed / "superwiki"
            self.assert_link_to(superwiki_link, dist)
            # Installed links expose the real entrypoint and role docs.
            self.assertTrue((superwiki_link / "SKILL.md").is_file())
            self.assertTrue(
                (superwiki_link / "references" / "roles" / "wiki-auditor.md").is_file()
            )
            self.assertTrue(
                (superwiki_link / "templates" / "superwiki-auto" / "SKILL.md.tmpl").is_file()
            )

            # Fresh install dirs contain exactly this one skill: no siblings.
            self.assertEqual(
                sorted(path.name for path in installed.iterdir()), ["superwiki"]
            )

        # Runtime-specific skill dirs are not created at all: the installer
        # only targets the agent-compatible dir.
        for skills_dir in OTHER_GLOBAL_SKILL_DIRS:
            self.assertFalse(
                os.path.lexists(home / skills_dir),
                f"{skills_dir} must not be created by skills.sh",
            )

        # Installation never registers helper agents or creates agent dirs.
        for agents_dir in (
            home / ".codex" / "agents",
            home / ".config" / "opencode" / "agents",
            home / ".claude" / "agents",
            home / ".cursor" / "agents",
        ):
            self.assertFalse(agents_dir.exists())

    def test_global_install_preserves_preexisting_unrelated_skill_entries(self):
        root = self.sandbox()
        dist = make_dist(root / "dist")
        home = root / "home"

        # A foreign skill symlink is never repointed.
        foreign_librarian = root / "foreign" / "librarian"
        foreign_librarian.mkdir(parents=True)
        (foreign_librarian / "SKILL.md").write_text(
            "user owned librarian\n", encoding="utf-8"
        )
        claude_skills = home / ".claude" / "skills"
        claude_skills.mkdir(parents=True)
        librarian_link = claude_skills / "librarian"
        librarian_link.symlink_to(foreign_librarian)

        # An existing unrelated skill directory is left untouched.
        explorer_dir = home / ".config" / "opencode" / "skills" / "explorer"
        explorer_dir.mkdir(parents=True)
        explorer_marker = explorer_dir / "marker.txt"
        explorer_marker.write_text("user owned explorer\n", encoding="utf-8")

        # An existing unrelated skill file is left untouched.
        agents_skills = home / ".agents" / "skills"
        agents_skills.mkdir(parents=True)
        explorer_file = agents_skills / "explorer"
        explorer_bytes = b"user owned explorer file\n"
        explorer_file.write_bytes(explorer_bytes)

        # A dangling unrelated skill link also stays in place.
        dangling = home / ".cursor" / "skills" / "librarian"
        dangling.parent.mkdir(parents=True)
        dangling.symlink_to(root / "missing-librarian-target")

        # The Codex global dir holds a foreign entry too; it must never gain
        # this skill and must stay byte-for-byte identical.
        codex_skills = home / ".codex" / "skills"
        codex_skills.mkdir(parents=True)
        codex_foreign = codex_skills / "other-skill"
        codex_foreign_bytes = b"user owned codex skill\n"
        codex_foreign.write_bytes(codex_foreign_bytes)

        untouched = {
            skills_dir: tree_snapshot(home / skills_dir)
            for skills_dir in OTHER_GLOBAL_SKILL_DIRS
        }
        catalog_before = sorted(path.name for path in agents_skills.iterdir())

        proc = self.run_script(dist / "skills.sh", cwd=root, home=home)

        self.assertEqual(proc.returncode, 0, proc.stderr)

        self.assertTrue(librarian_link.is_symlink())
        self.assertEqual(os.readlink(librarian_link), str(foreign_librarian))
        self.assertEqual(
            (librarian_link / "SKILL.md").read_text(encoding="utf-8"),
            "user owned librarian\n",
        )
        self.assertEqual(
            explorer_marker.read_text(encoding="utf-8"), "user owned explorer\n"
        )
        self.assertFalse(explorer_file.is_symlink())
        self.assertEqual(explorer_file.read_bytes(), explorer_bytes)
        self.assertTrue(dangling.is_symlink())
        self.assertFalse(dangling.exists())
        self.assertEqual(os.readlink(dangling), str(root / "missing-librarian-target"))

        self.assertEqual(codex_foreign.read_bytes(), codex_foreign_bytes)

        # Only the agent-compatible scope receives the link. Every other
        # runtime skill dir stays byte-for-byte identical and never gains a
        # SuperWiki entry.
        for skills_dir in OTHER_GLOBAL_SKILL_DIRS:
            installed = home / skills_dir
            self.assertEqual(
                tree_snapshot(installed),
                untouched[skills_dir],
                f"{skills_dir} must not be modified by skills.sh",
            )
            self.assertFalse(
                os.path.lexists(installed / "superwiki"),
                f"{skills_dir} must not receive a superwiki link",
            )

        # The install target keeps its foreign entry and gains exactly one link.
        self.assertEqual(
            sorted(path.name for path in agents_skills.iterdir()),
            sorted(catalog_before + ["superwiki"]),
        )
        self.assert_link_to(agents_skills / "superwiki", dist)

    def test_global_install_preserves_unrelated_settings_and_creates_no_hooks(self):
        root = self.sandbox()
        dist = make_dist(root / "dist")
        home = root / "home"
        hook_config = home / ".codex" / "hooks.json"
        codex_config = home / ".codex" / "config.toml"
        claude_settings = home / ".claude" / "settings.json"
        hook_config.parent.mkdir(parents=True)
        claude_settings.parent.mkdir(parents=True)

        hook_bytes = b'{"hooks": {"UserPromptSubmit": ["user-owned.sh"]}}\n'
        config_bytes = b'model = "user-choice"\n'
        settings_bytes = b'{"theme": "dark"}\n'
        hook_config.write_bytes(hook_bytes)
        codex_config.write_bytes(config_bytes)
        claude_settings.write_bytes(settings_bytes)

        proc = self.run_script(dist / "skills.sh", cwd=root, home=home)

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(hook_config.read_bytes(), hook_bytes)
        self.assertEqual(codex_config.read_bytes(), config_bytes)
        self.assertEqual(claude_settings.read_bytes(), settings_bytes)

        # Skill installation alone never adds hook scripts or plugin config.
        self.assertFalse((home / ".codex" / "hooks").exists())
        self.assertFalse((home / ".codex" / "hooks.global.json").exists())
        self.assertEqual(
            list(home.rglob("superwiki-memory-hook.py")),
            [],
        )
        self.assertEqual(
            [path for path in home.rglob("hooks.json")],
            [hook_config],
        )

    def test_global_install_preserves_preexisting_agent_entries(self):
        root = self.sandbox()
        dist = make_dist(root / "dist")
        home = root / "home"

        # A stale distribution may still ship the retired helper definitions.
        legacy_agents = dist / "agents"
        legacy_agents.mkdir(exist_ok=True)
        legacy_bytes = {
            "memory-librarian.toml": b'name = "retired-memory-librarian"\n',
            "superwiki-initializer.toml": b'name = "retired-superwiki-initializer"\n',
            "superwiki-initializer.md": (
                b"---\nname: retired-superwiki-initializer\n---\n"
            ),
        }
        for name, content in legacy_bytes.items():
            (legacy_agents / name).write_bytes(content)

        # A user-owned foreign agent definition and a retired SuperWiki-named
        # link in an existing agents dir must survive installation untouched.
        codex_agents = home / ".codex" / "agents"
        codex_agents.mkdir(parents=True)
        foreign_agent = codex_agents / "memory-librarian.toml"
        foreign_bytes = b'name = "user-memory-librarian"\n'
        foreign_agent.write_bytes(foreign_bytes)
        # User-owned librarian/explorer agent configs captured before install
        # must remain byte-identical; the installer has no agent step.
        librarian_agent = codex_agents / "librarian.toml"
        librarian_agent_bytes = b'name = "user-librarian"\nmodel = "user-choice"\n'
        librarian_agent.write_bytes(librarian_agent_bytes)
        explorer_agent = codex_agents / "explorer.toml"
        explorer_agent_bytes = b'name = "user-explorer"\neffort = "user-choice"\n'
        explorer_agent.write_bytes(explorer_agent_bytes)
        elsewhere = root / "elsewhere.toml"
        elsewhere.write_bytes(b'name = "old-superwiki"\n')
        retired_link = codex_agents / "superwiki-initializer.toml"
        retired_link.symlink_to(elsewhere)
        retired_target = os.readlink(retired_link)

        # A real file where a helper link used to go is likewise untouched.
        claude_agents = home / ".claude" / "agents"
        claude_agents.mkdir(parents=True)
        claude_agent = claude_agents / "superwiki-initializer.md"
        claude_bytes = b"---\nname: user-owned\n---\n"
        claude_agent.write_bytes(claude_bytes)

        proc = self.run_script(dist / "skills.sh", cwd=root, home=home)

        self.assertEqual(proc.returncode, 0, proc.stderr)

        # The stale definitions in the distribution are never consumed.
        for name, content in legacy_bytes.items():
            self.assertEqual((legacy_agents / name).read_bytes(), content)

        self.assertFalse(foreign_agent.is_symlink())
        self.assertEqual(foreign_agent.read_bytes(), foreign_bytes)
        self.assertFalse(librarian_agent.is_symlink())
        self.assertEqual(librarian_agent.read_bytes(), librarian_agent_bytes)
        self.assertFalse(explorer_agent.is_symlink())
        self.assertEqual(explorer_agent.read_bytes(), explorer_agent_bytes)
        self.assertTrue(retired_link.is_symlink())
        self.assertEqual(os.readlink(retired_link), retired_target)
        self.assertEqual(elsewhere.read_bytes(), b'name = "old-superwiki"\n')
        self.assertFalse(claude_agent.is_symlink())
        self.assertEqual(claude_agent.read_bytes(), claude_bytes)

        # Existing agent dirs gain no new entries; absent ones stay absent.
        self.assertEqual(
            sorted(path.name for path in codex_agents.iterdir()),
            [
                "explorer.toml",
                "librarian.toml",
                "memory-librarian.toml",
                "superwiki-initializer.toml",
            ],
        )
        self.assertEqual(
            sorted(path.name for path in claude_agents.iterdir()),
            ["superwiki-initializer.md"],
        )
        for absent_agents_dir in (
            home / ".config" / "opencode" / "agents",
            home / ".cursor" / "agents",
        ):
            self.assertFalse(absent_agents_dir.exists())

        # The skill link is still installed, but only in the agent-compatible
        # global skill dir; other runtime skill dirs are not created.
        agents_skills = home / ".agents" / "skills"
        self.assert_link_to(agents_skills / "superwiki", dist)
        self.assertEqual(
            sorted(path.name for path in agents_skills.iterdir()), ["superwiki"]
        )
        for skills_dir in OTHER_GLOBAL_SKILL_DIRS:
            self.assertFalse(
                os.path.lexists(home / skills_dir),
                f"{skills_dir} must not be created by skills.sh",
            )


if __name__ == "__main__":
    unittest.main()
