import pandas as pd

class PandasUtils:
    @staticmethod
    def is_not_empty(cell) -> bool:
        if isinstance(cell, pd.Series):
            return pd.notna(cell).any()
        return pd.notna(cell)

    @staticmethod
    def as_string(cell) -> str:
        if isinstance(cell, pd.Series):
            return str(cell.apply(lambda x: str(x) if pd.notna(x) else ''))
        return str(cell) if pd.notna(cell) else ''


