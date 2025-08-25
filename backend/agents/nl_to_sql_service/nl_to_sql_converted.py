# File: backend/NL_TO_SQL_Service/nl_to_sql_converter.py
from langchain_core.prompts import PromptTemplate
from langchain_community.chat_models import ChatOllama

# Initialize the local Mistral model
try:
    llm = ChatOllama(model="mistral", base_url="http://localhost:11434")
except Exception as e:
    print(f"Failed to connect to local Ollama server: {e}. Using a mock LLM.")
    class MockLLM:
        def invoke(self, prompt):
            return type('', (object,), {'content': 'SELECT * FROM users WHERE user_id = "mock_user";'})()
    llm = MockLLM()

# New prompt template for NL-to-SQL generation with a focus on user context
SQL_PROMPT_TEMPLATE = """
You are a top-tier SQL query generator. Your task is to convert a natural language question into a syntactically correct SQL query.
You have access to the following database schema:
{db_schema}

The user's ID is: {user_id}. All queries must be filtered to show only data belonging to this specific user.
This is a critical security and privacy requirement. You must ALWAYS include a WHERE clause that filters by the user_id.

User's question: {question}

SQL query:
"""

def generate_sql_query(user_input: str, db_schema: dict, user_id: str) -> str:
    """
    Generates a SQL query from natural language.
    
    Args:
        user_input (str): The natural language query from the user.
        db_schema (dict): A dictionary representing the database schema.
        user_id (str): The authenticated ID of the current user.
        
    Returns:
        str: A generated SQL query.
    """
    # Create the prompt and chain for SQL generation
    prompt = PromptTemplate(
        input_variables=["question", "db_schema", "user_id"],
        template=SQL_PROMPT_TEMPLATE
    )
    
    sql_chain = prompt | llm
    
    # Generate and return the SQL query
    generated_sql = sql_chain.invoke(
        {"question": user_input, "db_schema": db_schema, "user_id": user_id}
    ).content
    
    return generated_sql

