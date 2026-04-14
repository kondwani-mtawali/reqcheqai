"""
Kondwani 04/12: DB configuration to save user requirements and generated report
"""

from typing import Annotated

from fastapi import Depends, HTTPException, Query
from sqlmodel import Session, SQLModel, create_engine, select

from models import RequirementAnalysis # Imports the model

from main import app

# ------------------------------------------------------------------------------
# Engine: holds the connections to the DB. Only one engine boject exists per DB
sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)
# ------------------------------------------------------------------------------

# Function that creates the tables for the table model above
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

# Session: stores objects to memory and keeps track of changes
def get_session():
    with Session(engine) as session:
        yield session # provides a new session for each request...

SessionDep = Annotated[Session, Depends(get_session)] 


"""
Database Functions Below. Written using FastAPI SQL(Relational) Databases Docs
"""
# On application start, create the DB
@app.on_event("startup")
def on_startup():
    create_db_and_tables()

# Writes a requirement report to DB
# Same annotations as Pydantic model
# Session dependency used to add new reqcheq to the Session instance
#@app.post("/reqcheqs/")
def create_report(reqcheq: RequirementAnalysis, session: Session = Depends(get_session)) -> RequirementAnalysis:
    session.add(reqcheq)
    session.commit()
    session.refresh(reqcheq)
    return reqcheq

# Gets all the requirement reports in DB
#@app.get("/reqcheqs/")
def read_reports(
    session: Session = Depends(get_session),
    offset: int = 0,
    limit: int = Query(default=100, le=100),
) -> list[RequirementAnalysis]:
    reqcheqs = session.exec(select(RequirementAnalysis).offset(offset).limit(limit)).all() # offset and limits paginate results
    return reqcheqs

# Gets a single requirement report from DB
#@app.get("/reqcheqs/{reqcheq_id}")
def read_report(reqcheq_id: int, session: Session = Depends(get_session)) -> RequirementAnalysis:
    reqcheq = session.get(RequirementAnalysis, reqcheq_id)
    if not reqcheq:
        raise HTTPException(status_code=404, detail="Requirement Analysis Not Found")

# Deletes specified requirement report 
#@app.delete("/reqcheqs/{reqcheq_id}")
def delete_report(reqcheq_id: int, session: Session = Depends(get_session)):
    reqcheq = session.get(RequirementAnalysis, reqcheq_id)
    if not reqcheq:
        raise HTTPException(status_code=404, detail="Requirement Analysis Not Found")
    session.delete(reqcheq_id)
    session.commit()
    return {"ok": True}