from datetime import date
from pydantic import BaseModel, ConfigDict, Field, model_validator

class TournamentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    location: str = Field(min_length=2, max_length=200)
    start_date: date
    end_date: date
    description: str | None = None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_date < self.start_date:
            raise ValueError("End date cannot be earlier than start date")
        return self
    
class TournamentResponse(TournamentCreate):
    id: int
    database_status: str
    
    model_config = ConfigDict(from_attributes=True)

