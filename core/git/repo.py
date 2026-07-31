import subprocess

TIMEOUT_SECONDS = 15


def run(cwd, *args):
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
    )


def head_sha(cwd):
    try:
        proc = run(cwd, "rev-parse", "HEAD")
    except Exception:
        return None
    return proc.stdout.strip() if proc.returncode == 0 else None


def toplevel(cwd):
    try:
        proc = run(cwd, "rev-parse", "--show-toplevel")
    except Exception as e:
        return None, str(e)
    return (proc.stdout.strip(), None) if proc.returncode == 0 else (None, proc.stderr.strip())


def resolve(cwd):
    root, error = toplevel(cwd)
    if not root:
        return None, error
    sha = head_sha(root)
    if not sha:
        return None, f"could not resolve HEAD in {root}"
    return (root, sha), None


def diff(cwd, base, head, exclude_pathspecs=()):
    if base == head:
        return ""
    try:
        proc = run(cwd, "diff", f"{base}..{head}", "--", ".", *exclude_pathspecs)
    except Exception:
        return ""
    return proc.stdout if proc.returncode == 0 else ""


def user_email():
    try:
        proc = run(None, "config", "user.email")
    except Exception:
        return "unknown"
    return proc.stdout.strip() or "unknown" if proc.returncode == 0 else "unknown"
