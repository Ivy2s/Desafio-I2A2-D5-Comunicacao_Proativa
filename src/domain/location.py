from pydantic import BaseModel, ConfigDict, Field, FiniteFloat


class Location(BaseModel):
    """Localização compartilhada pelos domínios meteorológico e de seguros."""

    model_config = ConfigDict(extra="forbid")

    latitude: FiniteFloat = Field(ge=-90, le=90)
    longitude: FiniteFloat = Field(ge=-180, le=180)
    municipality: str | None = None
