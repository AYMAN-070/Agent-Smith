import json
from typing import List, Dict, Any


def run_tests(code: str, test_list: List[str]) -> str:
    """
    Run candidate Python code against a list of test assertions
    """
    execution_namespace: Dict[str, Any] = {}
    try:
        exec(code, execution_namespace)
    except Exception as e:
        return json.dumps({
            "success": False,
            "output": f"Code execution failed ({type(e).__name__}): {e}"
        })

    passed = 0
    total = len(test_list)
    failed_details: List[str] = []

    for assertion in test_list:
        try:
            exec(assertion, execution_namespace)
            passed += 1
        except AssertionError:
            failed_details.append(f"Assertion failed: {assertion}")
        except Exception as e:
            failed_details.append(f"Test error on '{assertion}' ({type(e).__name__}): {e}")

    if passed == total:
        return json.dumps({
            "success": True,
            "output": f"All {total} tests passed successfully."
        })
    else:
        return json.dumps({
            "success": False,
            "output": f"{passed}/{total} tests passed. Failures:\n" + "\n".join(failed_details)
        })
