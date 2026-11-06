"""runbook-doctor: a staleness gate for runbooks.

A runbook rots quietly: the script it tells you to run gets renamed, the link
it points at dies, the variable it sets is defined nowhere. Nothing checks,
because a runbook is prose. This makes it checkable: exit 1 when a runbook
names a script that no longer exists, and report the rest by severity."""

__version__ = "0.1.0"
