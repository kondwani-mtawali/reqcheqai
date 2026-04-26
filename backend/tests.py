import unittest
import json
from models import RequirementAnalysis
from sqlalchemy import text # <-- write SQL text to query/manipulate DB
from database import create_db_and_tables, get_session, create_report, read_report, read_all_reports
from main import atomicity_score, measurability_score, complexity_score, readability_score, overall_score

create_db_and_tables() # Calls the function to create/initialize datbase

class TestDatabaseFunctions(unittest.TestCase):
    def test_db_save(self):
        """
        Tests that my DB function correctly saves the requirement analysis to the database
        """
        
        # Dummy requirement to save in report
        requirement = "The system shall analyze the detected vulnerability. The system shall inspect SSL certificate. The system shall identify acceptable low false positive rates. The system shall allow multiple clients to login and save their files to the remote server!"
        
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
        session.refresh(db_save)
        db_save_id = db_save.id

        # Unnittest assertions
        self.assertIsNotNone(db_save.id, "Should receive an id") # ensure the ID is valid
        self.assertEqual(db_save.id, db_save_id, "Report ID should match") 
        self.assertEqual(db_save.user_req, requirement) # ensure the requirement matches the user requirement
        self.assertEqual(db_save.req_score, 90) # ensure the score is 90
        self.assertIsInstance(db_save.report, str) # ensure the report is a string
    
    def test_get_report(self):
        """
        Tests that the read_report DB function correctly retrieves a single report from the database
        """
        # Setup: Create and save a report first
        requirement = "The system shall log all user actions"
        report = {
            "report": {
                "functional_portion": "The system shall log all user actions",
                "non_functional_portion": "N/A",
                "ambiguity_level": "Low",
                "active_voice": "Yes"
            },
            "req_score": 95
        }
        db_entry = RequirementAnalysis(user_req=requirement, report=json.dumps(report), req_score=95)
        
        # Save the report
        session_gen = get_session()
        session = next(session_gen)
        saved_report = create_report(reqcheq=db_entry, session=session)
        session.add(saved_report)
        session.commit()
        session.refresh(saved_report)
        saved_id = saved_report.id
        
        # Call the read_report function
        saved_report = read_report(reqcheq_id=saved_id, session=session)
        
        # Assertions
        self.assertIsNotNone(saved_report, "Report should be found")
        self.assertEqual(saved_report.id, saved_id, "Report ID should match")
        self.assertEqual(saved_report.user_req, requirement, "Requirement should match")
        self.assertEqual(saved_report.req_score, 95, "Score should match")

    def test_get_all_reports(self):
        """Tests that the database functions successfully return all the reports in the DB"""

        requirement1 = "The system shall return all the contents of the database within ten milliseconds"
        report1 = {
            "report": {
                "functional_portion": "The system shall return all the contents of the database",
                "non_functional_portion": "within ten milliseconds",
                "ambiguity_level": "Low",
                "active_voice": "Yes"
            },
            "req_score": 100
        }
        
        db_entry1 = RequirementAnalysis(user_req=requirement1, report=json.dumps(report1), req_score=95)

        requirement2 = "The system shall post user requests to the server in a hashed format, ensuring user information stays confidential"
        report2 = {
            "report": {
                "functional_portion": "The system shall post user requests to the server in a hashed format",
                "non_functional_portion": "ensuring user information stays confidential",
                "ambiguity_level": "Low",
                "active_voice": "Yes"
            },
            "req_score": 100
        }
        
        db_entry2 = RequirementAnalysis(user_req=requirement2, report=json.dumps(report2), req_score=95)

        requirement3 = "The system should store user information in the database securely"
        report3 = {
            "report": {
                "functional_portion": "The system should store user information in the database",
                "non_functional_portion": "securely",
                "ambiguity_level": "High",
                "active_voice": "Yes"
            },
            "req_score": 80
        }
        
        db_entry3 = RequirementAnalysis(user_req=requirement3, report=json.dumps(report3), req_score=95)

         # Save the reports
        session_gen = get_session()
        session = next(session_gen)

        # Delete all existing rows in table from previous tests
        session.exec(text("DELETE FROM requirementanalysis")) # table name is lowercase in SQL statement
        session.commit()

        saved_report1 = create_report(reqcheq=db_entry1, session=session)
        saved_report2 = create_report(reqcheq=db_entry2, session=session)
        saved_report3 = create_report(reqcheq=db_entry3, session=session)

        session.add(saved_report1)
        session.commit()
        session.add(saved_report2)
        session.commit()
        session.add(saved_report3)
        session.commit()
        session.refresh(saved_report1)
        session.refresh(saved_report2)
        session.refresh(saved_report3)

        # After saving and committing all reports, call read_reports to retrieve them:
        all_reports = read_all_reports(session=session) # session is only required param
        
        # Now you can add assertions on the returned reports:
        self.assertEqual(len(all_reports), 3, "Should return all 3 reports")
        
        # Assert each requirement committed above exists in DB
        self.assertIn(requirement1, [r.user_req for r in all_reports], "Report 1 should be in results")
        self.assertIn(requirement2, [r.user_req for r in all_reports], "Report 2 should be in results")
        self.assertIn(requirement3, [r.user_req for r in all_reports], "Report 3 should be in results")
        
        # Add more specific assertions...Score? Functional/Non-Functional Components?         

