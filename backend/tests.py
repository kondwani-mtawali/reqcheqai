# tests.py
from fastapi.testclient import TestClient
from .main import app
import unittest
import json
from sqlmodel import SQLModel
from models import RequirementAnalysis
from database import create_db_and_tables, get_session, create_report, read_report, read_reports, delete_report

# Import App as a Test Client
client = TestClient(app)

create_db_and_tables() # Calls the function to create/initialize datbase

class TestDatabaseFunctions(unittest.TestCase):
    def test_analyze_db_save(self):
        """Tests that the /analyze endpoint saves the requirement and report to DB"""
        requirement = "The system shall analyze the detected vulnerability. The system shall inspect SSL certificate.The system shall identify acceptable low false positive rates. The system shall allow multiple clients to login and save their files to the remote server!"

        output = client.post("/analyze", requirement)