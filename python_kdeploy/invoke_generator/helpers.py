from __future__ import annotations

import io
import os.path
import typing as t
import uuid

from fabric import Connection

from .datatypes import Image

BuildKwargs = t.Dict[str, str]


def read_service_template() -> str:
    cur_dir = os.path.join(os.path.dirname(__file__), "service.temp")
    with open(cur_dir, "r") as f:
        data = f.read()
    return data


def get_context(
    host: str, user: str, port: t.Optional[int] = 22
) -> Connection:
    return Connection(host=host, user=user, port=port)


def get_sha(context: Connection, folder: str) -> str:
    with context.cd(folder):
        result = context.run("git rev-parse --short HEAD", hide=True)
        return result.stdout.strip()


def exists(context: Connection, path: str) -> bool:
    return context.run(f"ls {path}", warn=True, hide=True).ok


def git_clone(
    context: Connection, repository_name: str, branch: t.Optional[str] = None
) -> None:
    if not branch:
        branch = "master"
    # remove repo before clone
    if exists(context, repository_name):
        print("[PREP] remove existing folder")
        context.run(f"sudo rm -rf {repository_name}")
    context.run(
        "git clone --progress --verbose --single-branch --branch"
        f" {branch} git@bitbucket.org:selenium-health/{repository_name}.git"
    )
    return


def upload_file(
    context: Connection,
    file: t.Union[str, io.StringIO],
    remote_path: str,
    su: bool = False,
) -> None:
    context.run(f"sudo mkdir --parents {os.path.dirname(remote_path)}")
    if not su:
        context.put(file, remote=remote_path)
    else:
        tmp_file_name = f"tmp_{uuid.uuid4()}"
        context.put(file, remote=tmp_file_name)
        context.run(f"sudo mv {tmp_file_name} {remote_path}")


def create_docker_build_command(
    dockerfile_path: str,
    image_name: str,
    no_cache: bool,
    build_kwargs: BuildKwargs,
) -> str:
    """
    docker build {--no-cache} -t {image_name}
    -f {Dockerfile} --build-arg {ARG1=KEY1 ...} .
    """
    cmd = "sudo docker build"
    if no_cache:
        cmd += " --no-cache"

    cmd += f" -t {image_name}"
    cmd += f" -f {dockerfile_path}"
    for key, value in build_kwargs.items():
        cmd += f" --build-arg {key}={value}"
    cmd += " ."
    print(f"\t[PREPARE] create cmd: `{cmd}`")
    return cmd


def _build_image(
    context: Connection,
    image: Image,
    no_cache: bool = False,
    build_kwargs: BuildKwargs = None,
) -> str:
    sha = get_sha(context, image.repository_name) or "latest"
    image_name = f"{image.key}:{sha}"

    build_kwargs = build_kwargs or {}
    cmd = create_docker_build_command(
        image.dockerfile_path, image_name, no_cache, build_kwargs
    )
    with context.cd(image.repository_name):
        print(
            f"\t\t[BUILD] " f"Building the image from {image.dockerfile_path}"
        )
        context.run(cmd, hide=True)
    print(f"\t\t[BUILD] Finished. Image name = {image_name}")
    return image_name


def build_image(
    context: Connection,
    image: Image,
    no_cache: bool = False,
    build_kwargs: BuildKwargs = None,
) -> str:
    base_image = None
    if image.depends:
        if len(image.depends) > 1:
            raise NotImplementedError("multiple depends are not supported")
        base_image = _build_image(
            context, image.depends[0], no_cache, build_kwargs
        )
        image.depends[0].built_image_name = base_image
    build_kwargs = build_kwargs or {}
    if base_image:
        build_kwargs["BASE_IMAGE"] = base_image
    out_image_name = _build_image(context, image, no_cache, build_kwargs)
    image.built_image_name = out_image_name
    return out_image_name


def submit_service(context: Connection, image: Image) -> None:
    """
    1. Upload env file
    2. Check if service exist
    2. Create service config and upload
    3. Setup systemd service
    """
    if image.env_file:
        env_file_remote = f"{image.app_path}/{image.env_file}"
        upload_file(context, image.env_file, env_file_remote, su=True)
    else:
        env_file_remote = ""
    # 2
    srv = read_service_template().format(
        SERVICE_DESCRIPTION=f"FaceSign {image.key}",
        RUN_PARAMS=image.run_params,
        ENV_FILE=f"--env-file {env_file_remote}" if image.env_file else "",
        IMAGE_NAME=image.built_image_name,
    )
    upload_file(
        context,
        io.StringIO(srv),
        f"/etc/systemd/system/{image.key}.service",
        su=True,
    )
    # 3
    context.run("sudo systemctl daemon-reload")
    context.run(f"sudo systemctl start {image.key}.service")
    context.run(f"sudo systemctl enable {image.key}.service")


def remove_service(context: Connection, image: Image) -> None:
    """Remove service from systemctl"""
    context.run(f"sudo rm -rf /var/www/apps/{image.key}")
    context.run(f"sudo systemctl stop {image.key}.service", warn=True)
    context.run(f"sudo systemctl disable {image.key}.service", warn=True)
    context.run(f"sudo rm /etc/systemd/system/{image.key}.service", warn=True)
    context.run(f"sudo rm /etc/systemd/system/{image.key}.service", warn=True)
    context.run(
        f"sudo rm /usr/lib/systemd/system/{image.key}.service", warn=True
    )
    context.run(
        f"sudo rm /usr/lib/systemd/system/{image.key}.service", warn=True
    )
    context.run(f"sudo rm /etc/init.d/{image.key}.service", warn=True)
    context.run("sudo systemctl daemon-reload", warn=True)
    context.run("sudo systemctl reset-failed", warn=True)
