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

# File: avcmt/system/context_managers.py
"""
This module provides a context manager for handling signals gracefully.
FINAL REVISION: Implements a 'double-press CTRL+C' shutdown mechanism for better UX.
"""

import os
import signal
import subprocess
import sys
import threading

from avcmt.utils import get_docs_dry_run_file, get_log_file


class GracefulShutdownManager:
    """
    A robust, class-based context manager for handling CTRL+C (SIGINT)
    using a 'double-tap' confirmation mechanism with enhanced Windows support.
    """

    def __init__(self, confirmation_timeout: int = 5):
        self.shutdown_event = threading.Event()
        self.original_handler = None
        self.interrupt_received = False
        self.confirmation_timeout = confirmation_timeout
        self.timer = None
        self._shutdown_initiated = False
        self._cleanup_completed = False  # Track cleanup completion

    def __enter__(self):
        """Sets up the custom signal handler upon entering the 'with' block."""
        self.original_handler = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, self._handler)
        return self.shutdown_event

    def __exit__(self, exc_type, exc_value, traceback):
        """Restores the original signal handler upon exiting with comprehensive cleanup."""
        # Cancel any active timer
        if self.timer:
            self.timer.cancel()
            self.timer = None

        # Restore original signal handler
        if self.original_handler:
            signal.signal(signal.SIGINT, self.original_handler)

        # Mark cleanup as completed
        self._cleanup_completed = True

        # ENHANCED: Comprehensive exception suppression for Windows batch job prevention
        if exc_type is None:
            # Normal exit, no exceptions
            return False

        # Handle all possible interruption-related exceptions
        suppressed_exceptions = (
            KeyboardInterrupt,
            SystemExit,
            EOFError,
            BrokenPipeError,
            ConnectionResetError,
        )

        if exc_type in suppressed_exceptions or (
            exc_type and issubclass(exc_type, suppressed_exceptions)
        ):
            self._shutdown_initiated = True
            # Force a clean exit by suppressing the exception completely
            return True

        # Don't suppress other types of exceptions
        return False

    def _reset_interrupt_flag(self):
        """Callback to reset the interrupt flag if the confirmation window expires."""
        if not self._shutdown_initiated and not self._cleanup_completed:
            print(
                "\nTermination confirmation window expired. Resuming...",
                file=sys.stderr,
            )
            self.interrupt_received = False
            self.timer = None

    def _handler(self, signum, frame):
        """
        Handles the SIGINT signal with immediate termination strategy to prevent hanging.
        """
        # Ignore signals if cleanup is already completed
        if self._shutdown_initiated or self._cleanup_completed:
            return

        if self.interrupt_received:
            # This is the second press (confirmation)
            if self.timer:
                self.timer.cancel()
                self.timer = None
            print(
                "\nTermination confirmed. Signaling workers to stop...", file=sys.stderr
            )
            self._shutdown_initiated = True
            self.shutdown_event.set()

            # ENHANCED: Always show summary before termination
            self._show_termination_summary()

            # FIXED: Proper cross-platform termination with better error handling
            try:
                if sys.platform == "win32":
                    # Windows: Kill process tree using taskkill
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(os.getpid())],
                        capture_output=True,
                        timeout=2,
                        check=False,
                    )
                else:
                    # Unix: Send SIGTERM to process group
                    os.killpg(os.getpgid(os.getpid()), signal.SIGTERM)
            except Exception:
                # All termination attempts failed, use fallback
                pass

            # ULTIMATE: Force immediate exit regardless of cleanup success
            os._exit(130)
        else:
            # This is the first press
            self.interrupt_received = True
            print(
                f"\nCTRL+C detected. Press CTRL+C again within {self.confirmation_timeout} seconds to terminate.",
                file=sys.stderr,
            )
            # Start a timer to reset the confirmation state
            self.timer = threading.Timer(
                self.confirmation_timeout, self._reset_interrupt_flag
            )
            self.timer.start()

    @staticmethod
    def _show_termination_summary():
        """Show termination summary with file paths before forced exit."""
        try:
            print("\n" + "=" * 60, file=sys.stderr)
            print("🛑 PROCESS ABORTED BY USER", file=sys.stderr)
            print("=" * 60, file=sys.stderr)

            dry_run_path = get_docs_dry_run_file()
            log_path = get_log_file("docs.log")

            if dry_run_path.exists():
                print(f"📄 Dry run results: {dry_run_path}", file=sys.stderr)
            else:
                print("📄 No dry run results found", file=sys.stderr)

            if log_path.exists():
                print(f"📜 Full log file: {log_path}", file=sys.stderr)
            else:
                print("📜 No log file found", file=sys.stderr)

            print("=" * 60 + "\n", file=sys.stderr)

        except Exception:
            # Silently ignore any errors in summary display
            pass
