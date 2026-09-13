# Security

Greenblind executes the command you supply against copies of repository code. It runs with your user permissions, inherited environment variables, and network access. Copies protect the working tree from Greenblind's own edits; they are not a security boundary against test code.

Use trusted repositories or an external disposable sandbox. Do not run unknown PR code on a machine with valuable credentials. Commands must terminate their own background services.

Reports contain code excerpts and command arguments. Captured log tails are opt-in. HTML escapes source text and has no scripts, network resources, analytics, or external fonts. Review reports before making them public.

Report vulnerabilities through GitHub's private vulnerability reporting when available. Avoid posting credentials or private code in public issues.
