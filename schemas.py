from typing import List, Optional

from pydantic import BaseModel, HttpUrl


from pydantic import BaseModel, HttpUrl, ConfigDict

class RepositoryBase(BaseModel):
    name: str
    html_url: HttpUrl
    description: Optional[str] = None
    language: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)



class UserSyncResponse(BaseModel):
    username: str
    status: str  
    is_new: bool
    repositories: List[RepositoryBase]
