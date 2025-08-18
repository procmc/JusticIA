from typing import List, Optional
from pydantic import BaseModel

class IngestaItem(BaseModel):
    id: str
    texto: str
    metadata: Optional[dict] = None

class IngestaBatch(BaseModel):
    items: List[IngestaItem]

class ConsultaReq(BaseModel):
    query: str
    k: int = 3
