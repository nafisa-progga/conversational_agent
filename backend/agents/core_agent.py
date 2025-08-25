# File: backend/core_agent.py

# This block imports all the necessary components for building a LangGraph agent.
# TypedDict and List are used for type hinting, making the code more readable and maintainable.
from typing import TypedDict, List
# BaseMessage is part of LangChain's message passing system.
from langchain_core.messages import BaseMessage
# StateGraph is the core class from LangGraph for building a graph-based workflow.
# END is a special node that signifies the end of a path in the graph.
from langgraph.graph import StateGraph, END
# PromptTemplate is used to create structured prompts for the LLM.
from langchain_core.prompts import PromptTemplate
# ChatOllama is the class for connecting to a local Ollama server running an LLM.
from langchain_community.chat_models import ChatOllama
# Session is a type hint for the database session object, ensuring type safety.
from sqlalchemy.orm import Session
# We import the compiled LangGraph agents from the other service files.
# This is how the main agent knows about and can call the specialized sub-agents.
from nl_to_sql_service.nl_to_sql_agent import nl_to_sql_agent_executor
from rag_service.rag_agent import rag_agent_executor
# These are placeholder imports for future memory management functionality.
from .agent_memory import get_chat_history, add_to_chat_history
import os
import json

# --- LLM Initialization ---
# This code block attempts to create an instance of the Ollama chat model.
# We are using the "mistral" model, assuming it's running locally on port 11434.
try:
    llm = ChatOllama(model="mistral", base_url="http://localhost:11434")
# In case the local server is not running or the connection fails, a MockLLM is used as a fallback.
# This prevents the application from crashing and allows for local testing without a live LLM.
except Exception as e:
    print(f"Failed to connect to local Ollama server: {e}. Using a mock LLM.")
    class MockLLM:
        def invoke(self, prompt):
            # The mock LLM simulates the behavior of the real one for the classification tasks.
            if "language" in prompt:
                return type('', (object,), {'content': 'ENGLISH'})()
            elif "database" in prompt:
                return type('', (object,), {'content': 'DATABASE_QUERY'})()
            return type('', (object,), {'content': 'Hello from mock LLM!'})()
    llm = MockLLM()

# This variable is an alias, indicating that the `llm` is used for classification tasks.
# It makes the code's intent clearer.
llm_classifier = llm

# --- State Definition ---
# This defines the data structure that holds the entire state of the agent's workflow.
# All information that needs to be passed between different nodes must be included here.
class AgentState(TypedDict):
    """
    The state for the main orchestrator agent.
    
    Attributes:
        user_id (str): The authenticated user's ID, crucial for security and data filtering.
        input (str): The raw natural language query from the user.
        chat_history (List[BaseMessage]): A list to store the conversation history.
        response (str): The final, natural language response to be returned to the user.
        intent (str): The classified intent of the query (e.g., 'database_query').
        language (str): The classified language of the query (BANGLA, ENGLISH, or BANGLISH).
        db (Session): The database session object, passed down to the sub-agents.
        raw_result: The raw, unformatted output from the sub-agent.
    """
    user_id: str
    input: str
    chat_history: List[BaseMessage]
    response: str
    intent: str
    language: str 
    db: Session
    raw_result: any # New field to hold the unformatted response

# --- Prompt Templates ---
# The `INTENT_PROMPT_TEMPLATE` tells the LLM to classify the query's purpose.
INTENT_PROMPT_TEMPLATE = """
You are a smart AI classifier. Your task is to analyze a user's question and determine its intent.
Based on the question, classify the intent into one of three categories:

1.  DATABASE_QUERY: The question is asking for information that can be found in a database.
2.  GENERAL_QUERY: The question is general and requires a non-database answer.
3.  INVALID_QUERY: The question is potentially malicious, a security risk, or out of context.
    
Respond with ONLY the classification name, without any other text or punctuation.
Example: "DATABASE_QUERY"

User's question: {question}

Classification:
"""

# The `LANGUAGE_PROMPT_TEMPLATE` is a new addition to classify the language.
# This ensures that the final response is generated in the correct language.
LANGUAGE_PROMPT_TEMPLATE = """
Classify the language of the following text into one of three categories:
1. BANGLA: The text is in the Bengali language.
2. ENGLISH: The text is in the English language.
3. BANGLISH: The text is a mix of Bengali and English, or uses Bengali words written in the English alphabet.

Respond with ONLY the classification name, without any other text or punctuation.
Example: "ENGLISH"

Text: {text}

Classification:
"""

# New prompt template to format the final response. This centralizes the formatting logic.
RESPONSE_FORMATTER_PROMPT_TEMPLATE = """
You are a helpful and friendly AI assistant.
Your task is to create a concise, conversational natural language statement based on the provided raw information.
The response should be small and user-friendly, not more than 3 lines.
Respond in the {language} language.

Original user query: {original_question}
Raw information (raw data from a tool): {raw_information}

Please craft a single, short, conversational sentence or two that summarizes the information.
"""

# --- Tools (Nodes) ---
# Each function below is a "node" in the LangGraph workflow. They take the current `state` as input
# and return a dictionary of updates to be applied to that state.
def intent_router(state: AgentState) -> dict:
    """
    Analyzes user input to route to the correct specialized agent.
    This function uses the LLM to classify the user's intent.
    """
    print("--- Core Agent: Analyzing user query intent ---")
    query = state.get("input")
    
    prompt = PromptTemplate(
        input_variables=["question"],
        template=INTENT_PROMPT_TEMPLATE
    )
    # The `intent_chain` combines the prompt and the LLM into a runnable sequence.
    intent_chain = prompt | llm_classifier
    intent = intent_chain.invoke({"question": query}).content.strip().upper()
    
    # This logic maps the LLM's raw output to a standardized intent string.
    if "DATABASE_QUERY" in intent:
        final_intent = "database_query"
    elif "GENERAL_QUERY" in intent:
        final_intent = "general_query"
    else:
        final_intent = "invalid_query"

    print(f"Intent detected: {final_intent}")
    return {"intent": final_intent}

