from dataclasses import dataclass

@dataclass
class SelectedCell:
    area: str  # "inner" or "ring"
    r: int
    c: int