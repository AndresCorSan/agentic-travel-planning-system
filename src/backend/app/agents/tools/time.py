from datetime import datetime
from langchain.tools import tool

@tool
def get_current_date() -> str:
    """Return the current date in YYYY-MM-DD format."""
    return datetime.now().strftime("%Y-%m-%d")