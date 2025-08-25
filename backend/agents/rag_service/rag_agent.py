# File: backend/Rag_Service/rag_agent.py

from typing import TypedDict
from langgraph.graph import StateGraph, END
from .rag_tool import generate_rag_response

# Define the Agent State for the sub-agent
class AgentState(TypedDict):
    """
    State for the RAG agent.
    """
    input: str
    response: str
    validation_status: str
    language: str
    raw_result: any # New field

# --- Tools (Nodes) ---
def rag_tool(state: AgentState) -> dict:
    """
    Generates a response using the RAG service.
    This node now returns the raw, unformatted text to the core agent.
    """
    print("--- RAG Agent: Retrieving knowledge ---")
    query = state.get("input")
    language = state.get("language") # Get the language from the state
    
    # Call the core RAG function, passing the language to guide the response
    raw_response_from_rag = generate_rag_response(user_input=query, language=language)
    
    print("RAG process completed.")
    # Return the raw response so the core agent can format it.
    return {"raw_result": raw_response_from_rag, "validation_status": "success"}

# --- Build the LangGraph Workflow (Graph) ---
def create_rag_agent_executor():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("rag_system", rag_tool)
    workflow.set_entry_point("rag_system")
    workflow.add_edge("rag_system", END)
    
    return workflow.compile()

rag_agent_executor = create_rag_agent_executor()
