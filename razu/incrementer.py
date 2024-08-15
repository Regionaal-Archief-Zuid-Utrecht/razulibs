class Incrementer:
    def __init__(self, start_number: int):
        self.current_number = start_number - 1

    def next(self) -> int:
        self.current_number += 1
        return self.current_number
