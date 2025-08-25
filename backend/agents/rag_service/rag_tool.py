# File: backend/Rag_Service/rag_tool.py
from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Initialize the local Mistral model
try:
    llm = ChatOllama(model="mistral", base_url="http://localhost:11434")
except Exception as e:
    print(f"Failed to connect to local Ollama server: {e}. Using a mock LLM.")
    class MockLLM:
        def invoke(self, prompt):
            return type('', (object,), {'content': 'This is a mock RAG response.'})()
    llm = MockLLM()

# Define the RAG prompt template
RAG_PROMPT_TEMPLATE = """
You are a helpful assistant. Use the following context to answer the user's question.
If you don't know the answer, just say that you don't know. Do not make up an answer.
Respond in the {language} language.
Context:
{context}

Question: {question}
"""

def generate_rag_response(user_input: str, language: str) -> str:
    """
    Generates a response using the RAG approach.
    
    Args:
        user_input (str): The user's query.
        language (str): The language of the response.
        
    Returns:
        str: The generated response.
    """
    # In a real-world scenario, this would retrieve context from a vector store
    # For this example, we'll use a simple, static context.
    dummy_context = "Business analysis is a professional discipline focused on identifying business needs and determining solutions to business problems. A stakeholder is anyone with an interest in a project or business."
    
    # Create the prompt and chain for the RAG response
    prompt = PromptTemplate(
        template=RAG_PROMPT_TEMPLATE,
        input_variables=["context", "question", "language"]
    )
    
    rag_chain = prompt | llm | StrOutputParser()
    
    # Generate and return the RAG response
    response = rag_chain.invoke({"context": dummy_context, "question": user_input, "language": language})
    
    return response
