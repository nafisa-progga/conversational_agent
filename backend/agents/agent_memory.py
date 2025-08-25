# File: backend/agent_memory.py

from langchain.memory import ConversationBufferMemory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from typing import List

# Create a global memory object for demonstration.
# In a real application, you would manage this on a per-session/per-user basis.
memory = ConversationBufferMemory(return_messages=True)

def get_chat_history() -> List[BaseMessage]:
    """
    Retrieves the current chat history from memory.
    """
    return memory.load_memory_variables({})["history"]

def add_to_chat_history(user_input: str, ai_response: str):
    """
    Adds the latest user query and agent response to memory.
    """
    memory.save_context({"input": user_input}, {"output": ai_response})
