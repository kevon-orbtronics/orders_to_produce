"""Shared connection helper for the Klaes SQL Server database.

Connection settings are read from `api/.env`:
DATABASE_SERVER, DATABASE_NAME, DATABASE_USERNAME, DATABASE_PASSWORD.
"""

import os

import pypyodbc as pyodbc
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

REQUIRED_SETTINGS = ("DATABASE_SERVER", "DATABASE_NAME", "DATABASE_USERNAME", "DATABASE_PASSWORD")


def get_connection():
	"""Open a new connection to the Klaes database.

	Queries can reference tables as [dbo].[TABLE] because the database is
	selected in the connection string.
	"""
	missing = [key for key in REQUIRED_SETTINGS if not os.getenv(key)]
	if missing:
		raise RuntimeError(f"Missing Klaes database settings in api/.env: {', '.join(missing)}")

	return pyodbc.connect(
		"TrustServerCertificate=yes;"
		"DRIVER={ODBC Driver 18 for SQL Server};"
		f"SERVER={os.getenv('DATABASE_SERVER')};"
		f"DATABASE={os.getenv('DATABASE_NAME')};"
		"ENCRYPT=yes;"
		f"UID={os.getenv('DATABASE_USERNAME')};"
		f"PWD={os.getenv('DATABASE_PASSWORD')}"
	)
