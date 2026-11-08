import os


def dangerous_wipe_system() -> None:
    """Deliberately dangerous snippet attempting command execution."""
    os.system("rm -rf /tmp/test_dir")
