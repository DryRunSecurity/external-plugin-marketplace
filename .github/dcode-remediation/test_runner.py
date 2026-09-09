import asyncio
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import tomllib
import unittest
from unittest.mock import patch

import runner


spec = importlib.util.spec_from_file_location("static_policy", Path(__file__).with_name("sitecustomize.py"))
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)
ONE = "11111111-1111-1111-1111-111111111111"
TWO = "abcdefab-2222-2222-2222-222222222222"
ACCOUNT = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
REPO = "example-org/example-repo"


def comment():
    return {"id": 42, "updated_at": "2026-01-01T00:00:00Z", "body": "Finding",
            "issue_url": "https://api.github.com/repos/example-org/example-repo/issues/7",
            "user": {"id": runner.BOT_ID, "login": "dryrunsecurity[bot]", "type": "Bot"}}


def context():
    return {"kind": "comment", "repository": REPO, "repository_id": 123, "sha": "a" * 40,
            "pr_number": 7, "comment_id": 42, "version": runner.comment_version(comment(), "a" * 40)}


def changes():
    return [{"path": "app/test.rb", "before": "old\n", "after": "new\n"}]


class NpmCompletionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for directory in ("original", "source"):
            target = self.root / directory
            target.mkdir()
            runner.save(target / "package.json", {"dependencies": {"next": "15.1.6", "react": "^19.0.0"}})
            runner.save(target / "package-lock.json", {"lockfileVersion": 3})
        self.source = self.root / "source"
        manifest = runner.load(self.source / "package.json")
        manifest["dependencies"]["next"] = "15.5.16"
        runner.save(self.source / "package.json", manifest)
        runner.save(self.root / "context.json", context())

    @patch("runner.subprocess.run")
    def test_report_only_skips_npm_without_changing_existing_lock(self, run):
        runner.save(self.root / "context.json", dict(context(), explanation_head="existing-head"))
        runner.save(self.source / "package-lock.json", {"lockfileVersion": 3, "version": "existing"})
        before = runner.snapshot(self.source)
        runner.complete_npm(self.root)
        run.assert_not_called()
        self.assertEqual(runner.snapshot(self.source), before)
        self.assertFalse((self.root / "npm-completed").exists())

    @patch("runner.subprocess.run")
    def test_skip_unchanged_or_absent_manifest(self, run):
        original = self.root / "original/package.json"
        (self.source / "package.json").write_bytes(original.read_bytes())
        runner.complete_npm(self.root)
        original.unlink()
        (self.source / "package.json").unlink()
        runner.complete_npm(self.root)
        run.assert_not_called()

    def test_isolated_command_and_output_copy(self):
        for name in (".npmrc", ".env", "credentials.json", "app.js"):
            (self.source / name).write_text("must not be copied")
        manifest = (self.source / "package.json").read_bytes()
        generated_lock = {"lockfileVersion": 3, "packages": {"node_modules/next": {"version": "15.5.16"}}}

        def run(command, **kwargs):
            mount = command[command.index("--mount") + 1]
            work = Path(mount.removeprefix("type=bind,src=").removesuffix(",dst=/work"))
            self.assertNotEqual(work, self.source)
            self.assertEqual({item.name for item in work.iterdir()}, {"package.json", "package-lock.json"})
            self.assertEqual((work / "package.json").read_bytes(), manifest)
            self.assertEqual((work / "package-lock.json").read_bytes(), (self.root / "original/package-lock.json").read_bytes())
            self.assertEqual(command, [
                "docker", "run", "--rm", "--read-only", "--cap-drop=ALL", "--security-opt=no-new-privileges",
                "--user", f"{os.getuid()}:{os.getgid()}", "--tmpfs", "/tmp:rw,nosuid,size=512m,mode=1777",
                "--mount", f"type=bind,src={work},dst=/work", "--workdir", "/work", "--env", "HOME=/tmp",
                "node:22-bookworm-slim", "npm", "install", "--package-lock-only", "--ignore-scripts",
                "--no-audit", "--no-fund"])
            self.assertEqual(kwargs, {"env": {"PATH": "/usr/bin", "HOME": "/home/test"},
                                      "check": True, "capture_output": True, "text": True, "timeout": 300})
            runner.save(work / "package-lock.json", generated_lock)
            (work / "node_modules").mkdir()

        with patch.dict(os.environ, {"PATH": "/usr/bin", "HOME": "/home/test", "GH_TOKEN": "fake-gh",
                                     "MODEL_API_KEY": "fake-model", "DRYRUN_API_KEY": "fake-dryrun"}, clear=True):
            with patch("runner.subprocess.run", side_effect=run) as mocked:
                runner.complete_npm(self.root)
                mocked.assert_called_once()
        self.assertEqual(runner.load(self.source / "package-lock.json"), generated_lock)
        self.assertEqual((self.source / "package.json").read_bytes(), manifest)
        self.assertFalse((self.source / "node_modules").exists())
        self.assertEqual(runner.load(self.root / "original/package-lock.json"), {"lockfileVersion": 3})

    @patch("runner.subprocess.run")
    def test_reject_unsupported_package_managers_and_workspaces(self, run):
        manifest = runner.load(self.source / "package.json")
        for field, value in (("packageManager", "pnpm@10.0.0"), ("packageManager", "yarn@4.0.0"),
                             ("workspaces", ["packages/*"])):
            with self.subTest(field=field, value=value):
                runner.save(self.source / "package.json", dict(manifest, **{field: value}))
                with self.assertRaisesRegex(ValueError, "only a root npm"):
                    runner.complete_npm(self.root)
        runner.save(self.source / "package.json", manifest)
        for name in ("yarn.lock", "pnpm-lock.yaml", "bun.lock", "bun.lockb", "npm-shrinkwrap.json"):
            path = self.root / "original" / name
            path.write_text("unsupported")
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "only a root npm"):
                runner.complete_npm(self.root)
            path.unlink()
        run.assert_not_called()

    @patch("runner.subprocess.run")
    def test_reject_missing_original_or_agent_edited_lock(self, run):
        (self.source / "package-lock.json").write_text("{}")
        with self.assertRaisesRegex(ValueError, "untouched"):
            runner.complete_npm(self.root)
        (self.root / "original/package-lock.json").unlink()
        with self.assertRaisesRegex(ValueError, "original package-lock.json"):
            runner.complete_npm(self.root)
        run.assert_not_called()

    def test_npm_failure_does_not_copy_output(self):
        before = (self.source / "package-lock.json").read_bytes()
        with patch("runner.subprocess.run", side_effect=subprocess.CalledProcessError(1, ["docker"])):
            with self.assertRaises(subprocess.CalledProcessError):
                runner.complete_npm(self.root)
        self.assertEqual((self.source / "package-lock.json").read_bytes(), before)
        self.assertFalse((self.root / "npm-completed").exists())

    def test_report_covers_external_lockfile_and_records_actual_completion(self):
        def run(command, **kwargs):
            mount = command[command.index("--mount") + 1]
            work = Path(mount.removeprefix("type=bind,src=").removesuffix(",dst=/work"))
            runner.save(work / "package-lock.json", {"lockfileVersion": 3, "packages": {"node_modules/next": {"version": "15.5.16"}}})
        with patch("runner.subprocess.run", side_effect=run):
            runner.complete_npm(self.root)
        self.assertTrue((self.root / "npm-completed").is_file())
        runner.save(self.root / "context.json", context())
        explanation = {"summary": "Next 15.5.16 addresses the reported advisory. Tests were not run.",
                       "files": {"package.json": "Selects the fixed Next release instead of the vulnerable release."}}
        runner.save(self.root / "agent-output.txt", explanation)
        with self.assertRaisesRegex(ValueError, "changed paths"):
            runner.bundle(self.root)
        explanation["files"]["package-lock.json"] = "The external npm step will lock the fixed Next release and its integrity metadata."
        runner.save(self.root / "agent-output.txt", explanation)
        runner.bundle(self.root)
        completed = runner.load(self.root / "artifact/report.json")
        self.assertIn("Trusted post-agent npm completion", completed["summary"])
        self.assertIn("The agent did not run npm", completed["summary"])
        self.assertIn("not an application test", completed["summary"])
        self.assertEqual(completed["files"], explanation["files"])

    def test_lockfile_sized_proposal_is_bounded(self):
        runner.validate_changes([{"path": "package-lock.json", "before": "a" * 400_000, "after": "b" * 400_000}])
        with self.assertRaises(ValueError):
            runner.validate_changes([{"path": "package-lock.json", "before": "a" * 600_000, "after": "b" * 600_000}])


