"""
main.py: Application entry point that creates the application
"""
import json
from dotenv import load_dotenv
import json
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
from database import create_db_and_tables

app = FastAPI() # App initialization
env_variable = load_dotenv() # Loads environment variable
client = OpenAI() # Initializes openAI client

@app.on_event("startup") # Initializes DB on start up
def on_startup():
    create_db_and_tables()

class UserRequirement(BaseModel):
    requirement: str

# Validates LLM Report as JSON, returns an integer
class JsonReport(BaseModel):
    report: dict # Returned as JSON by LLM, passed in as dict in function call
    req_score: int


@app.post("/analyze", response_model=JsonReport) # <--- Analyze Endpoint(POST Method), JSON Report = Output/Response Endpoint Expects 
def report_generation(request: UserRequirement):
    # Prompt Engineering
    prompt = f""" 
    TASK1: Identify the functional and non-functional portions of the given software requirement
    TASK1 DEFINITIONS:
    - Functional: Describes what the system should do, its behavior
    - Non-Functional: Describe the constraints under which the system should behave
    TASK1 CONSIDERATIONS:
    - If either a functional or non-functional portion is not present, output N/A
    
    TASK2: Classify the ambiguity level of the requirement as either low, medium or high
    TASK2 CRITERIA:
    - High: requirement contains 4 or more ambigious words/phrases
    - Medium: requirement contains 3 or less ambigious words/phrases
    - Low: requirement contains no ambigious words/phrases

    TASK3: Classify whether or not the requirement is written in active voice structure
    TASK3 DEFINITION:
    - Requirements written in active voice follow this sequence: agent + verb + target
    - Agent = The actor, the main subject
    - Verb = the action being done
    - Target = the subject being acted upon

    OUTPUT: Structured JSON
    "Respond ONLY in JSON format as specified. Do not include explanations or extra text. Do not use code fences"
    {{
        "functional_portion": "Exact portion of the requirement describing system behavior",
        "non_functional_portion": "Exact portion describing constraints or quality attributes",
        "ambiguity_level": "High, Medium, or Low",
        "active_voice": "Yes or No"
    }}
    

    Requirement:
    {request.requirement}
    """

    response = client.responses.create(model = "gpt-4o-mini", input = prompt) 
    
    # Tries loading JSON data
    try:
        report = json.loads(response.output_text)
    # Outputs LLM response if not JSON
    except json.JSONDecodeError:
        return {
            "error": "LLM returned invalid JSON",
            "raw_output": response.output_text
        }
    
    req_score = overall_score(report)
    
    return {"report": report, 
            "req_score": req_score}


# Add a function to generate an overall score based on LLM generations
def overall_score(report: dict) -> int: 
    req_score = 0

    #Attribute 20 points for present functional portion
    if report.get("functional_portion") != "N/A":
        req_score +=20
    
    # Attribute 20 points for present non-function portion
    if report.get("non_functional_portion") != "N/A":
        req_score +=20
    
    # Attribute 10 points for high ambiguity
    if report.get("ambiguity_level") == "High":
        req_score +=10
    
    # Attribute 20 points for medium ambiguity
    elif report.get("ambiguity_level") == "Medium":
        req_score +=20

    # Attribute 30 points for low ambiguity
    elif report.get("ambiguity_level") == "Low":
        req_score +=30
        
    # Attribute 30 points for requirement written in active voice
    if report.get("active_voice") == "Yes":
        req_score +=30
    
    # Attribute 15 points for requirement lacking active voice structure
    elif report.get("active_voice") == "No":
        req_score +=15
    
    return req_score