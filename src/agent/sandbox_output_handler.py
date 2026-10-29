"""Module to inspect, clean, and truncate sandbox outputs."""

from typing import Any


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

    @staticmethod
    def build_patch_confirmed_feedback(observation: str) -> str:
        """Build urgent feedback informing the agent that diff is ready."""
        return (
            f"{observation}\n\n"
            "[PATCH CONFIRMED - READY FOR SUBMISSION]\n"
            "Your diff is verified and repository tests have already passed.\n"
            "Do NOT run further searches, edits, or tests.\n"
            "Submit your solution now using: final_answer(get_patch())"
        )

    @staticmethod
    def get_no_code_feedback(benchmark: str = "mbpp") -> str:
        """Build feedback when no Python code block was detected in model output."""
        if benchmark == "mbpp":
            return (
                "Error: No executable Python code block was detected in your response.\n"
                "You MUST wrap your Python code in ```python\n<code here>\n```.\n"
                "If you have completed the solution, call final_answer(solution_code)."
            )
        return (
            "Error: No executable Python code block detected.\n"
            "Wrap your Python code in ```python\n<code here>\n```.\n"
            "If you have completed the fix, call final_answer(get_patch())."
        )

    @classmethod
    def get_mbpp_feedback(cls, code: str, sand_answer: dict[str, Any]) -> str:
        """Analyze sandbox output for MBPP and return appropriate prompt feedback."""
        status = sand_answer.get("status")
        if status == "success":
            raw_obs = sand_answer.get("output", "").strip()
            observation = cls.clean_and_truncate(code, raw_obs)
            print("\n👁️  [Observation Output]:")
            print(observation if observation else "(No stdout output)")

            if not observation:
                return (
                    "Warning: You defined a function but did NOT print "
                    "any test results and did NOT call final_answer().\n"
                    "To proceed, you MUST either test your function:\n"
                    "  res = run_tests(candidate, tests)\n"
                    "  print(res)\n"
                    "Or call final_answer(solution_code) if you are sure it works."
                )

            if cls.is_test_run_finished(
                code, observation, has_patch=True, benchmark="mbpp"
            ):
                print(
                    "🎯 MBPP tests passed! Forcing agent to submit final_answer."
                )
                return (
                    f"{observation}\n\n"
                    "[CRITICAL NOTICE: ALL TESTS PASSED!]\n"
                    "All assertions passed. You are done!\n"
                    "Submit your final solution immediately: "
                    "final_answer(solution_code)"
                )

            return observation

        raw_error = (
            sand_answer.get("error") or "Execution failed without details."
        )
        error_trace = cls.clean_and_truncate(code, raw_error)
        partial_output = sand_answer.get("output", "").strip()
        if partial_output:
            cleaned_partial = cls.clean_and_truncate(code, partial_output)
            error_trace += (
                f"\n\n[PARTIAL OUTPUT BEFORE INTERRUPTION]:\n{cleaned_partial}"
            )
        print("\n" + "!" * 50)
        print("❌ FAILED: Error detected in sandbox:")
        print("-" * 50)
        print(f"{error_trace}")
        print("-" * 50)
        print(
            "🔄 Feeding code and error trace back to prompt for next iteration..."
        )
        print("!" * 50 + "\n")
        return f"Execution Error:\n{error_trace}"

    @classmethod
    def get_swebench_feedback(
        cls,
        code: str,
        sand_answer: dict[str, Any],
        tests_passed: bool = False,
        has_patch: bool = False,
    ) -> tuple[str, bool]:
        """Analyze sandbox output for SWE-bench and return (feedback, tests_passed)."""
        status = sand_answer.get("status")
        if status == "success":
            raw_obs = sand_answer.get("output", "").strip()
            observation = cls.clean_and_truncate(code, raw_obs)
            print("\n👁️  [Observation Output]:")
            print(observation if observation else "(No stdout output)")

            if cls.is_test_run_finished(
                code, observation, has_patch=has_patch, benchmark="swebench"
            ):
                print("🎯 Tests passed! Forcing agent to inspect and submit.")
                return cls.build_test_success_feedback(observation), True

            if (
                tests_passed
                and "get_patch" in code
                and ("diff --git" in observation or "--- a/" in observation)
            ):
                print("🎯 Patch confirmed after tests! Forcing final_answer.")
                return (
                    cls.build_patch_confirmed_feedback(observation),
                    tests_passed,
                )

            if not observation:
                return (
                    "Code executed successfully with no printed output.\n"
                    "Remember to print() tool results, or verify changes "
                    "with print(get_patch()).",
                    tests_passed,
                )

            return observation, tests_passed

        raw_error = sand_answer.get("error") or "Unknown execution error."
        error_trace = cls.clean_and_truncate(code, raw_error)
        partial_output = sand_answer.get("output", "").strip()
        if partial_output:
            cleaned_partial = cls.clean_and_truncate(code, partial_output)
            error_trace += (
                f"\n\n[PARTIAL OUTPUT BEFORE INTERRUPTION]:\n{cleaned_partial}"
            )
        print("\n" + "!" * 50)
        print("❌ FAILED: Error detected in sandbox:")
        print(f"{error_trace}")
        print("!" * 50 + "\n")
        return (
            f"Execution error:\n{error_trace}\nFix your code and try again.",
            tests_passed,
        )