class ExplanationRefreshTests(unittest.TestCase):
    def test_prepare_uses_existing_head_read_only_or_preserves_new_run(self):
        version = runner.digest(json.dumps([ACCOUNT, [ONE], "a" * 40]))
        branch = "dryrun/remediate-" + version[:16]
        for scenario in ("existing", "new", "foreign"):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                runner.save(root / "event.json", {})
                pr = {"number": 8, "state": "open", "user": {"login": "human" if scenario == "foreign" else "github-actions[bot]"},
                      "base": {"ref": "main", "sha": "a" * 40},
                      "head": {"ref": branch, "sha": "b" * 40, "repo": {"id": 123}},
                      "body": f"<!-- dryrun-dcode:findings:{version} -->"}
                def gh(path, **kwargs):
                    if path == f"repos/{REPO}":
                        return {"id": 123, "default_branch": "main"}
                    if path.endswith("/permission"):
                        return {"permission": "write"}
                    if "/branches/" in path:
                        return {"commit": {"sha": "a" * 40}}
                    if "/pulls?" in path:
                        return [] if scenario == "new" else [pr]
                    self.assertTrue(path.endswith("/pulls/8"))
                    return pr
                def archive(repo, sha, target):
                    (target / "app").mkdir(parents=True)
                    (target / "app/test.rb").write_text("new\n" if sha == "b" * 40 else "before-image-not-for-prompt\n")
                    (target / "keep.rb").write_text("unchanged\n")
                finding = {"id": ONE, "account_id": ACCOUNT, "provider_repo_id": 123, "finding_type": "deepscan"}
                env = {"GITHUB_REPOSITORY": REPO, "GITHUB_ACTOR": "writer", "GITHUB_EVENT_NAME": "workflow_dispatch",
                       "GITHUB_EVENT_PATH": str(root / "event.json"), "GITHUB_OUTPUT": str(root / "output"),
                       "SKILLS_ROOT": str(root / "skills"), "INPUTS_JSON": json.dumps({"finding_id": ONE, "account_id": ACCOUNT})}
                with patch.dict(os.environ, env), patch.object(runner, "gh", side_effect=gh), patch.object(runner, "source_archive", side_effect=archive) as archives, patch.object(runner.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, json.dumps({"data": finding}))):
                    if scenario == "foreign":
                        with self.assertRaisesRegex(ValueError, "does not match"):
                            runner.prepare("findings", root)
                        archives.assert_not_called()
                        continue
                    runner.prepare("findings", root)
                ctx = runner.load(root / "context.json")
                prompt = (root / "prompt.txt").read_text()
                self.assertNotIn("before-image-not-for-prompt", prompt)
                if scenario == "existing":
                    self.assertEqual([call.args[1] for call in archives.call_args_list], ["a" * 40, "b" * 40])
                    self.assertEqual((ctx["explanation_pr"], ctx["explanation_head"]), (8, "b" * 40))
                    self.assertEqual((root / "source/app/test.rb").read_text(), "new\n")
                    self.assertIn("DO NOT edit source files", prompt)
                    self.assertIn("immutable head " + "b" * 40, prompt)
                    self.assertIn('Use exactly these changed repository-relative paths in files: ["app/test.rb"]', prompt)
                    self.assertNotIn("Edit the actual source files", prompt)
                    self.assertIn("No npm completion runs in report-only mode", prompt)
                    self.assertNotIn("publication requires that step to succeed", prompt)
                else:
                    self.assertNotIn("explanation_head", ctx)
                    self.assertEqual(archives.call_count, 1)
                    self.assertEqual(runner.snapshot(root / "source"), runner.snapshot(root / "original"))
                    self.assertIn("Edit the actual source files", prompt)
                    self.assertIn("publication requires that step to succeed", prompt)

    def test_model_source_mount_is_read_only_only_for_report_refresh(self):
        for refresh in (False, True):
            with self.subTest(refresh=refresh), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                ctx = {"key_env": "OPENAI_API_KEY"}
                if refresh:
                    ctx["explanation_head"] = "existing-head"
                runner.save(root / "context.json", ctx)
                with patch.dict(os.environ, {"MODEL_API_KEY": "test-key", "SKILLS_ROOT": temporary}), patch.object(runner.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "report", "")) as run:
                    runner.run_agent(root)
                mounts = [item for item in run.call_args.args[0] if item.startswith("type=bind,")]
                source = next(item for item in mounts if ",dst=/work" in item)
                self.assertEqual(source.endswith(",readonly"), refresh)

    def test_report_only_publication_cannot_create_or_retarget_pr(self):
        ctx = {"kind": "findings", "repository": REPO, "sha": "a" * 40, "version": "v" * 64,
               "base_branch": "main", "finding_ids": [ONE], "explanation_pr": 8, "explanation_head": "head"}
        for scenario in ("missing", "changed", "replaced", "closed"):
            pr = {"number": 9 if scenario == "replaced" else 8, "state": "closed" if scenario == "closed" else "open",
                  "base": {"ref": "main"}, "head": {"sha": "changed" if scenario == "changed" else "head"},
                  "body": f"<!-- dryrun-dcode:findings:{ctx['version']} -->"}
            with self.subTest(scenario=scenario), patch.object(runner, "verify_publication", return_value=(ctx, changes())), patch.object(runner, "read_report", return_value=report()), patch.object(runner, "gh") as gh:
                gh.side_effect = [[]] if scenario == "missing" else [[pr], pr]
                with self.assertRaises(ValueError):
                    runner.publish_findings(Path("/unused"))
                self.assertTrue(all(len(call.args) == 1 for call in gh.call_args_list))

    def test_report_only_freshness_rechecks_head_before_writes(self):
        ctx = {"kind": "findings", "repository": REPO, "sha": "base", "base_branch": "main",
               "explanation_pr": 8, "explanation_head": "head"}
        for field, value in (("head", {"sha": "changed"}), ("state", "closed"), ("base", {"ref": "other"})):
            pr = {"state": "open", "head": {"sha": "head"}, "base": {"ref": "main"}, field: value}
            with self.subTest(field=field), patch.object(runner, "gh", side_effect=[{"commit": {"sha": "base"}}, pr]) as gh:
                with self.assertRaisesRegex(ValueError, "changed during explanation refresh"):
                    runner.recheck_source(ctx)
                self.assertTrue(all(len(call.args) == 1 for call in gh.call_args_list))


