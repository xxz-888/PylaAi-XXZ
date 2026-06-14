import sys

from gui.multi_instance_launcher import run_multi_instance_launcher


if __name__ == "__main__":
    raise SystemExit(run_multi_instance_launcher(smoke_test="--smoke-test" in sys.argv))
