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


# File: avcmt/__init__.py
# Deskripsi: Mendefinisikan API publik untuk paket avcmt.

# Mengekspos fungsi utama untuk proses commit sebagai bagian dari API publik.
# Pengguna paket Anda akan mengimpor ini.
from .commit import run_commit_group_all

# Mengekspos kelas dan error dari modul release juga merupakan praktik yang baik,
# jika Anda ingin pengguna dapat menggunakannya secara terprogram.
from .release import ReleaseFailedError, ReleaseManager

# Mengekspos fungsi utilitas yang mungkin berguna bagi pengguna eksternal (opsional).
# Untuk saat ini, kita biarkan internal untuk menjaga API tetap bersih.
# from .utils import setup_logging

# Mendefinisikan apa yang akan diimpor saat pengguna melakukan `from avcmt import *`
__all__ = [
    "ReleaseFailedError",
    "ReleaseManager",
    "run_commit_group_all",
]