class ParsingTests(unittest.TestCase):
    def test_single_multiple_and_dedup(self):
        self.assertEqual(runner.select_ids({"finding_id": ONE}), [ONE])
        self.assertEqual(runner.select_ids({"finding_ids": ONE + ", " + TWO.upper() + "\n" + ONE}), [ONE, TWO])

    def test_invalid_or_conflicting_sources(self):
        for inputs in ({}, {"finding_id": ONE, "issue_number": "1"},
                       {"finding_id": ONE + "," + TWO}, {"finding_ids": ONE + ",not-a-uuid"}):
            with self.subTest(inputs=inputs), self.assertRaises(ValueError):
                runner.select_ids(inputs)
        with self.assertRaises(ValueError):
            runner.ids_from_text("\n".join(f"{i:08x}-1111-1111-1111-111111111111" for i in range(21)))

    def test_issue_heading_and_links(self):
        body = f"## DryRun finding IDs\n- {ONE}\n- {TWO}\n## Other\nnot an ID"
        self.assertEqual(runner.select_ids({"issue_number": "1"}, body), [ONE, TWO])
        body = f"[finding](https://app.dryrun.security/risk-register?finding={ONE})\nhttps://app.sb.dryrun.security/risk-register?finding={TWO}"
        self.assertEqual(runner.issue_ids(body), [ONE, TWO])
        for body in (ONE, f"https://evil.example/risk-register?finding={ONE}",
                     f"https://app.dryrun.security.evil.example/risk-register?finding={ONE}"):
            with self.assertRaises(ValueError):
                runner.issue_ids(body)

    def test_finding_identity_and_foreign_repository(self):
        finding = {"id": ONE, "account_id": ACCOUNT, "provider_repo_id": "123", "finding_type": "sca"}
        runner.validate_finding(finding, ONE, ACCOUNT, 123)
        for field, value in (("id", TWO), ("account_id", ONE), ("provider_repo_id", 456), ("finding_type", "code_policy")):
            with self.subTest(field=field), self.assertRaises(ValueError):
                runner.validate_finding(dict(finding, **{field: value}), ONE, ACCOUNT, 123)

    def test_inputs_only_come_from_workflow_environment(self):
        inputs = {"pr_number": 7, "provider": "anthropic", "model": "selected-model"}
        for name in ("pull_request", "workflow_dispatch", "workflow_call", "issues", "issue_comment"):
            with self.subTest(event=name), patch.dict(os.environ, {"GITHUB_EVENT_NAME": name, "INPUTS_JSON": json.dumps(inputs)}):
                self.assertEqual(runner.workflow_inputs(), inputs)
        for raw in ("[]", "null", '"text"', "not JSON"):
            with patch.dict(os.environ, {"INPUTS_JSON": raw}), self.assertRaises(ValueError):
                runner.workflow_inputs()


