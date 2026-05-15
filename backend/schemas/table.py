from pydantic import BaseModel, ConfigDict


class TableOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    TableID: int
    TableNo: str
    TableName: str | None
    Seats: int | None
    TableStatus: str
