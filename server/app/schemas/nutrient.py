from pydantic import BaseModel


class NutrientReferenceOut(BaseModel):
    code: str
    display_name: str
    unit: str
    category: str

    model_config = {"from_attributes": True}
