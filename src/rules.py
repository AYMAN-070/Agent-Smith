class RulesMbpp:
    def __init__(self, iteration: int | None = 10) -> None:
        self.iterations = iteration or 10
        self.input_tokens = 6000
        self.output_tokens = 1500
        self.timeout = 120


class RulesSwe:
    def __init__(self, iteration: int | None = 30) -> None:
        self.iterations = iteration or 30
        self.input_tokens = 300000
        self.output_tokens = 10000
        self.timeout = 900