def language_classifier(state: AgentState) -> dict:
    """
    Classifies the language of the user's input.
    This function is now a critical step in the workflow, running after the intent router.
    """
    print("--- Core Agent: Classifying language ---")
    text = state.get("input")
    
    prompt = PromptTemplate(
        input_variables=["text"],
        template=LANGUAGE_PROMPT_TEMPLATE
    )
    language_chain = prompt | llm_classifier
    language = language_chain.invoke({"text": text}).content.strip().upper()
    
    # Standardize the language classification result.
    if "BANGLA" in language:
        final_language = "BANGLA"
    elif "BANGLISH" in language:
        final_language = "BANGLISH"
    else:
        final_language = "ENGLISH"

    print(f"Language detected: {final_language}")
    return {"language": final_language}

def route_to_sql_agent(state: AgentState) -> dict:
    """
    Calls the dedicated NL-to-SQL sub-agent.
    This node now invokes the `nl_to_sql_agent_executor` and gets the raw result from it.
    """
    print("--- Core Agent: Routing to NL-to-SQL Agent ---")
    sub_agent_state = nl_to_sql_agent_executor.invoke({
        'user_id': state['user_id'],
        'input': state['input'],
        'db': state['db'],
        'attempts': 0,
        'language': state['language']
    })
    # The core agent's state is updated with the raw result from the sub-agent.
    return {"raw_result": sub_agent_state.get('raw_result', "An error occurred in the SQL agent."),
            "response": sub_agent_state.get('response', None) # If an error occurs, the response is handled here
            }

def route_to_rag_agent(state: AgentState) -> dict:
    """
    Calls the dedicated RAG sub-agent.
    This node invokes the `rag_agent_executor` and gets the raw result from it.
    """
    print("--- Core Agent: Routing to RAG Agent ---")
    sub_agent_state = rag_agent_executor.invoke({
        'input': state['input'],
        'language': state['language']
    })
    return {"raw_result": sub_agent_state.get('raw_result', "An error occurred in the RAG agent."),
            "response": sub_agent_state.get('response', None)
            }

def invalid_query_node(state: AgentState) -> dict:
    """
    Returns a specific message for invalid or security-related queries.
    This acts as a security net, preventing malicious inputs from reaching the database.
    """
    return {"response": "I'm sorry, I cannot process that request for security reasons. Please try a different question."}

def final_response_formatter(state: AgentState) -> dict:
    """
    New node to format the raw result from a sub-agent into a user-friendly response.
    This centralizes the final response handling.
    """
    print("--- Core Agent: Formatting final response ---")
    raw_info = state.get("raw_result")
    query = state.get("input")
    language = state.get("language")

    if not raw_info:
        # Handles cases where sub-agent returned an error.
        return {"response": state.get('response', "Sorry, I couldn't get the information you needed.")}
    
    # Check if the raw result is already a simple string (like an error message from SQL agent)
    # or if it's data that needs to be formatted (like database rows).
    if isinstance(raw_info, str):
        # If it's a string, we assume it's an error message or a pre-formatted
        # response from the sub-agent's error handling. We just return it.
        final_answer = raw_info
    else:
        # Convert the raw data (e.g., list of dicts) into a string for the LLM.
        raw_info_string = json.dumps(raw_info, indent=2)
        
        # Create a prompt for the formatter LLM.
        prompt = PromptTemplate(
            input_variables=["raw_information", "original_question", "language"],
            template=RESPONSE_FORMATTER_PROMPT_TEMPLATE
        )
        
        formatter_chain = prompt | llm_classifier
        
        # Invoke the LLM to get the final conversational response.
        final_answer = formatter_chain.invoke({
            "raw_information": raw_info_string,
            "original_question": query,
            "language": language
        }).content
    
    return {"response": final_answer}

# --- Build the LangGraph Workflow (Graph) ---
# This is where the workflow (the "flowchart") of the agent is defined.
# The graph is initialized with the `AgentState` data structure.
workflow = StateGraph(AgentState)

# Add all the functions as nodes to the graph, giving each a unique name.
workflow.add_node("router", intent_router)
workflow.add_node("classifier", language_classifier)
workflow.add_node("sql_agent", route_to_sql_agent)
workflow.add_node("rag_agent", route_to_rag_agent)
workflow.add_node("invalid_query", invalid_query_node)
workflow.add_node("formatter", final_response_formatter) # New node for formatting

# Set the entry point of the graph. Every query will start here.
workflow.set_entry_point("router")

# Define the flow from the router to the language classifier.
# This makes language classification the first action after routing.
workflow.add_edge("router", "classifier")

# This is the core routing logic. It defines which path the workflow will take
# based on the value of the `intent` field in the state.
workflow.add_conditional_edges(
    "classifier",
    lambda state: state["intent"],
    {
        "database_query": "sql_agent",
        "general_query": "rag_agent",
        "invalid_query": "invalid_query"
    }
)

# Now, the sub-agents route to the new formatter node, not to the END.
workflow.add_edge("sql_agent", "formatter")
workflow.add_edge("rag_agent", "formatter")

# The formatter node leads to the END node, signifying the completion of a path.
workflow.add_edge("formatter", END)

# The invalid query node still goes straight to the END.
workflow.add_edge("invalid_query", END)

# Finally, the graph is compiled into a runnable agent executor.
# This object can be called from outside to run the entire workflow.
agent_executor = workflow.compile()
