from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class Listing:
    id: str                          # unique id (market + gift id)
    name: str
    number: Optional[str]            # #12345
    price_ton: float
    market: str                      # MRKT / Portals / Getgems
    url: str
    image_url: Optional[str] = None
    is_black_backdrop: bool = False
    listed_at: Optional[datetime] = None
    model: Optional[str] = None
    backdrop: Optional[str] = None

    @property
    def display_name(self) -> str:
        if self.number:
            return f"{self.name} #{self.number}"
        return self.name