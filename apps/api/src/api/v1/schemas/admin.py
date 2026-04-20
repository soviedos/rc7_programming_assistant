from pydantic import BaseModel


class AdminStatusResponse(BaseModel):
    manuals_indexed: int
    active_users: int
    pending_jobs: int