class TriggerTests(unittest.TestCase):
    def test_explicit_events_and_findings_issue_comments_require_writer(self):
        event = {"action": "created", "issue": {"number": 7, "pull_request": {}}, "comment": comment()}
        for name in ("pull_request", "workflow_dispatch", "workflow_call", "issues", "issue_comment"):
            for kind in ("comment", "findings"):
                if name == "issue_comment" and kind == "comment":
                    continue
                for permission in ("read", "triage", "none", "write", "maintain", "admin"):
                    env = {"GITHUB_REPOSITORY": REPO, "GITHUB_EVENT_NAME": name, "GITHUB_ACTOR": "example-writer"}
                    with self.subTest(event=name, kind=kind, permission=permission), patch.dict(os.environ, env), patch.object(runner, "gh", return_value={"permission": permission}) as gh:
                        if permission in {"write", "maintain", "admin"}:
                            self.assertFalse(runner.authorize_trigger(event, kind))
                        else:
                            with self.assertRaisesRegex(ValueError, "repository writer"):
                                runner.authorize_trigger(event, kind)
                        gh.assert_called_once_with(f"repos/{REPO}/collaborators/example-writer/permission")

    def test_only_verified_new_or_edited_pr_bot_comments_bypass_writer(self):
        event = {"action": "created", "issue": {"number": 7, "pull_request": {}}, "comment": comment()}
        env = {"GITHUB_REPOSITORY": REPO, "GITHUB_EVENT_NAME": "issue_comment", "GITHUB_ACTOR": "example-reader"}
        with patch.dict(os.environ, env), patch.object(runner, "gh", return_value={"permission": "read"}) as gh:
            for action in ("created", "edited"):
                self.assertTrue(runner.authorize_trigger(dict(event, action=action), "comment"))
            gh.assert_not_called()
            invalid = [dict(event, action="deleted"), dict(event, issue={"number": 7})]
            for field, value in (("id", 99), ("login", "lookalike[bot]"), ("type", "User")):
                invalid.append(dict(event, comment=dict(comment(), user=dict(comment()["user"], **{field: value}))))
            for changed in invalid:
                with self.subTest(event=changed), self.assertRaisesRegex(ValueError, "repository writer"):
                    runner.authorize_trigger(changed, "comment")

    def test_prepare_comment_uses_trusted_inputs_not_pr_body(self):
        for name in ("pull_request", "workflow_dispatch", "workflow_call", "issues", "issue_comment"):
            with self.subTest(event=name), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                event = {"pull_request": {"number": 99, "body": json.dumps({"provider": "openai", "model": "untrusted",
                                                                                 "base_url": "https://untrusted.example"})}}
                runner.save(root / "event.json", event)
                inputs = {"pr_number": 7, "comment_id": 42, "provider": "anthropic", "model": "trusted-model"}
                env = {"GITHUB_REPOSITORY": REPO, "GITHUB_EVENT_NAME": name, "GITHUB_ACTOR": "example-writer",
                       "GITHUB_EVENT_PATH": str(root / "event.json"), "GITHUB_OUTPUT": str(root / "output"),
                       "INPUTS_JSON": json.dumps(inputs)}
                def gh(path, **kwargs):
                    if path == f"repos/{REPO}":
                        return {"id": 123}
                    if path.endswith("/permission"):
                        return {"permission": "write"}
                    if path.endswith("/pulls/7"):
                        return {"state": "open", "head": {"sha": "a" * 40, "repo": {"id": 123}}, "base": {"ref": "main"}}
                    self.assertTrue(path.endswith("/issues/comments/42"))
                    return comment()
                def archive(repo, sha, target):
                    target.mkdir()
                    (target / "query.rb").write_text("source\n")
                with patch.dict(os.environ, env), patch.object(runner, "gh", side_effect=gh), patch.object(runner, "source_archive", side_effect=archive):
                    runner.prepare("comment", root)
                ctx = runner.load(root / "context.json")
                self.assertEqual((ctx["pr_number"], ctx["model"], ctx["key_env"]), (7, "anthropic:trusted-model", "ANTHROPIC_API_KEY"))
                self.assertNotIn("untrusted", (root / "config.toml").read_text())
                self.assertIn("adapter-provided quoting or a query builder", (root / "prompt.txt").read_text())

    def test_prepare_findings_on_issue_comment_rejects_nonwriter_before_api(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            runner.save(root / "event.json", {"action": "created", "issue": {"number": 7, "pull_request": {}}, "comment": comment()})
            env = {"GITHUB_REPOSITORY": REPO, "GITHUB_EVENT_NAME": "issue_comment", "GITHUB_ACTOR": "example-reader",
                   "GITHUB_EVENT_PATH": str(root / "event.json"), "INPUTS_JSON": json.dumps({"finding_id": ONE})}
            with patch.dict(os.environ, env), patch.object(runner, "gh", side_effect=[{"id": 123}, {"permission": "read"}]), patch.object(runner.subprocess, "run") as run:
                with self.assertRaisesRegex(ValueError, "repository writer"):
                    runner.prepare("findings", root)
                run.assert_not_called()


class ProviderTests(unittest.TestCase):
    def test_defaults_and_responses_configuration(self):
        model, key, raw = runner.provider_config({})
        config = tomllib.loads(raw)
        self.assertEqual(model, "openai:gpt-5.5")
        self.assertEqual(key, "OPENAI_API_KEY")
        self.assertNotIn("base_url", raw)
        self.assertNotIn("azure", raw.lower())
        self.assertTrue(config["models"]["providers"]["openai"]["params"]["use_responses_api"])
        self.assertFalse(config["interpreter"]["enable_interpreter"])
        self.assertFalse(config["startup"]["read_project_dotenv"])
        self.assertFalse(config["extensions"]["enabled"])
        self.assertFalse(config["plugins"]["auto_update"])
        self.assertNotIn("api_key =", raw)

    def test_native_providers_and_chat_completions(self):
        model, key, raw = runner.provider_config({"provider": "anthropic", "base_url": ""})
        self.assertEqual(model, "anthropic:claude-sonnet-4-5")
        self.assertEqual(key, "ANTHROPIC_API_KEY")
        self.assertNotIn("base_url", raw)
        self.assertNotIn("azure", raw.lower())
        self.assertNotIn("base_url", runner.provider_config({"provider": "openai", "base_url": ""})[2])
        config = tomllib.loads(runner.provider_config({"use_responses_api": False})[2])
        self.assertFalse(config["models"]["providers"]["openai"]["params"]["use_responses_api"])

    def test_gateway_overrides_and_no_cross_provider_fallback(self):
        for provider in ("openai", "anthropic"):
            with self.subTest(provider=provider):
                model, key, raw = runner.provider_config({"provider": provider, "model": "gateway-model",
                                                       "base_url": "https://gateway.example/v1/"})
                self.assertEqual(model, provider + ":gateway-model")
                self.assertEqual(key, provider.upper() + "_API_KEY")
                providers = tomllib.loads(raw)["models"]["providers"]
                self.assertEqual(set(providers), {provider})
                self.assertEqual(providers[provider]["base_url"], "https://gateway.example/v1")
                self.assertEqual("params" in providers[provider], provider == "openai")

    def test_bad_configuration(self):
        for inputs in ({"provider": "other"}, {"provider": "openai-compatible"}, {"provider": "bedrock"},
                       {"model": "x\ny"}, {"model": "x\ry"}, {"model": " "}, {"model": 42},
                       {"use_responses_api": "maybe"}):
            with self.subTest(inputs=inputs), self.assertRaises(ValueError):
                runner.provider_config(inputs)
        for base in ("http://localhost", "file:///tmp/model", "https:///v1", "https://user:pass@example.com",
                     "https://@example.com", "https://example.com?key=secret", "https://example.com#fragment",
                     "https://example.com\n/evil", "https://example.com\\evil", "https://example.com:bad", 42):
            for provider in ("openai", "anthropic"):
                with self.subTest(provider=provider, base=base), self.assertRaises(ValueError):
                    runner.provider_config({"provider": provider, "base_url": base})


    def test_model_key_is_required_selected_and_redacted(self):
        for provider in ("openai", "anthropic"):
            with self.subTest(provider=provider), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                key_env = provider.upper() + "_API_KEY"
                runner.save(root / "context.json", {"key_env": key_env})
                env = {"MODEL_API_KEY": "explicit-test-key", "SKILLS_ROOT": temporary,
                       "OPENAI_API_KEY": "inherited-openai", "ANTHROPIC_API_KEY": "inherited-anthropic",
                       "GH_TOKEN": "test-gh", "DRYRUN_API_KEY": "test-dryrun"}
                with patch.dict(os.environ, env, clear=True), patch.object(runner.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "explicit-test-key", "")) as run:
                    runner.run_agent(root)
                    command = run.call_args.args[0]
                    self.assertEqual([command[i + 1] for i, value in enumerate(command) if value == "-e"], [key_env])
                    self.assertIn("dcode-remediation:0.1.66", command)
                    self.assertEqual(run.call_args.kwargs["env"][key_env], "explicit-test-key")
                    self.assertEqual((root / "agent-output.txt").read_text(), "[REDACTED]")
                    for secret in env.values():
                        if secret != temporary:
                            self.assertNotIn(secret, command)
                    run.return_value = subprocess.CompletedProcess([], 1, "", "error: explicit-test-key")
                    with self.assertRaisesRegex(RuntimeError, r"error: \[REDACTED\]"):
                        runner.run_agent(root)
                    del os.environ["MODEL_API_KEY"]
                    run.reset_mock()
                    with self.assertRaisesRegex(ValueError, "Model API key secret is missing"):
                        runner.run_agent(root)
                    run.assert_not_called()


