import os
from langsmith import Client

from dotenv import load_dotenv

load_dotenv()

client = Client()
projects = client.list_projects()
print(f"Connected to LangSmith! Found {len(list(projects))} projects.")
