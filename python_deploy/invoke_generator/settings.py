from __future__ import annotations

import functools
import os.path
import typing as t

import toml

from python_deploy.invoke_generator.datatypes import Image, Host


def parse_image_config(images: dict, image: str) -> Image:
    return Image(
        key=image,
        service=images[image]["service"],
        depends=[
            parse_image_config(images, item)
            for item in images[image].get("depends", [])
        ],
        repository_name=images[image]["repository_name"],
        branch=images[image]["branch"],
        dockerfile_path=images[image]["dockerfile_path"],
        build_kwargs=images[image].get("build_kwargs", {}),
        run_params=images[image].get("run_params", ""),
        env_file=images[image].get("env_file", None),
        app_path=images[image].get("app_path", ""),
    )


@functools.lru_cache(1)
def parse_config() -> t.Tuple[t.Dict[str, Host], t.Dict[str, Image]]:
    file_path = os.path.join(os.curdir, "config.toml")

    with open(file_path, "r") as f:
        config = toml.load(f)

    if "host" not in config:
        raise RuntimeError("unable to find host in config")

    targets = {}
    hosts = config["host"]
    for host in hosts:
        targets[host.upper()] = Host(
            hosts[host]["user"],
            hosts[host]["host"],
            hosts[host].get("root", "."),
            hosts[host].get("port", 22),
        )

    target_images = {}
    images = config["image"]
    for image in images:
        target_images[image] = parse_image_config(images, image)

    return targets, target_images


TARGETS, IMAGES = parse_config()

COMMANDS = {"deploy", "remove"}

if __name__ == "__main__":
    print(TARGETS, IMAGES)
