# runbook-doctor

[![selftest](https://github.com/waleakomolafe/runbook-doctor/actions/workflows/selftest.yml/badge.svg)](https://github.com/waleakomolafe/runbook-doctor/actions/workflows/selftest.yml)

A staleness gate for runbooks. It reads your markdown and fails the build
when the runbook tells someone to run a script that no longer exists.

| rule | severity | what it flags |
|---|---|---|
| `missing-script` | HIGH | a step runs `ops/foo.sh` and the file is gone - renamed, moved, or deleted after the runbook was written |
| `dead-link` | MEDIUM | a relative link or image points at a file that does not exist |
| `lone-variable` | LOW | `$VAR` used inside exactly one command and mentioned nowhere else in the doc - defined nowhere the reader can see |
| `todo-rot` | INFO | TODO / FIXME markers, counted and shown, never a failure |

A runbook is the one document people open under pressure, and nothing
compiles it. The script it names gets renamed in a refactor nobody connects
to the doc; the failure surfaces at 3am as "follow the runbook", and the
runbook's first step is wrong. Controls belong in the pipeline - the same
premise as
[drift-sentinel](https://github.com/waleakomolafe/drift-sentinel),
[pipeline-sentinel](https://github.com/waleakomolafe/pipeline-sentinel) and
[slo-sentinel](https://github.com/waleakomolafe/slo-sentinel), applied to
documentation.

## Install

    pip install .

## Use

    runbook-doctor docs/ README.md     # those files
    runbook-doctor .                   # every .md under the path
    runbook-doctor --fail-severity MEDIUM .
    runbook-doctor --format json .

Exit codes: 0 clean, 1 findings at or above the fail severity (HIGH by
default), 2 nothing scanned. Web links, anchors and mailto targets are
skipped; the doctor judges this repo, not the internet.

Put it in CI next to the lint job and a stale runbook stops shipping.

## Selftest

CI runs the test suite, then the doctor against this repository's own
markdown, then audits this repo's workflows with pipeline-sentinel. A
runbook linter that fails its own runbook would be its own finding.

## Scope and limits

Markdown only. Script detection covers code spans that reference a path
with a runnable extension (`.sh`, `.py`, `.ps1`, `.cmd`, `.bat`); a bare
command like `terraform plan` is deliberately ignored - it is a command,
not a repo file. The variable rule is advisory by design: it cannot know
your shell environment, so it reports and lets a person decide.

## License

MIT
