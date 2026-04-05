#!/usr/bin/env python3
import sys


DEPRECATION_MESSAGE = (
    "apps/Portal/dpipe-gui.py is deprecated.\n"
    "Use the ControlPilot diffusion-pipe UI and API endpoints instead.\n"
)


def main() -> int:
    sys.stderr.write(DEPRECATION_MESSAGE)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
