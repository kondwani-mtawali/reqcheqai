"""
DB Models
"""
from sqlmodel import SQLModel, Field
# -------------------------------------------------------------------------------------
# Table Model/Config: id, inputted user req, llm generated report, calculated req_score
class RequirementAnalysis(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_req: str = Field(index = True)
    report: str = Field(index = True)
    req_score: int = Field(default=None, index=True)
# --------------------------------------------------------------------------------------

