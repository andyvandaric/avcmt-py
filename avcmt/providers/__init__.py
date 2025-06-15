# File: avcmt/providers/__init__.py
from .pollinations import PollinationsProvider


def get_provider(name):
    if name.lower() == "pollinations":
        return PollinationsProvider()
    raise NotImplementedError(f"Provider '{name}' is not implemented yet.")
