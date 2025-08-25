# File: backend/NL_TO_SQL_Service/nl_to_sql_agent.py

from typing import TypedDict, List
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, END
from langchain_core.prompts import PromptTemplate
from langchain_community.chat_models import ChatOllama
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from .nl_to_sql_converter import generate_sql_query
import re

# Initialize the local Mistral model via the Ollama API.
try:
    llm = ChatOllama(model="mistral", base_url="http://localhost:11434")
except Exception as e:
    print(f"Failed to connect to local Ollama server: {e}. Using a mock LLM.")
    class MockLLM:
        def invoke(self, prompt):
            return type('', (object,), {'content': 'Hello from mock LLM!'})()
    llm = MockLLM()

# Define the Agent State for the sub-agent
class AgentState(TypedDict):
    """
    State for the NL-to-SQL agent.
    
    Attributes:
        user_id (str): The authenticated user's ID.
        input (str): The user's natural language query.
        response (str): The final, conversational response to the user.
        sql_query (str): The generated SQL query.
        validation_status (str): The status of the query validation ('valid', 'invalid', 'execution_failed').
        db (Session): The database session object.
        attempts (int): A counter for the number of self-correction attempts.
        language (str): The language of the user's query.
        raw_result: The raw, unformatted output of the query.
    """
    user_id: str
    input: str
    response: str
    sql_query: str
    validation_status: str
    db: Session
    attempts: int
    language: str
    raw_result: any # New field

# This prompt is no longer needed here as formatting is centralized in the core agent.
# RESPONSE_PROMPT_TEMPLATE = """..."""

# --- Tools (Nodes) ---
def nl_to_sql_tool(state: AgentState) -> dict:
    """
    Generates a SQL query by calling the dedicated service (`nl_to_sql_converter.py`).
    """
    print("--- NL-to-SQL Tool: Generating query ---")
    query = state.get("input")
    user_id = state.get("user_id")
    
    # Dummy schema for demonstration
    dummy_schema = {
        "tables": ["users", "products", "sales"],
        "columns": {
            "users": ["id", "username", "email", "user_id"],
            "products": ["id", "name", "price", "user_id"],
            "sales": ["id", "product_id", "user_id", "sale_date", "revenue"]
        }
    }
    
    # Call the converter to generate the query
    generated_sql = generate_sql_query(user_input=query, db_schema=dummy_schema, user_id=user_id)
    
    print(f"Generated SQL: {generated_sql}")
    return {"sql_query": generated_sql}

def sql_validator(state: AgentState) -> dict:
    """
    Validates the generated SQL query for security risks AND user ID filtering.
    """
    print("--- SQL Validator: Validating query ---")
    sql_query = state.get("sql_query")
    user_id = state.get("user_id")
    
    # 1. Check for malicious keywords
    malicious_keywords = ["DROP", "DELETE", "UPDATE", ";"]
    if any(keyword in sql_query.upper() for keyword in malicious_keywords):
        print("SQL query is invalid due to security concerns.")
        # Now, we return an error message directly to the core agent.
        return {"validation_status": "invalid", "raw_result": "The query contains potentially harmful commands and cannot be executed."}

    # 2. Check for user_id filtering in the WHERE clause
    user_id_check = re.search(r"WHERE.*user_id\s*=\s*['\"]?" + re.escape(user_id) + r"['\"]?", sql_query, re.IGNORECASE)
    
    if user_id_check:
        print("SQL query is valid and includes user_id filter.")
        return {"validation_status": "valid"}
    else:
        print("SQL query is invalid: Missing or incorrect user_id filter.")
        # Return a specific error message.
        return {"validation_status": "invalid", "raw_result": "The generated query is missing the required user-specific filter. It has been blocked for security reasons."}

def sql_executor(state: AgentState) -> dict:
    """
    Executes the validated SQL query and returns the raw results.
    """
    print("--- SQL Executor: Executing query and returning raw results ---")
    
    sql_query = state.get("sql_query")
    db = state.get("db")
    
    try:
        # Dummy database interaction. In a real application, this would execute against a live DB.
        with db.get_bind().connect() as connection:
            if "sales" in sql_query:
                # Mocking a successful query result for this example
                results = [
                    {"product_id": "P1", "revenue": 1500, "user_id": state['user_id']},
                    {"product_id": "P2", "revenue": 2000, "user_id": state['user_id']}
                ]
            else:
                results = [{"username": "John Doe", "email": "john.doe@example.com", "user_id": state['user_id']}]
            
            # The executor now returns the raw results directly to the core agent for formatting.
            return {"raw_result": results, "validation_status": "success"}
            
    except SQLAlchemyError as e:
        print(f"Database execution error: {e}")
        # If execution fails, return a specific error message to be handled by the core agent.
        return {"response": None, "validation_status": "execution_failed"}

def self_correction_loop(state: AgentState) -> dict:
    """
    Handles self-correction for failed SQL execution. It retries up to 3 times.
    """
    print("--- Self-Correction Loop: Attempting to fix query ---")
    
    attempts = state.get("attempts", 0) + 1
    
    if attempts <= 3:
        print(f"Attempt {attempts}/3: Modifying prompt and retrying.")
        # Modify the prompt to encourage a different query
        new_input = f"{state.get('input')}\n\nNote: The previous SQL query failed to execute. Please try a different approach."
        return {"input": new_input, "attempts": attempts, "response": None, "sql_query": None}
    else:
        print("Max attempts reached. Moving to failure node.")
        # If max attempts are reached, return an error message to the core agent.
        return {"validation_status": "failed", "raw_result": "I'm sorry, I was unable to generate a valid database query after multiple attempts. Please try rephrasing your question."}
        
# --- Build the LangGraph Workflow (Graph) ---
def create_nl_to_sql_agent_executor():
    """
    Creates and compiles the NL-to-SQL agent workflow.
    """
    workflow = StateGraph(AgentState)
    
    workflow.add_node("nl_to_sql", nl_to_sql_tool)
    workflow.add_node("validator", sql_validator)
    workflow.add_node("executor", sql_executor)
    workflow.add_node("corrector", self_correction_loop)

    workflow.set_entry_point("nl_to_sql")
    
    workflow.add_edge("nl_to_sql", "validator")
    
    # Conditional routing based on validation status
    # Note: `invalid` now returns a raw result/error message.
    workflow.add_conditional_edges(
        "validator",
        lambda state: state["validation_status"],
        {
            "valid": "executor",
            "invalid": END # If invalid, the process stops here and main agent handles the response
        }
    )

    # Conditional routing based on execution status
    # Note: `success` now returns a raw result.
    workflow.add_conditional_edges(
        "executor",
        lambda state: state["validation_status"],
        {
            "success": END, # If successful, the process stops
            "execution_failed": "corrector" # If failed, go to the correction loop
        }
    )
    
    # Conditional routing from the correction loop
    # Note: `fail` now returns a raw result/error message.
    workflow.add_conditional_edges(
        "corrector",
        lambda state: "continue" if state["attempts"] < 3 else "fail",
        {
            "continue": "nl_to_sql", # Try again with a modified prompt
            "fail": END # Stop and signal failure to the main agent
        }
    )
    
    return workflow.compile()

nl_to_sql_agent_executor = create_nl_to_sql_agent_executor()
