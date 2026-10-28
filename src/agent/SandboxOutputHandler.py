"""Module to inspect, clean, and truncate sandbox outputs."""


class SandboxOutputHandler:
    """Handles inspection, cleaning, and truncation of sandbox outputs."""

    @staticmethod
    def is_test_run_finished(
        code: str, output: str, has_patch: bool, benchmark: str = "swebench"
    ) -> bool:
        """Determine if the candidate solution passed all tests.

        Parameters
        ----------
        code : str
            The python code executed in the sandbox.
        output : str
            The raw stdout/stderr observation returned by the sandbox.
        has_patch : bool
            Whether a non-empty patch/diff exists in the repository.
        benchmark : str
            Target benchmark type ("swebench" or "mbpp").

        Returns
        -------
        bool
            True if tests passed and code modifications exist, False otherwise.
        """
        # 1. Verify that run_tests was actually invoked
        if "run_tests" not in code:
            return False

        # 2. Verify that actual code changes exist (avoid early step 1 exit)
        if not has_patch:
            return False

        output_lower = output.lower()

        # 3. MBPP benchmark check
        if benchmark == "mbpp":
            return '"success": true' in output_lower

        # 4. SWE-bench evaluation check
        exit_zero = "exit code: 0" in output_lower
        no_failure = (
            "failed" not in output_lower
            and "failures" not in output_lower
            and "error" not in output_lower
        )
        has_passed = "passed" in output_lower or "pass" in output_lower

        return exit_zero and (has_passed or no_failure)

    @staticmethod
    def clean_and_truncate(
        code: str, output: str, head_lines: int = 40, tail_lines: int = 60
    ) -> str:
        """Remove conda bash debug noise and truncate long observations.

        Parameters
        ----------
        code : str
            The python code executed in the sandbox.
        output : str
            The raw observation output to sanitize.
        head_lines : int
            Number of initial lines to preserve.
        tail_lines : int
            Number of trailing lines to preserve.

        Returns
        -------
        str
            The sanitized and potentially truncated observation.
        """
        lines = output.splitlines()

        # Only strip bash debug traces if run_tests or bash commands ran.
        # NEVER strip lines starting with '+' on get_patch/diff outputs!
        if "run_tests" in code or "run_command" in code:
            lines = [
                line
                for line in lines
                if not line.startswith(("+ ", "++ ", "+++ "))
            ]

        max_lines = head_lines + tail_lines
        if len(lines) <= max_lines:
            return "\n".join(lines)

        head = lines[:head_lines]
        tail = lines[-tail_lines:]
        omitted = len(lines) - max_lines

        truncation_marker = (
            f"\n\n... [OUTPUT TRUNCATED: {omitted} lines omitted "
            "to save context] ...\n\n"
        )
        return "\n".join(head) + truncation_marker + "\n".join(tail)

    @staticmethod
    def build_test_success_feedback(observation: str) -> str:
        """Build urgent feedback informing the agent that all tests passed."""
        return (
            f"{observation}\n\n"
            "[CRITICAL NOTICE: ALL TESTS PASSED SUCCESSFULLY!]\n"
            "Your fix is verified. Do NOT modify tests or refactor further.\n"
            "Inspect your diff with print(get_patch()) then submit immediately "
            "using: final_answer(get_patch())"
        )
