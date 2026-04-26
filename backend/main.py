"""
main.py: Application entry point that creates the application
"""

import json
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
from database import create_db_and_tables, create_report, get_session, read_report
from fastapi.middleware.cors import CORSMiddleware
import spacy
import textstat
from models import RequirementAnalysis

load_dotenv()  # Loads environment variable
nlp = spacy.load("en_core_web_sm") # load spacy's pre-trained model
client = OpenAI()  # Initializes openAI client

app = FastAPI()  # App initialization

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")  # Initializes DB on start up
def on_startup():
    create_db_and_tables()


class UserRequirement(BaseModel):
    requirement: str

# Validates LLM Report as JSON, returns an integer
class JsonReport(BaseModel):
    reqcheq_id: int
    report: dict  # Returned as JSON by LLM, passed in as dict in function call
    atomicity_score: int # Spacy --> Counts verbs in the requirement. A good requirement describes one feature at a time
    measurability_score: int # Spacy --> measures the presence of numbers, units, and keywords
    complexity_score: int # Spacy --> measures requiremetn length, number of clauses, and verb count
    readability_score: int # textStat --> Flesch Reading Ease: a formula that calculates text readability, see formula above method
    req_score: int

@app.post("/analyze", response_model=JsonReport)  # <--- Analyze Endpoint(POST Method), JSON Report = Output/Response Endpoint Expects
def report_generation(request: UserRequirement):
    # Prompt Engineering
    prompt = f""" 
    TASK1: Identify whether the requirement is a functional requirement, a non-functional requirement, or both.
    TASK1 DEFINITIONS:
    - Functional: Describes what the system should do, its behavior(the what)
    - Non-Functional: Describe the constraints under which the system should behave(the how)
    - Functional + Non-Functional: Describes both what the system should do and under what conditions the system must do it
    TASK1 CONSIDERATIONS: If the requirement includes both Functional and Non-Functional information, output Functional + Non-Functional
    TASK 1 OUTPUT: Functional || Non-Functional || Functional + Non-Functional

    TASK2: Identify the functional and non-functional portions of the given software requirement and output the separate portions
    TASK2 DEFINITIONS:
    - Functional: Describes what the system should do, its behavior
    - Non-Functional: Describe the constraints under which the system should behave
    TASK2 CONSIDERATIONS:
    - If either a functional or non-functional portion is not present, output N/A
    TASK2 OUTPUT: The mimic of the functional and/or non-functional portion of the requirement

    TASK3: Identify the class the software requirement is being referred to in the requirement
    TASK3 DEFINITIONS:
    - Functional: A software requirement without any specification of constraints or the conditions the feature must satisfy
    - Performace: Describes how efficiently the system operates under specific conditions, including speed, responsiveness, and resource usage
    - Security: Describes how the system protects data and prevents unauthorized access or misuse.
    - Usability: Describes how easy and intuitive the system is for users to interact with.
    - Maintainability: Describes how easily the system can be modified, updated, or extended over time.
    - Reliability: Describes the system's ability to operate consistently without failure over time.
    TASK3 CONSIDERATIONS: 
    - A software requirement is capable of referencing multiple non-functional categories(e.g., Performance and Security)
    - A software requirement may not have any non-functional components to it, resulting in being classified as Functional 
    TASK3 OUTPUT: Output one, or multiple, classes the software requirement belongs to, or just "Functional" if there's no non-functional portion to the requirement
    
    TASK 3: Assign an ambiguity score to the requirement on a scale from 0 to 100.
    DEFINITION:
    - 0-33 (High Ambiguity): vague, subjective, multiple interpretations, not directly implementable
    - 34-66 (Moderate Ambiguity): partially clear but missing precision or detail
    - 67-100 (Low Ambiguity): clear, precise, measurable, directly implementable

    EVALUATION PROCESS (MANDATORY):
    Evaluate the requirement using the following signals:

    1. Vague Language:
    Does the requirement include vague or subjective terms (e.g., "fast", "efficient", "user-friendly")?
    → Yes = increases ambiguity

    2. Measurable Criteria:
    Does the requirement include numbers, thresholds, or constraints?
    → Yes = reduces ambiguity

    3. Clarity of Behavior:
    Is the system behavior clearly defined and specific?
    → No = increases ambiguity

    4. Implementability:
    Could a developer implement this requirement without making assumptions?
    → No = increases ambiguity

    SCORING INSTRUCTIONS:
    - Start at 50 (moderate ambiguity)
    - Add +10 to +20 for each factor that reduces ambiguity
    - Subtract −10 to −20 for each factor that increases ambiguity
    - Clamp final score between 0 and 100


    TASK4: Classify whether or not the requirement is written in active voice structure
    TASK4 DEFINITION:
    - Requirements written in active voice follow this sequence: agent + verb + target
    - Agent = The actor, the main subject
    - Verb = the action being done
    - Target = the subject being acted upon
    TASK4 OUTPUT: Yes or No. 

    OUTPUT: Structured JSON
    "Respond ONLY in JSON format as specified. Do not include explanations or extra text. Do not use code fences"
    {{
        "type:" "Functional or Non-Functional, or Functional + Non-Functional",
        "functional_portion": "Exact portion of the requirement describing system behavior",
        "non_functional_portion": "Exact portion describing constraints or quality attributes",
        "class:" "Functional, Performance, Security, Usability, Maintainability, Reliability, or N/A",
        "ambiguity_score": "0-100",
        "active_voice": "Yes or No"
    }}
    

    Requirement:
    {request.requirement}
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini", 
        messages=[{"role": "user", "content": prompt}], 
        temperature=0.0, 
        response_format={"type": "json_object" }
    )

    # Tries loading JSON data
    try:
        report_dict = json.loads(response.choices[0].message.content)
    # Outputs LLM response if not JSON
    except json.JSONDecodeError:
        return {
            "error": "LLM returned invalid JSON",
            "raw_output": response.choices[0].message.content,
        }
    
    atomicity = atomicity_score(request.requirement)
    measurability = measurability_score(request.requirement)
    complexity = complexity_score(request.requirement)
    readability = readability_score(request.requirement)

    # Computes the requirement overall
    req_score = overall_score(report_dict, atomicity, measurability, complexity, readability)

    """
    Database Save Portion:
    - Define the reqcheq being saved
    - Initialize the session being worked on
    - Create the report(save to the database)
    """
    reqcheq = RequirementAnalysis(user_req=request.requirement, report=json.dumps(report_dict), 
                                  atomicity_score=atomicity, measurability_score=measurability,
                                  complexity_score=complexity, readability_score=readability, req_score=req_score )
    session_gen = get_session()
    session = next(session_gen)
    db_save = create_report(reqcheq, session=session) # Save report to DB
    session.add(db_save)
    session.commit()

    return {"reqcheq_id": db_save.id, # id to eventually pass to feedback endpoint
            "report": report_dict, 
            "atomicity_score": atomicity,
            "measurability_score": measurability,
            "complexity_score": complexity,
            "readability_score": readability,
            "req_score": req_score}

def atomicity_score(text: str):
    """
    Calculates an atomicity score. Good requirements describe one feature, counting verbs informs
    how many features the requirement is specifying for implementation.
    """
    doc = nlp(text)

    # token = smallest analytical unit processed in spacy(word,symbol,etc.)
    verbs = [token.lemma for token in doc if token.pos_ == "VERB"] # Counts all the verbs in the requirement

    # Assigning an atomicity score based on number of verbs
    if len(verbs) == 0:
        return 0
    elif len(verbs) <= 4:
        return 100
    elif len(verbs) == 5:
        return 50
    elif len(verbs) >= 6:
        return 25
    
def measurability_score(text: str):
    """
    Computes a measurability score by searching through the requirement and observing whether it contains
    a list of units, keywords, and/or spacy's like_num attribute. Spacy's like_num finds descriptions of 
    numbers(.e.g. "hundreds", "ten", etc.). Measurable requirements are good requirements 
    - like_nums get 40 points
    - units get 40 points
    - keywords get 20 points
    - returns a number that can't exceed 100   
    """
    UNITS = {"seconds", "ms", "milliseconds", "%", "percent", "users", "requests"} # common unit terms we may see in requirements
    KEYWORDS = {"within", "at least", "at most", "no more than"} # keywords/phrases that imply measurement

    doc = nlp(text)

    score = 0

    # spacy like_num attribute
    if any(token.like_num for token in doc): 
        score += 40

    if any(token.text.lower() in UNITS for token in doc):
        score += 40

    if any(keyword in text.lower() for keyword in KEYWORDS):
        score += 20

    return min(score, 100) # ensures score doesn't exceed 100, might fix later

def complexity_score(request: UserRequirement):
    """
    Computes a complexity score of the requirement based on the sentence length, the number of verbs, and the number of clauses.
    The more complex a sentence, the longer it is, the more verbs it contains, the more clauses it contains. Making requirements
    precise and direct are important for implementation. 
    """
    
    doc = nlp(request)
    clause_count = sum(1 for token in doc if token.dep_ in ["advcl", "ccomp", "xcomp", "acl", "relcl"]) # Spacy labels that detect types of cluases
    if clause_count <=2:
        return 100
    elif clause_count == 3:
        return 70
    elif clause_count == 4:
        return 50
    elif clause_count > 4:
        return 30    

def readability_score(text: str):
    """
    Utilizes textstat's Flesch Reading Ease function. A formula that calculates text readability based on sentence 
    length and word length (syllables). Formula: 
    206.835 - (1.015 x ASL) - (84.6 x ASW)
    ASL = Average Sentence Length (total words / total sentences).
    ASW = Average Syllables per Word (total syllables / total words). The scoring system per docs:
    90-100 = Very Easy to read; 80-89 = Easy to read; 70-79 = fairly easy; 60-69 = standard; 50-59 = fairly difficult
    30-49 = difficult; 0-29 = confusing

    """
    readability_score = round(textstat.flesch_reading_ease(text))
    return readability_score

# Add a function to generate an overall score based on LLM generations
def overall_score(report: dict, atomicity: int, measurability: int, complexity: int, readability: int) -> int:
    """
    Computes the overall score of the requirement. Not necessary, more fun than anything else.
    """
    
    req_score = 0
    
    # Type Scoring
    req_type = report.get("type")
    match req_type:
        case "Functional + Non-Functional":
            req_score +=15
        case "Functional": 
            req_score +=5
        case "Non-Functional":
            req_score +=5

    # Function Portion Scoring
    functional_portion = report.get("functional_portion")
    match functional_portion:
        case "N/A":
            req_score -= 10
        case _:
            req_score += 5

    # Non-Function Portion Scoring
    non_functional_portion = report.get("non_functional_portion")
    match non_functional_portion:
        case "N/A":
            req_score -= 10
        case _:
            req_score += 10

    # Class Scoring
    req_class = report.get("class")
    match req_class:
        case "Functional":
            req_score +=5
        case _:
            req_score +=10
    
    # Ambiguity Scoring
    ambiguity = int(report.get("ambiguity_score"))
    if ambiguity <= 33: 
        req_score +=0
    elif 33 < ambiguity <= 66:
        req_score += 5
    elif 66 < ambiguity <= 100:
        req_score += 10  

    # Active Voice Scoring
    active_voice = report.get("active_voice")
    match active_voice:
        case "Yes":
            req_score += 10
        case "No":
            req_score += 0

    # Atomicity Scoring
    match atomicity:
        case 0:
            req_score += 0
        case 100:
            req_score += 10
        case 50:
            req_score += 5
        case 25:
            req_score += 3

    # Measurability Scoring
    if measurability <= 40:
        req_score += 0
    elif 41 < measurability <= 80:
        req_score += 5
    else:
        req_score += 10
    
    # Complexity Scoring
    if complexity < 50:
        req_score += 5
    elif complexity >= 50:
        req_score += 10

    # Readability Scoring
    if readability < 5:
        req_score += 0
    elif 6 < readability <= 30:
        req_score += 5
    elif readability > 30:
        req_score += 10

    return req_score

@app.get("/dbaccess")
def visualize_metrics():
    return 0

class LLMFeedback(BaseModel):
    reqcheq_id: int

@app.post("/feedback")
def llm_feedback(data: LLMFeedback):
    """Generates feedback and suggest requirement changes to the user"""

    # Retrieve the req_cheq using read_report
    session_gen = get_session()
    session = next(session_gen)
    saved_report = read_report(reqcheq_id=data.reqcheq_id, session=session)
    if not saved_report:
        return {"Error:" "Report Not Found"}
    
    json_report = json.loads(saved_report.report)

    prompt = f""" 
    You're currently acting as a Senior Software Developer & Software Requirement Analysis Expert. You will be given a requirement,
    your task is to take a given software requirement, provide the user with feedback on how they must improve it, taking into account 
    the analysis report of that requirement that has been previously generated. 

    The Software Requirement being analyzed:
    {saved_report.user_req}
    - The Analysis Report of that Requirement:
    - The type of software requirement: {json_report.get('type')}
    - The functional portion of the requirement: {json_report.get('functional_portion')}
    - The non-functional portion of the requirement: {json_report.get('non_functional_portion')}
    - The class of non-functional requirements the requirement falls under: {json_report.get('class')}
    - The ambiguity score(out of 100) given to the requirement: {json_report.get('ambiguity_score')}
    - Whether or not the requirement is written in active voice: {json_report.get('active_voice')}
    - The atomicity score(out of 100) given to the requirement: {saved_report.atomicity_score}
    - The measurability score(out of 100) given to the requirement: {saved_report.measurability_score}
    - The complexity score(out of 100) given to the requirement: {saved_report.complexity_score}
    - The readability score(out of 100) given to the requirement: {saved_report.readability_score}
    - The overall requirement score given to the requirement: {saved_report.req_score}   

    - Generate/Output the following in JSON format. ONLY in JSON format as specified. Do not include explanations or extra text. Do not use code fences
    1) Begin with a short/minimal disclaimer that this is an AI generated analysis
    2) Provide general constructive feedback on the requirement, limit to 200 words
    3) Explain what is good about the software requirement, limit to 200 words
    4) Explain what was done poorly about the software requirements, limit to 200 words
    5) Suggest changes the user should make to the requirement in order to fix it, limit to 200 words
    6) Provide the user with an improved version of their originally inputted software requirement, limit to 200 words
    
    OUTPUT FORMAT:
    {{
        "disclaimer:" "AI Generated Feedback
        "feedback:" "provide general constructive feedback, limit to 200 words",
        "requirement_strengths": "speak about what the requirement does well, limit to 200 words",
        "requirement_weaknesses": "speak about what the requirement does poorly, limit to 200 words",
        "suggestions:" "walk over suggestions the user could make to improve their requirement, limit to 200 words",
        "improved_version": "Revise and rewrite an improved version of the software reuirement, keep it atomic",
    }}
    
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini", 
        messages=[{"role": "user", "content": prompt}], 
        temperature=0.0, 
        response_format={"type": "json_object" }
    )

    # Tries loading JSON data
    try:
        feedback_dict = json.loads(response.choices[0].message.content)
        print(feedback_dict)
    # Outputs LLM response if not JSON
    except json.JSONDecodeError:
        return {
            "error": "LLM returned invalid JSON",
            "raw_output": response.choices[0].message.content,
        }

    return feedback_dict




