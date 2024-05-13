import os
from pydantic import BaseModel


class Settings(BaseModel):
    database_uri: str
    auth_token: str


settings = Settings(
    database_uri=os.environ.get("DATABASE_URI"),
    auth_token=os.environ.get("AUTH_TOKEN"),
)
