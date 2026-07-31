import contextlib

try:
    import fcntl
except ImportError:  # Windows
    fcntl = None  # type: ignore[assignment]


@contextlib.contextmanager
def try_lock(path):
    if fcntl is None:
        yield True
        return

    try:
        lock_file = open(path, "w")
    except OSError:
        yield True
        return

    acquired = False
    try:
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            acquired = True
        except OSError:
            pass
        yield acquired
    finally:
        if acquired:
            fcntl.flock(lock_file, fcntl.LOCK_UN)
        lock_file.close()
