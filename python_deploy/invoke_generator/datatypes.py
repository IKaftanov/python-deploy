from __future__ import annotations

import dataclasses as dc
import os.path
import typing as t


@dc.dataclass
class Host:
    user: str
    host: str
    root: str
    port: t.Optional[int] = 22

    def __str__(self) -> str:
        return f"Host(user={self.user}, host={self.host})"


@dc.dataclass
class Image:
    key: str
    service: bool
    repository_name: str
    branch: str
    dockerfile_path: str
    depends: t.List[Image] = dc.field(default_factory=lambda: [])
    build_kwargs: t.Dict[str, str] = dc.field(default_factory=lambda: {})
    run_params: t.Optional[str] = ""
    env_file: t.Optional[str] = None
    app_path: t.Optional[str] = ""
    built_image_name: t.Optional[str] = ""

    def __post_init__(self) -> None:
        correct_build_kwargs = {}
        for key, value in self.build_kwargs.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise ValueError("unable to update build args")
            correct_build_kwargs[key.upper()] = value.upper()
        self.build_kwargs = correct_build_kwargs

        if self.app_path:
            self.app_path = os.path.join(self.app_path, self.key)
