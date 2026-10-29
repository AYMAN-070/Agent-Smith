class RulesMpbb:
    def __init__(self) -> None:
        self.iterations = 10
        self.input_tokens = 6000
        self.output_tokens = 1500
        self.timeout = 120


class RulesSwe:
    def __init__(self) -> None:
        self.iterations = 30
        self.input_tokens = 300000
        self.output_tokens = 10000
        self.timeout = 900
