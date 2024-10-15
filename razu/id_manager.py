class IDManager:
    """ 
    Class ensures IDs are unqiue. IDs in this context are simple integers.
    """
    def __init__(self):
        self.used_ids = set()
        self.current_id = 0 

    def generate_id(self) -> int:
        self.current_id += 1
        while self.current_id in self.used_ids:
            self.current_id += 1
        self.used_ids.add(self.current_id)
        return self.current_id

    def register_id(self, entity_id: int) -> int:
        if entity_id in self.used_ids:
            raise ValueError(f"ID {entity_id} is already used.")
        self.used_ids.add(entity_id)
        return entity_id

    def is_used(self, entity_id) -> bool:
        return entity_id in self.used_ids
    
    def get_count(self):
        return len(self.used_ids)

    def reset(self):
        self.used_ids.clear()
        self.current_id = 0
