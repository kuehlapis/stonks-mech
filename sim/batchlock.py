"""Atomic, cross-process lock for expensive match/calibration batches."""
import os
import shutil
import sys
import time


LOCK = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "notes", "tests", ".match-batch.lock"))


class BatchLock:
    def __init__(self, label, timeout=1800):
        self.label = label
        self.timeout = timeout
        self.owner = False

    def acquire(self):
        deadline = time.time() + self.timeout
        while True:
            try:
                os.mkdir(LOCK)
            except FileExistsError:
                try:
                    age = time.time() - os.path.getmtime(LOCK)
                    if age > 21600:
                        shutil.rmtree(LOCK, ignore_errors=True)
                        continue
                except OSError:
                    pass
                if time.time() >= deadline:
                    raise TimeoutError("another match batch owns %s (lock %s)" % (self.label, LOCK))
                time.sleep(0.25)
                continue
            owner = os.path.join(LOCK, "owner.json")
            with open(owner, "w", encoding="utf-8") as f:
                f.write(__import__("json").dumps({"pid": os.getpid(), "label": self.label}))
            self.owner = True
            return

    def release(self):
        if self.owner:
            shutil.rmtree(LOCK, ignore_errors=True)
            self.owner = False

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.release()
