import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict


class ProjectKeyResolutionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: uuid.UUID
    project_id: uuid.UUID
    key_type: Literal["ingest"] = "ingest"
    active: bool = True

