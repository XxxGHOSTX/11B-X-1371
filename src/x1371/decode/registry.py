from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from . import transforms
from .transforms import TransformResult

Transform = Callable[[str], Iterable[TransformResult]]


@dataclass(slots=True)
class RegisteredTransform:
    name: str
    handler: Transform


class DecoderRegistry:
    def __init__(self) -> None:
        self._transforms: list[RegisteredTransform] = []

    def register(self, name: str, handler: Transform) -> None:
        self._transforms.append(RegisteredTransform(name=name, handler=handler))

    def transforms(self) -> list[RegisteredTransform]:
        return list(self._transforms)


def default_registry() -> DecoderRegistry:
    registry = DecoderRegistry()
    registry.register("reverse", transforms.reverse_transform)
    registry.register("rot", transforms.rot_transform)
    registry.register("atbash", transforms.atbash_transform)
    registry.register("base", transforms.base_transform)
    registry.register("hex", transforms.hex_transform)
    registry.register("binary", transforms.binary_transform)
    registry.register("octal_decimal", transforms.octal_decimal_transform)
    registry.register("grid", transforms.grid_transform)
    registry.register("mirrored", transforms.mirrored_transform)
    registry.register("upside_down", transforms.upside_down_transform)
    registry.register("transposition", transforms.transposition_helpers)
    return registry
