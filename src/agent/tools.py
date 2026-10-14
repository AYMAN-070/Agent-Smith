from typing import Callable


def create_task_specific_run_test(secret_asserts: list[str]) -> Callable:
    """
    Creates a run_test function specifically tailored for the current LLM task.
    This is the real tool injected into the Sandbox.
    """

    def run_test(target_function: Callable) -> str:
        passed = 0
        total = len(secret_asserts)
        errors = []

        for assert_str in secret_asserts:
            try:
                test_env = {target_function.__name__: target_function}

                exec(assert_str, test_env)
                passed += 1
            except AssertionError:
                errors.append(f"Error : {assert_str}")
            except Exception as e:
                errors.append(f"Execution error '{type(e).__name__}' on : {assert_str}")

        if passed == total:
            return f"Success: {passed}/{total} tests passed. You can now call final_answer()."
        else:
            return f"Failed: {passed}/{total} tests passed.\nDetails:\n" + "\n".join(errors)

    return run_test