class SafetyTests(unittest.TestCase):
    def test_paths_and_patch_bounds(self):
        for path in ("../bad", "/bad", "a/../b", "a//b", ".", ".github/test.yml", "lib/AGENTS.md", ".env.local", "a\\b", "a\nb"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                runner.safe_path(path)
        self.assertEqual(str(runner.safe_path("app/new.rb")), "app/new.rb")
        for items in ([], changes() * 2, [{"path": "x", "before": "a", "after": "a"}],
                      [{"path": "x", "before": None, "after": "\x00"}],
                      [{"path": "x", "before": None, "after": "x" * (runner.MAX_PATCH + 1)}]):
            with self.assertRaises(ValueError):
                runner.validate_changes(items)

    def test_empty_file_creation_and_deletion_fail_closed(self):
        for before, after in ((None, ""), ("", None)):
            item = {"path": "empty.txt", "before": before, "after": after}
            for items in ([item], changes() + [item]):
                with self.subTest(before=before, mixed=len(items) > 1):
                    with self.assertRaisesRegex(ValueError, "Empty-file creation and deletion"):
                        runner.validate_changes(items)
                    with self.assertRaisesRegex(ValueError, "Empty-file creation and deletion"):
                        runner.patch_text(items)
        for before, after in (("", "text\n"), ("text\n", "")):
            self.assertIn("empty.txt", runner.patch_text([{"path": "empty.txt", "before": before, "after": after}]))

    def test_patch_new_deleted_and_no_newline(self):
        items = changes() + [{"path": "new.rb", "before": None, "after": "hello"},
                             {"path": "deleted.rb", "before": "bye\n", "after": None}]
        text = runner.patch_text(items)
        self.assertIn("--- /dev/null\n+++ b/new.rb", text)
        self.assertIn("--- a/deleted.rb\n+++ /dev/null", text)
        self.assertIn("\\ No newline at end of file", text)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for item in items:
                if item["before"] is not None:
                    target = root / item["path"]
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(item["before"])
            subprocess.run(["git", "apply", "--check", "-"], cwd=root, input=text, text=True, check=True, capture_output=True)

    def test_snapshot_preserves_crlf_and_rejects_symlinks(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "file").write_bytes(b"a\r\nb\r\n")
            self.assertEqual(runner.snapshot(root)["file"], "a\r\nb\r\n")
            (root / "link").symlink_to(root / "file")
            with self.assertRaises(ValueError):
                runner.snapshot(root)

    def test_archive_drops_instructions_links_and_traversal(self):
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode="w:gz") as archive:
            for name in ("root/app/a.rb", "root/../escape", "root/.github/test.yml", "root/AGENTS.md", "root/.env"):
                info = tarfile.TarInfo(name)
                info.size = 1
                archive.addfile(info, io.BytesIO(b"x"))
            link = tarfile.TarInfo("root/link")
            link.type, link.linkname = tarfile.SYMTYPE, "/etc/passwd"
            archive.addfile(link)
        with tempfile.TemporaryDirectory() as temporary, patch.object(runner.subprocess, "run") as run:
            run.return_value.stdout = stream.getvalue()
            runner.source_archive(REPO, "sha", Path(temporary))
            self.assertEqual(runner.snapshot(Path(temporary)), {"app/a.rb": "x"})

    def test_static_tool_policy(self):
        for name in ("execute", "js_eval", "task", "fetch_url", "web_search", "delete", "unknown"):
            self.assertFalse(policy.permitted({"name": name, "args": {}}))
        for path in ("/proc/self/environ", "/input/context.json", "/tmp/dcode-home/.deepagents/config.toml", "/work/../etc/passwd", "/work/.env"):
            self.assertFalse(policy.permitted({"name": "read_file", "args": {"file_path": path}}))
        self.assertTrue(policy.permitted({"name": "edit_file", "args": {"file_path": "/work/app/a.rb"}}))
        skill = str(policy.SKILLS / "remediation/SKILL.md")
        self.assertTrue(policy.permitted({"name": "read_file", "args": {"file_path": skill}}))
        self.assertFalse(policy.permitted({"name": "write_file", "args": {"file_path": skill}}))
        self.assertFalse(policy.permitted({"name": "glob", "args": {"path": "/work", "pattern": "../**"}}))

    def test_runtime_policy_sync_and_async(self):
        try:
            from langchain_core.messages import AIMessage
            from langchain_core.tools import StructuredTool
            from langgraph.prebuilt import ToolNode
            from importlib.metadata import version
            runtime_version = version("langgraph-prebuilt")
        except ImportError:
            self.skipTest("Pinned dcode runtime is tested in the Docker build")
        if runtime_version != "1.1.0":
            self.skipTest("Pinned dcode runtime is tested in the Docker build")
        sync, asynchronous = ToolNode._execute_tool_sync, ToolNode._execute_tool_async
        try:
            policy.install()
            def tool(file_path: str = "") -> str:
                return "executed"
            from langgraph.graph import StateGraph, MessagesState
            builder = StateGraph(MessagesState)
            builder.add_node("tools", ToolNode([StructuredTool.from_function(tool, name=name, description="test") for name in ("execute", "read_file")]))
            builder.set_entry_point("tools")
            builder.set_finish_point("tools")
            graph = builder.compile()
            for name, path, expected in (("execute", "", "error"), ("read_file", "/proc/self/environ", "error"), ("read_file", "/work/a.rb", "success")):
                request = {"messages": [AIMessage(content="", tool_calls=[{"name": name, "args": {"file_path": path}, "id": "test"}])]}
                self.assertEqual(graph.invoke(request)["messages"][-1].status, expected)
                self.assertEqual(asyncio.run(graph.ainvoke(request))["messages"][-1].status, expected)
        finally:
            ToolNode._execute_tool_sync, ToolNode._execute_tool_async = sync, asynchronous


def report():
    return {"summary": f"### {ONE}: Unsafe query\n\nUntrusted input could change query structure. "
            "The changed query treats input as data, preventing the reported injection. Tests were not run. "
            "Exercise malicious input and normal requests before merging.",
            "files": {"app/test.rb": "The query now quotes the untrusted value so it cannot terminate the SQL literal. "
                      "This removes the input-to-query-structure path reported by DryRun."}}


class ReportTests(unittest.TestCase):
    def test_raw_and_fenced_json(self):
        raw = json.dumps(report())
        for text in (raw, "\n```json\n" + raw + "\n```\n", "```\n" + raw + "\n```"):
            self.assertEqual(runner.parse_report(text, changes()), report())

    def test_reject_invalid_missing_oversized_or_unsafe_explanations(self):
        for value in (None, [], {}, {"summary": "x"}, dict(report(), files={}),
                      dict(report(), extra="x"), dict(report(), summary=" "), dict(report(), summary=[]),
                      dict(report(), summary="é" * 10001), dict(report(), files={"app/test.rb": "x" * 8001}),
                      dict(report(), files={"app/test.rb": ""}), dict(report(), files={"other.rb": "reason"}),
                      dict(report(), summary="```suggestion\nx\n```"), dict(report(), summary="<!-- marker -->")):
            with self.subTest(value=type(value)), self.assertRaises(ValueError):
                runner.parse_report(json.dumps(value), changes())
        for text in ("", "not JSON", "Explanation: " + json.dumps(report()), " " * (runner.MAX_REPORT * 6 + 1)):
            with self.assertRaises(ValueError):
                runner.parse_report(text, changes())
        many = [dict(changes()[0], path=f"app/{i}.rb") for i in range(6)]
        with self.assertRaisesRegex(ValueError, "oversized"):
            runner.validate_report({"summary": "reason", "files": {item["path"]: "x" * 7999 for item in many}}, many)
        with tempfile.TemporaryDirectory() as temporary, self.assertRaises(FileNotFoundError):
            runner.read_report(Path(temporary), changes())

    def test_bundle_saves_validated_report_outside_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for directory, text in (("original", "old\n"), ("source", "new\n")):
                (root / directory / "app").mkdir(parents=True)
                (root / directory / "app/test.rb").write_text(text)
            runner.save(root / "context.json", context())
            (root / "agent-output.txt").write_text("No structured explanation")
            with self.assertRaises(ValueError):
                runner.bundle(root)
            self.assertFalse((root / "artifact").exists())
            runner.save(root / "agent-output.txt", report())
            runner.bundle(root)
            self.assertEqual(runner.read_report(root / "artifact", changes()), report())
            self.assertEqual(runner.snapshot(root / "source"), {"app/test.rb": "new\n"})
            self.assertTrue((root / "artifact/fix.patch").is_file())
            self.assertTrue((root / "artifact/agent-output.txt").is_file())

    def test_body_limit_counts_utf8_without_truncating(self):
        self.assertEqual(runner.bounded_body("é" * 30000), "é" * 30000)
        with self.assertRaises(ValueError):
            runner.bounded_body("é" * 30001)


