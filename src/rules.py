"""Execution rules and resource limits for MBPP and SWE-bench benchmarks."""


class RulesMbpp:
    """Resource limits and iteration bounds for MBPP algorithmic tasks."""

    def __init__(self, iteration: int | None = 10) -> None:
        """Initialize MBPP rules with max iterations, tokens, and timeout."""
        self.iterations = iteration or 10
        self.input_tokens = 6000
        self.output_tokens = 1500
        self.timeout = 120


class RulesSwe:
    """Resource limits and iteration bounds for SWE-bench engineering tasks."""

    def __init__(self, iteration: int | None = 30) -> None:
        """Initialize SWE-bench rules with max iterations, tokens, and timeout."""
        self.iterations = iteration or 30
        self.input_tokens = 300000
        self.output_tokens = 10000
        self.timeout = 900