class TestScoreComputations(unittest.TestCase):
    """
        Tests the computation of all the requirement scores. The intention is to have 4 scores. Each with their unique way
        of being computed.
        - Atomocity Score: computes a score out of 100 based on the verb count
        - Measurability Score: computes a score out of 100 based on numeric input provided in a requirement
        - Complexity Score: computes a score based on how well structured the requirement is(number of clauses)
        - Readability Score: computes a readability score based on the average sentence length and number of syllables per word
        """
    def test_atomicity_score(self):
        # Case 1: Low atomicity requirement(only two verbs)
        req1 = "The system shall inspect SSL certificate"
        score1 = atomicity_score(req1)
        self.assertIsInstance(score1, int) # Should return an integer
        self.assertEqual(score1, 100)
        
        # Case 2: Poorly written requirement with high atomicity
        req2 = "The system shall receive input, send it to the backend, run it through the script, validate the output, and save to the database"
        score2 = atomicity_score(req2)
        self.assertLess(score2, 100)
    
    def test_measurability_score(self):
        # Case 1: Requirement written with measurable components
        req1 = "The system shall output the text to the user within 4 seconds of post request"
        score1 = measurability_score(req1)
        self.assertIsInstance(score1, int)
        self.assertEqual(score1, 100)

        # Case 2: Requirement written with poor measurability
        req2 = "The system shall run the script"
        score2 = measurability_score(req2)
        self.assertLess(score2, 50)
    
    def test_complexity_score(self):
        # Case 1: Well written requirement with low complexity
        req1 = "Upon registration, the system must generate a shared encryption key."
        score1 = complexity_score(req1)
        self.assertIsInstance(score1, int)
        self.assertEqual(score1, 100)

        # Case 2: Poorly Written requirement with high complexity
        req2 = "The system shall, in accordance with dynamically inferred user interaction patterns and contingent upon contextual session states " \
        "that may or may not persist across heterogeneous device environments, provide a mechanism through which end-users are enabled to initiate, modify, " \
        "and, where applicable, retroactively reconcile task-oriented data entities in a manner that is perceived as sufficiently intuitive, except in cases where " \
        "system-imposed constraints necessitate deviation from expected interaction paradigms, at which point alternative workflows should be made available without introducing" \
        " significant cognitive overhead or degradation in overall performance characteristics."
        score2 = complexity_score(req2)
        self.assertLess(score2, 80)

    def test_readability_score(self):
        # Case 1: Well written requirement with high readability
        req1 = "The system shall output the text to the user within 4 seconds of post request"
        score1 = readability_score(req1)
        self.assertIsInstance(score1, int)
        self.assertGreaterEqual(score1,30)

        # Case 2: 
        req2 = "The system shall, in accordance with dynamically inferred user interaction patterns and contingent upon contextual session states " \
        "that may or may not persist across heterogeneous device environments, provide a mechanism through which end-users are enabled to initiate, modify, " \
        "and, where applicable, retroactively reconcile task-oriented data entities in a manner that is perceived as sufficiently intuitive, except in cases where " \
        "system-imposed constraints necessitate deviation from expected interaction paradigms, at which point alternative workflows should be made available without introducing" \
        " significant cognitive overhead or degradation in overall performance characteristics."
        score2 = readability_score(req2)
        self.assertIsInstance(score2, int)
        self.assertLess(score2, 30)

class TestOverallScore(unittest.TestCase):

    def test_overall_score(self):
        report = {
            "type": "Functional + Non-Functional",
            "functional_portion": "Valid",
            "non_functional_portion": "Valid",
            "class": "Functional",
            "ambiguity_score": 70,
            "active_voice": "Yes"
        }

        atomicity = 100
        measurability = 90
        complexity = 60
        readability = 40

        result = overall_score(
            report,
            atomicity,
            measurability,
            complexity,
            readability
        )

        # Expected breakdown:
        # type: +15
        # functional_portion: +5
        # non_functional_portion: +10
        # class: +5
        # ambiguity (70): +10
        # active_voice: +10
        # atomicity (100): +10
        # measurability (90): +10
        # complexity (>=50): +10
        # readability (>30): +10
        # TOTAL = 95

        self.assertEqual(result, 95)
if __name__ == "__main__":
    unittest.main(verbosity=2)
