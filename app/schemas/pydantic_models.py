from typing import Optional, List

from pydantic import BaseModel, Field


class UpdateConfig(BaseModel):
    multiplier: Optional[int | float] = Field(default=1)
    suppliers_to_update: Optional[List[str]] = Field(default=None)
    oferta_ids_to_process: Optional[List[str]] = Field(default=None)
    allegro_token_id: int


