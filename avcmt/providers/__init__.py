# Copyright 2025 Andy Vandaric
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# File: avcmt/providers/__init__.py
from .pollinations import PollinationsProvider


def get_provider(name):
    """Returns an instance of the provider class associated with the specified name or raises a NotImplementedError if the provider is not recognized.

    This function maps a provider name to its corresponding provider class instance. If the provider name is not recognized, it raises an error indicating that the provider is not implemented.

    Args:
        name (str): The name of the provider to instantiate.

    Returns:
        object: An instance of the corresponding provider class.

    Raises:
        NotImplementedError: If the provider name is not recognized.
    """
    if name.lower() == "pollinations":
        return PollinationsProvider()
    raise NotImplementedError(f"Provider '{name}' is not implemented yet.")