class PublicationTests(unittest.TestCase):
    def setUp(self):
        reports = patch.object(runner, "read_report", return_value=report())
        reports.start()
        self.addCleanup(reports.stop)
        env = patch.dict(os.environ, {"GITHUB_RUN_ID": "1"})
        env.start()
        self.addCleanup(env.stop)

    def test_invalid_report_prevents_publication(self):
        for kind in ("comment", "findings"):
            with self.subTest(kind=kind), patch.object(runner, "verify_publication", return_value=(context(), changes())), patch.object(runner, "read_report", side_effect=ValueError("invalid report")), patch.object(runner, "gh") as gh:
                with self.assertRaisesRegex(ValueError, "invalid report"):
                    getattr(runner, "publish_" + kind)(Path("/unused"))
                gh.assert_not_called()

    def test_github_failure_diagnostic_redacts_tokens(self):
        error = subprocess.CalledProcessError(1, "gh", stderr="PR creation denied (HTTP 403); fake-token")
        with patch.dict(os.environ, {"GH_TOKEN": "fake-token"}), patch.object(runner.subprocess, "run", side_effect=error), patch("builtins.print") as output:
            with self.assertRaises(subprocess.CalledProcessError):
                runner.gh(f"repos/{REPO}/pulls", "POST", {})
        self.assertIn("PR creation denied (HTTP 403)", output.call_args.args[0])
        self.assertNotIn("fake-token", output.call_args.args[0])

    def test_exact_bot_identity_and_stale_version(self):
        pr = {"state": "open", "head": {"sha": "a" * 40, "repo": {"id": 123}}}
        self.assertTrue(runner.current_comment(context(), pr, comment()))
        for field, value in (("id", 99), ("login", "dryrunsecurity-fake[bot]"), ("type", "User")):
            changed = comment()
            changed["user"][field] = value
            self.assertFalse(runner.bot_comment(changed))
        changed = comment()
        changed["body"] += "edited"
        self.assertFalse(runner.current_comment(context(), pr, changed))
        pr["head"]["sha"] = "b" * 40
        self.assertFalse(runner.current_comment(context(), pr, comment()))
        pr["head"].update(sha="a" * 40, repo={"id": 456})
        self.assertFalse(runner.current_comment(context(), pr, comment()))

    def test_suggestions_only_on_valid_diff_lines(self):
        files = [{"filename": "app/test.rb", "patch": "@@ -1 +1 @@\n-old\n+old"}]
        suggestion = runner.suggestions(changes(), files, "marker", report())[0]
        self.assertEqual((suggestion["path"], suggestion["line"], suggestion["side"]), ("app/test.rb", 1, "RIGHT"))
        self.assertIn("```suggestion\nnew\n```", suggestion["body"])
        self.assertIn(report()["files"]["app/test.rb"], suggestion["body"])
        self.assertEqual(suggestion["body"].count("```"), 2)
        self.assertEqual(runner.suggestions(changes(), [], "marker", report()), [])
        self.assertEqual(runner.suggestions([{"path": "new", "before": None, "after": "x"}], files, "marker", report()), [])
        unsafe = [dict(changes()[0], after="```\n")]
        self.assertEqual(runner.suggestions(unsafe, files, "marker", report()), [])
        other = dict(changes()[0], path="app/other.rb")
        separate = dict(report(), files=dict(report()["files"], **{"app/other.rb": "Rejects unauthorized access at the second entrypoint."}))
        inline = runner.suggestions(changes() + [other], files + [dict(files[0], filename=other["path"])], "marker", separate)
        self.assertNotIn("second entrypoint", inline[0]["body"])
        self.assertIn("second entrypoint", inline[1]["body"])
        self.assertNotIn("SQL literal", inline[1]["body"])

    def test_summary_upsert_ignores_spoofed_marker(self):
        marker = "<!-- marker -->"
        with patch.object(runner, "gh") as gh:
            gh.side_effect = [[{"id": 1, "user": {"login": "human"}, "body": marker},
                               {"id": 2, "user": {"login": "github-actions[bot]"}, "body": marker}], {}]
            runner.upsert(REPO, 7, marker, "new")
            self.assertEqual(gh.call_args.args, (f"repos/{REPO}/issues/comments/2", "PATCH", {"body": "new"}))

    def test_already_published_is_noop(self):
        ctx = context()
        body = f"<!-- dryrun-dcode:comment:42 -->\n<!-- version:{ctx['version']} -->\n{runner.REPORT_FORMAT}"
        with patch.object(runner, "verify_publication", return_value=(ctx, changes())), patch.object(runner, "gh") as gh:
            gh.return_value = [{"user": {"login": "github-actions[bot]"}, "body": body}]
            runner.publish_comment(Path("/unused"))
            self.assertEqual(gh.call_count, 1)

    def test_terse_comment_refreshes_once_with_inline_and_timeline_rationale(self):
        ctx = context()
        old_body = f"<!-- dryrun-dcode:comment:42 -->\n<!-- version:{ctx['version']} -->"
        bot = {"login": "github-actions[bot]"}
        timeline = [{"id": 2, "user": bot, "body": old_body}]
        inline = [{"id": 3, "user": bot, "body": old_body}]
        calls = []
        def gh(path, method="GET", data=None, pages=False):
            calls.append((path, method, data))
            if method == "GET":
                if "/issues/7/comments?" in path:
                    return list(timeline)
                if "/pulls/7/comments?" in path:
                    return list(inline)
                return [{"filename": "app/test.rb", "patch": "@@ -1 +1 @@\n-old\n+old"}]
            if method == "POST":
                self.assertTrue(path.endswith("/reviews"))
                inline.extend(dict(item, id=4, user=bot) for item in data["comments"])
            elif method == "DELETE":
                inline[:] = [item for item in inline if item["id"] != 3]
            elif method == "PATCH":
                self.assertTrue(path.endswith("/issues/comments/2"))
                timeline[0]["body"] = data["body"]
            return {}
        with patch.object(runner, "verify_publication", return_value=(ctx, changes())), patch.object(runner, "recheck_source"), patch.object(runner, "gh", side_effect=gh):
            runner.publish_comment(Path("/unused"))
            count = len(calls)
            runner.publish_comment(Path("/unused"))
        self.assertEqual(len(calls), count + 1)
        self.assertEqual((len(timeline), len(inline)), (1, 1))
        self.assertIn(report()["summary"], timeline[0]["body"])
        self.assertIn(report()["files"]["app/test.rb"], timeline[0]["body"])
        self.assertIn(report()["files"]["app/test.rb"], inline[0]["body"])
        self.assertIn("```suggestion\nnew\n```", inline[0]["body"])
        self.assertIn("No commits or pushes", timeline[0]["body"])
        self.assertIn("Complete proposed patch", timeline[0]["body"])

    def test_large_patch_falls_back_without_discarding_explanation(self):
        detailed = {"summary": "s" * 20000, "files": {"app/test.rb": "r" * 7900}}
        with patch.object(runner, "verify_publication", return_value=(context(), changes())), patch.object(runner, "read_report", return_value=detailed), patch.object(runner, "recheck_source"), patch.object(runner, "gh", return_value=[]), patch.object(runner, "patch_text", return_value="x" * 44000), patch.object(runner, "upsert") as publish:
            runner.publish_comment(Path("/unused"))
        body = publish.call_args.args[3]
        self.assertIn(detailed["summary"], body)
        self.assertIn(detailed["files"]["app/test.rb"], body)
        self.assertNotIn("Complete proposed patch", body)
        self.assertIn("Download the complete patch", body)
        self.assertLessEqual(len(body.encode()), runner.MAX_BODY)

    def test_artifact_cannot_retarget_pr(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            runner.save(root / "context.json", context())
            runner.save(root / "changes.json", changes())
            runner.save(root / "event.json", {})
            env = {"GITHUB_REPOSITORY": REPO, "GITHUB_ACTOR": "example-writer", "GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_EVENT_PATH": str(root / "event.json"), "INPUTS_JSON": json.dumps({"pr_number": "8", "comment_id": "42"})}
            with patch.dict(os.environ, env), patch.object(runner, "gh", side_effect=[{"id": 123}, {"permission": "write"}]):
                with self.assertRaisesRegex(ValueError, "differs"):
                    runner.verify_publication(root, "comment")

    def test_comment_publisher_only_writes_comments(self):
        calls = []
        def gh(path, method="GET", data=None, pages=False):
            calls.append((path, method, data))
            return [] if method == "GET" else {}
        with patch.object(runner, "verify_publication", return_value=(context(), changes())), patch.object(runner, "recheck_source"), patch.object(runner, "gh", side_effect=gh), patch.dict(os.environ, {"GITHUB_RUN_ID": "1"}):
            runner.publish_comment(Path("/unused"))
        writes = [(path, method) for path, method, data in calls if method != "GET"]
        self.assertEqual(writes, [(f"repos/{REPO}/issues/7/comments", "POST")])
        self.assertIn("Complete proposed patch", calls[-1][2]["body"])

    def test_stale_comment_prevents_all_writes(self):
        with patch.object(runner, "verify_publication", return_value=(context(), changes())), patch.object(runner, "recheck_source", side_effect=ValueError("stale")), patch.object(runner, "gh", return_value=[]) as gh, patch.dict(os.environ, {"GITHUB_RUN_ID": "1"}):
            with self.assertRaisesRegex(ValueError, "stale"):
                runner.publish_comment(Path("/unused"))
            self.assertTrue(all(len(call.args) == 1 for call in gh.call_args_list))

    def test_combined_findings_create_one_commit_and_one_pr(self):
        ctx = {"kind": "findings", "repository": REPO, "sha": "a" * 40, "version": "v" * 64,
               "base_branch": "main", "finding_ids": [ONE, TWO], "issue_number": None}
        calls = []
        def gh(path, method="GET", data=None, pages=False):
            calls.append((path, method, data))
            if method == "GET":
                if "/pulls?" in path:
                    return []
                if "/git/commits/" in path:
                    return {"tree": {"sha": "base-tree"}}
                return {"tree": [{"path": "app/test.rb", "mode": "100755"}]}
            return {"sha": "new-sha", "html_url": "https://github.com/example-org/example-repo/pull/8"}
        with patch.object(runner, "verify_publication", return_value=(ctx, changes())), patch.object(runner, "recheck_source"), patch.object(runner, "gh", side_effect=gh):
            runner.publish_findings(Path("/unused"))
        writes = [(path, data) for path, method, data in calls if method == "POST"]
        self.assertEqual([path.rsplit("/", 1)[-1] for path, data in writes], ["trees", "commits", "refs", "pulls"])
        self.assertEqual(writes[0][1]["tree"][0]["mode"], "100755")
        self.assertEqual(writes[1][1]["parents"], [ctx["sha"]])
        self.assertEqual(writes[-1][1]["base"], "main")
        self.assertIn(ONE, writes[-1][1]["body"])
        self.assertIn(TWO, writes[-1][1]["body"])
        self.assertIn(report()["summary"], writes[-1][1]["body"])
        self.assertIn(report()["files"]["app/test.rb"], writes[-1][1]["body"])
        self.assertIn("<!-- explanation-head:new-sha -->", writes[-1][1]["body"])
        self.assertIn("Tests were not run", writes[-1][1]["body"])

    def test_findings_retry_reuses_matching_ref_after_pr_creation_failure(self):
        ctx = {"kind": "findings", "repository": REPO, "sha": "a" * 40, "version": "v" * 64,
               "base_branch": "main", "finding_ids": [ONE], "issue_number": None}
        calls = []
        ref_created = False
        pr_attempts = 0
        def gh(path, method="GET", data=None, pages=False):
            nonlocal ref_created, pr_attempts
            calls.append((path, method, data))
            if method == "GET":
                if "/pulls?" in path:
                    return []
                if "/git/ref/" in path:
                    return {"object": {"type": "commit", "sha": "existing-commit"}}
                if path.endswith("/git/commits/existing-commit"):
                    return {"tree": {"sha": "expected-tree"}, "parents": [{"sha": ctx["sha"]}]}
                if "/git/commits/" in path:
                    return {"tree": {"sha": "base-tree"}}
                return {"tree": [{"path": "app/test.rb", "mode": "100644"}]}
            if path.endswith("/git/trees"):
                return {"sha": "expected-tree"}
            if path.endswith("/git/refs"):
                if ref_created:
                    raise subprocess.CalledProcessError(1, "gh", stderr="Reference already exists (HTTP 422)")
                ref_created = True
            if path.endswith("/pulls"):
                pr_attempts += 1
                if pr_attempts == 1:
                    raise subprocess.CalledProcessError(1, "gh", stderr="PR creation unavailable (HTTP 403)")
            return {"sha": "new-commit", "html_url": "https://github.com/example-org/example-repo/pull/8"}
        with patch.object(runner, "verify_publication", return_value=(ctx, changes())), patch.object(runner, "recheck_source"), patch.object(runner, "gh", side_effect=gh):
            with self.assertRaises(subprocess.CalledProcessError):
                runner.publish_findings(Path("/unused"))
            self.assertTrue(ref_created)
            runner.publish_findings(Path("/unused"))
        self.assertEqual(pr_attempts, 2)
        self.assertIn((f"repos/{REPO}/git/commits/existing-commit", "GET", None), calls)
        self.assertFalse(any(method in {"PATCH", "DELETE"} for path, method, data in calls))

    def test_findings_retry_rejects_mismatched_tree_or_source_parent(self):
        ctx = {"kind": "findings", "repository": REPO, "sha": "a" * 40, "version": "v" * 64,
               "base_branch": "main", "finding_ids": [ONE], "issue_number": None}
        for tree, parents in (("other-tree", [ctx["sha"]]), ("expected-tree", ["b" * 40]),
                              ("expected-tree", []), ("expected-tree", [ctx["sha"], "b" * 40])):
            with self.subTest(tree=tree, parents=parents), patch.object(runner, "verify_publication", return_value=(ctx, changes())), patch.object(runner, "recheck_source"), patch.object(runner, "gh") as gh:
                gh.side_effect = [[], {"tree": {"sha": "base-tree"}},
                                  {"tree": [{"path": "app/test.rb", "mode": "100644"}]},
                                  {"sha": "expected-tree"}, {"sha": "new-commit"},
                                  subprocess.CalledProcessError(1, "gh", stderr="Reference already exists (HTTP 422)"),
                                  {"object": {"sha": "existing-commit"}},
                                  {"tree": {"sha": tree}, "parents": [{"sha": parent} for parent in parents]}]
                with self.assertRaisesRegex(ValueError, "Existing remediation branch differs"):
                    runner.publish_findings(Path("/unused"))
                self.assertFalse(any(call.args[0].endswith("/pulls") or
                                     (len(call.args) > 1 and call.args[1] in {"PATCH", "DELETE"})
                                     for call in gh.call_args_list))

    def test_existing_findings_pr_links_source_issue(self):
        ctx = {"kind": "findings", "repository": REPO, "sha": "a" * 40, "version": "v" * 64,
               "base_branch": "main", "finding_ids": [ONE], "issue_number": 9}
        marker = f"<!-- dryrun-dcode:findings:{ctx['version']} -->"
        url = "https://github.com/example-org/example-repo/pull/8"
        existing_comment = {"id": 10, "user": {"login": "github-actions[bot]"}, "body": marker}
        pr = {"number": 8, "state": "open", "base": {"ref": "main"}, "head": {"sha": "head"}, "html_url": url,
              "body": marker + "\n" + runner.REPORT_FORMAT + "\n<!-- explanation-head:head -->"}
        for comments, endpoint, method in (([], "issues/9/comments", "POST"),
                                          ([existing_comment], "issues/comments/10", "PATCH")):
            with self.subTest(method=method), patch.object(runner, "verify_publication", return_value=(ctx, changes())), patch.object(runner, "recheck_source") as recheck, patch.object(runner, "gh") as gh:
                gh.side_effect = [[pr], pr, comments, {}]
                runner.publish_findings(Path("/unused"))
                self.assertEqual(gh.call_count, 4)
                gh.assert_called_with(f"repos/{REPO}/{endpoint}", method, {"body": f"Remediation PR: {url}\n\n{marker}"})
                recheck.assert_called_once_with(ctx)

    def test_existing_pr_refresh_requires_exact_head_then_preserves_report(self):
        ctx = {"kind": "findings", "repository": REPO, "sha": "a" * 40, "version": "v" * 64,
               "base_branch": "main", "finding_ids": [ONE], "issue_number": None,
               "explanation_pr": 8, "explanation_head": "head"}
        marker = f"<!-- dryrun-dcode:findings:{ctx['version']} -->"
        new_blob = subprocess.check_output(["git", "hash-object", "--stdin"], input=b"new\n").decode().strip()
        base = [{"path": "app/test.rb", "mode": "100755", "type": "blob", "sha": "old-blob"},
                {"path": ".github/untouched.yml", "mode": "100644", "type": "blob", "sha": "unchanged"}]
        for scenario in ("match", "mismatch", "unrelated", "stale", "foreign"):
            pr = {"number": 8, "state": "open", "base": {"ref": "other" if scenario == "foreign" else "main"},
                  "head": {"sha": "head"}, "html_url": "https://github.com/example-org/example-repo/pull/8", "body": marker}
            actual = [dict(base[0], sha="wrong" if scenario == "mismatch" else new_blob),
                      dict(base[1], sha="changed" if scenario == "unrelated" else "unchanged")]
            calls, reads = [], 0
            def gh(path, method="GET", data=None, pages=False):
                nonlocal reads
                calls.append((path, method, data))
                if method == "PATCH":
                    pr["body"] = data["body"]
                    return pr
                self.assertEqual(method, "GET")
                if "/pulls?" in path:
                    return [pr]
                if path.endswith("/pulls/8"):
                    reads += 1
                    return dict(pr, head={"sha": "changed"}) if scenario == "stale" and reads == 2 else pr
                return {"tree": base if ctx["sha"] in path else actual}
            with self.subTest(scenario=scenario), patch.object(runner, "verify_publication", return_value=(ctx, changes())), patch.object(runner, "recheck_source"), patch.object(runner, "gh", side_effect=gh):
                if scenario == "match":
                    runner.publish_findings(Path("/unused"))
                    self.assertIn(report()["summary"], pr["body"])
                    self.assertIn(report()["files"]["app/test.rb"], pr["body"])
                    self.assertIn("<!-- explanation-head:head -->", pr["body"])
                    self.assertIn(ctx["sha"], pr["body"])
                    self.assertIn("Complete patch and agent report", pr["body"])
                    original = pr["body"]
                    with patch.object(runner, "read_report", return_value=dict(report(), summary="A different explanation")):
                        runner.publish_findings(Path("/unused"))
                    self.assertEqual(pr["body"], original)
                    self.assertEqual([method for path, method, data in calls if method != "GET"], ["PATCH"])
                else:
                    with self.assertRaises(ValueError):
                        runner.publish_findings(Path("/unused"))
                    self.assertTrue(all(method == "GET" for path, method, data in calls))

    def test_head_comparison_handles_created_deleted_and_truncated_trees(self):
        ctx = {"repository": REPO, "sha": "base"}
        updates = [{"path": "deleted.rb", "before": "old", "after": None},
                   {"path": "new.rb", "before": None, "after": "é\n"}]
        blob = subprocess.check_output(["git", "hash-object", "--stdin"], input="é\n".encode()).decode().strip()
        base = {"tree": [{"path": "deleted.rb", "mode": "100644", "type": "blob", "sha": "old"}]}
        head = {"tree": [{"path": "new.rb", "mode": "100644", "type": "blob", "sha": blob}]}
        with patch.object(runner, "gh", side_effect=[base, head]):
            runner.verify_existing_head(ctx, updates, "head")
        with patch.object(runner, "gh", return_value={"truncated": True}), self.assertRaisesRegex(ValueError, "truncated"):
            runner.verify_existing_head(ctx, updates, "head")


if __name__ == "__main__":
    unittest.main()
