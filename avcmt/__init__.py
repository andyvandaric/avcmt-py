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

"""
This file defines the public API of the 'avcmt' package, making key components
directly importable for users of the library.
"""

# Expose the primary function for the commit process from its new location.
# This allows users to do `from avcmt import run_commit_group_all`.
from .modules.commit_generator import run_commit_group_all

# Expose classes and errors from the release module from its new location.
# This allows `from avcmt import ReleaseManager`.
from .modules.release_manager import ReleaseFailedError, ReleaseManager

# Defines what will be imported when a user runs `from avcmt import *`.
# It's a good practice to explicitly list the public API.
__all__ = [
    "ReleaseFailedError",
    "ReleaseManager",
    "run_commit_group_all",
]
