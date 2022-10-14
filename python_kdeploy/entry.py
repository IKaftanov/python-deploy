from __future__ import annotations

import argparse

from python_kdeploy.invoke_generator import settings
from python_kdeploy.invoke_generator.helpers import (
    get_context,
    build_image,
    submit_service,
    remove_service,
)


class SmartFormatter(argparse.HelpFormatter):
    def _split_lines(self, text, width):
        if text.startswith("R|"):
            return text[2:].splitlines()
        # this is the RawTextHelpFormatter._split_lines
        return argparse.HelpFormatter._split_lines(self, text, width)


def execute_command(service: str, action: str, target: str, no_cache: bool):
    target_host = settings.TARGETS[target]
    context = get_context(target_host.host, target_host.user, target_host.port)
    if action == "deploy":
        build_image(context, settings.IMAGES[service], no_cache)
        submit_service(context, settings.IMAGES[service])
    else:
        remove_service(context, settings.IMAGES[service])


def cmd():
    parser = argparse.ArgumentParser(
        description="Deployment Commands", formatter_class=SmartFormatter
    )

    parser.add_argument(
        "--service",
        choices=[k for k, v in settings.IMAGES.items() if v.service],
        help="Service name",
    )
    parser.add_argument("--action", choices=settings.COMMANDS)

    parser.add_argument(
        "--target",
        choices=[target for target in settings.TARGETS],
        default="PROD",
        help="R|"
        + "\n".join(f"{k}: {v}" for k, v in settings.TARGETS.items()),
    )

    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--verbose", action="store_true")

    args = parser.parse_args()
    if args.verbose:
        print(args)
        print(
            "Available Images:\n",
            "\n".join(str(item) for item in settings.IMAGES.values()),
        )
        print(
            "Available Targets:\n",
            "\n".join(str(item) for item in settings.TARGETS.values()),
        )
    if not args.service or not args.action:
        raise RuntimeError("no arguments passed")

    execute_command(args.service, args.action, args.target, args.no_cache)
