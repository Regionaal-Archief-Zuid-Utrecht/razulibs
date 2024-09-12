class Incrementer:
    """ A class to increment an integer value sequentially. """
    
    def __init__(self, start_number: int = 1):
        """ Initializes the `Incrementer` with a given starting number. """
        self.current_number = start_number - 1

    def next(self) -> int:
        """ Increments the current number by 1 and returns the updated value. """
        self.current_number += 1
        return self.current_number
