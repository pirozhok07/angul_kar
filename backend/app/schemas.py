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

class AthleteCreate(BaseModel):
    first_name: str = Field(min_length=2, max_length=100)
    second_name: str | None = Field(default=None, min_length=2, max_length=100)
    last_name: str = Field(min_length=2, max_length=100)
    birth_date: date
    gender: str = Field(min_length=2, max_length=7)
    weight: float | None = Field(default=None, ge=0, le=999.99)
    weight_fact: float | None = Field(default=None, ge=0, le=999.99)
    rank_kyu: str | None = Field(max_length=5)
    rank_sport: str | None = Field(max_length=5)
    
class AthleteResponse(AthleteCreate):
    id: int
    registration_status: str
    
    model_config = ConfigDict(from_attributes=True)