import textwrap

from runbook_doctor import cli
from runbook_doctor.checks import check, link_refs, script_refs

GOOD = """
# Runbook

Run `ops/deploy.sh --prod` then check [the dashboard](docs/dash.md).

Set `REGION=us` before `ops/migrate.py`, and export `${REGION}` everywhere.
"""


def build(tmp_path, body, name="docs/runbook.md", extra=None):
    root = tmp_path
    (root / "ops").mkdir(exist_ok=True)
    (root / "ops" / "deploy.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    (root / "ops" / "migrate.py").write_text("", encoding="utf-8")
    (root / "docs").mkdir(exist_ok=True)
    (root / "docs" / "dash.md").write_text("dash\n", encoding="utf-8")
    doc = root / name
    doc.write_text(textwrap.dedent(body), encoding="utf-8")
    for rel, content in (extra or {}).items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return list(check(doc, root))


def test_clean_runbook_has_no_findings(tmp_path):
    assert build(tmp_path, GOOD) == []


def test_missing_script_is_high(tmp_path):
    fs = build(tmp_path, """
        # Runbook

        Restore with `ops/restore.sh --all`.
        """)
    assert [(f.rule, f.severity) for f in fs] == [("missing-script", "HIGH")]


def test_bare_command_names_are_not_scripts(tmp_path):
    fs = build(tmp_path, """
        Run `terraform plan` and `./local.sh`.
        """)
    rules = [f.rule for f in fs]
    assert "missing-script" not in rules  # terraform is a command; ./local.sh is a bare name


def test_dead_relative_link_is_medium(tmp_path):
    fs = build(tmp_path, """
        See [the old doc](docs/old.md) first.
        """)
    assert [(f.rule, f.severity) for f in fs] == [("dead-link", "MEDIUM")]


def test_web_links_and_anchors_are_skipped():
    text = "[x](https://example.com/a.md) [y](#section) [z](mailto:a@b.c)"
    assert list(link_refs(text)) == []


def test_lone_variable_is_low(tmp_path):
    fs = build(tmp_path, """
        Deploy with `ops/deploy.sh --region $REGION_ONLY_ONCE`.
        """)
    assert ("lone-variable", "LOW") == (fs[0].rule, fs[0].severity)


def test_variable_mentioned_twice_is_known(tmp_path):
    fs = build(tmp_path, """
        Set REGION in the portal, then run `ops/deploy.sh --region $REGION`.
        """)
    assert [f for f in fs if f.rule == "lone-variable"] == []


def test_todo_rot_is_info_never_a_failure(tmp_path):
    fs = build(tmp_path, "# Run\n\n<!-- TODO: rewrite this -->\n")
    assert [(f.rule, f.severity) for f in fs] == [("todo-rot", "INFO")]


def test_script_ref_extraction():
    text = "run `ops/a.sh x` and `$HOME/bin/b.py` and `notapath.sh`"
    assert sorted(script_refs(text)) == ["HOME/bin/b.py", "ops/a.sh"]


def _repo(tmp_path, docs, files):
    for rel, content in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return tmp_path


def test_table_rows_are_summaries_not_steps(tmp_path):
    fs = build(tmp_path, """
        | rule | example |
        |---|---|
        | missing-script | `ops/gone.sh` named in a step |

        But a step `ops/deploy.sh` outside a table is real.
        """)
    rules = [f.rule for f in fs]
    assert "missing-script" not in rules


def test_cli_fails_on_missing_script(tmp_path, capsys):
    _repo(tmp_path, None, {
        "README.md": "Run `ops/gone.sh` now.\n",
        "ops/ok.sh": "",
    })
    assert cli.main([str(tmp_path / "README.md"), "--root", str(tmp_path)]) == 1
    assert "missing-script" in capsys.readouterr().out


def test_cli_passes_clean_repo(tmp_path, capsys):
    _repo(tmp_path, None, {
        "README.md": "Run `ops/ok.sh`.\n",
        "ops/ok.sh": "",
    })
    assert cli.main([str(tmp_path), "--root", str(tmp_path)]) == 0
    assert "clean" in capsys.readouterr().out


def test_cli_threshold_and_json(tmp_path, capsys):
    _repo(tmp_path, None, {
        "README.md": "See [gone](gone.md).\n",
    })
    assert cli.main([str(tmp_path / "README.md"), "--root", str(tmp_path),
                     "--fail-severity", "MEDIUM"]) == 1
    capsys.readouterr()
    assert cli.main([str(tmp_path / "README.md"), "--root", str(tmp_path),
                     "--format", "json", "--fail-severity", "HIGH"]) == 0
    import json as _json
    payload = _json.loads(capsys.readouterr().out)
    assert payload["findings"][0]["rule"] == "dead-link"


def test_cli_no_markdown(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    assert cli.main([str(empty)]) == 2
