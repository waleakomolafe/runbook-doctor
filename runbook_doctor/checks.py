"""The checks. Pure functions over (markdown text, repo root) so tests need
no git and no network.

Severities, by what fails at 3am:
  HIGH   a step names a script that does not exist - the runbook lies at the
         exact moment it is opened
  MEDIUM a relative link or image is dead - the next reader hits a 404 and
         stops trusting the rest
  LOW    a variable used in a command appears nowhere else in the doc -
         possibly undefined, possibly fine; a person decides
  INFO   TODO / FIXME count - rot made visible, never a failure
"""

import re
from dataclasses import dataclass
from pathlib import Path

CODE_SPAN = re.compile(r"`([^`\n]+)`")
LINK = re.compile(r"\[[^\]]*\]\(\s*([^)\s]+)\s*\)")
DOLLAR_BRACED = re.compile(r"\$\{(\w+)\}")
DOLLAR_BARE = re.compile(r"(?<![\w$])\$(\w+)")
TODO = re.compile(r"\b(TODO|FIXME|XXX)\b", re.IGNORECASE)
RUNNABLE = (".sh", ".py", ".ps1", ".cmd", ".bat")


@dataclass
class Finding:
    rule: str
    severity: str
    file: str
    detail: str


def script_refs(text):
    """Local script paths inside code spans. A command like `ops/foo.sh -x`
    yields ops/foo.sh; absolute URLs and bare filenames are ignored (a bare
    name is usually a command, not a repo file)."""
    for token in CODE_SPAN.findall(text):
        words = token.strip().split()
        if not words:
            continue
        word = words[0].lstrip("$").strip("\"'")
        # "./x.sh" is a bare name wearing a directory costume.
        if word.startswith("./"):
            word = word[2:]
        if word.endswith(RUNNABLE) and ("/" in word or "\\" in word):
            yield word


def link_refs(text):
    """Relative markdown/image targets. http(s), mailto, anchors and absolute
    paths are skipped - the doctor judges this repo, not the internet."""
    for href in LINK.findall(text):
        if "://" in href or href.startswith(("mailto:", "#", "/")):
            continue
        yield href.split("#")[0]


def check(doc, root):
    """Yield findings for one markdown document against a repo root."""
    doc = Path(doc).resolve()
    root = Path(root).resolve()
    full = doc.read_text(encoding="utf-8", errors="replace")
    # Table rows are summaries, not steps: a rules table that documents
    # `ops/foo.sh` as an EXAMPLE must not read as a run step. Links stay
    # checked everywhere - a link in a table is still a link.
    step_text = "\n".join(l for l in full.splitlines()
                          if not l.lstrip().startswith("|"))
    rel = str(doc.relative_to(root)).replace("\\", "/")

    for ref in sorted(set(script_refs(step_text))):
        if not (root / ref).exists():
            yield Finding("missing-script", "HIGH", rel,
                          "step runs `%s` but %s does not exist" % (ref, ref))

    for href in sorted(set(link_refs(full))):
        if href and not (root / href.replace("/", "\\")).exists() \
                and not (root / href).exists():
            yield Finding("dead-link", "MEDIUM", rel,
                          "links to %s which does not exist" % href)

    used = set(DOLLAR_BRACED.findall("".join(
        t for t in CODE_SPAN.findall(step_text) if "$" in t)))
    used |= set(DOLLAR_BARE.findall("".join(
        t for t in CODE_SPAN.findall(step_text) if "$" in t)))
    # A variable mentioned anywhere else in the doc (definition, prose,
    # another example) counts as known. Used exactly once in a command and
    # never again is the smell.
    for var in sorted(used):
        if len(re.findall(r"\b%s\b" % re.escape(var), full)) < 2:
            yield Finding("lone-variable", "LOW", rel,
                          "$%s appears only inside one command - defined "
                          "nowhere in this doc" % var)

    todos = TODO.findall(step_text)
    if todos:
        yield Finding("todo-rot", "INFO", rel,
                      "%d TODO/FIXME marker(s)" % len(todos))
