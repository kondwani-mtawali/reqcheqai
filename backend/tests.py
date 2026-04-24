# tests.py
from fastapi.testclient import TestClient
from main import app
import unittest
import json
from sqlmodel import SQLModel
from models import RequirementAnalysis
from database import create_db_and_tables, get_session, create_report, read_report, read_reports, delete_report, get_session

# Import App as a Test Client
client = TestClient(app)

create_db_and_tables() # Calls the function to create/initialize datbase

class TestDatabaseFunctions(unittest.TestCase):
    def test_db_save(self):
        """
        Tests that my DB function correctly saves the requirement analysis to the database
        Test cases written based on model. create_report DB function to be written based on docs.
        """
        
        # Dummy requirement to save in report
        requirement = "The system shall analyze the detected vulnerability. The system shall inspect SSL certificate.The system shall identify acceptable low false positive rates. The system shall allow multiple clients to login and save their files to the remote server!"
        
        # Dummy report based on the requirement above
        report = {
            "report": {
                "functional_portion": "The system shall analyze the detected vulnerability. The system shall inspect SSL certificate. The system shall allow multiple clients to login and save their files to the remote server.",
                "non_functional_portion": "The system shall identify acceptable low false positive rates.",
                "ambiguity_level": "Medium",
                "active_voice": "Yes"
            },
            "req_score": 90
                }
        db_entry = RequirementAnalysis(user_req = requirement, report = json.dumps(report), req_score=90) # Report must be string for DB

        # Call DB Function 
        session_gen = get_session() # Session = temporary workspace
        session = next(session_gen) # database.py generates sessions
        db_save = create_report(reqcheq=db_entry, session=session)
        session.commit()

        # Unnittest assertions
        self.assertIsNotNone(db_save.id, "Should receive an id") # ensure the ID is valid 
        self.assertEqual(db_save.user_req, requirement) # ensure the requirement matches the user requirement
        self.assertEqual(db_save.req_score, 90) # ensure the score is 90
        self.assertIsInstance(db_save.report, str) # ensure the report is a string
        
    #def get_db_reports(self):

        
        
if __name__ == "__main__":
    unittest.main(verbosity=2)
