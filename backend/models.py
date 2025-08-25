# File: backend/models.py

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database_connector import Base

# A simple user model. This table will store basic user information.
class User(Base):
    """
    Represents the 'users' table in the database.
    """
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    
    # Relationship to the Query table. The backref creates a `.user`
    # attribute on the Query object, linking it back to the User.
    queries = relationship("Query", back_populates="user")
    
    # Relationships for fine-tuning data
    # fine_tuning_data = relationship("FineTuningData", back_populates="user") # Removed
    sql_feedback = relationship("SQLFeedback", back_populates="user")

# The query model. This table will store a history of user interactions.
class Query(Base):
    """
    Represents the 'queries' table, storing a history of user interactions.
    """
    __tablename__ = "queries"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"))
    query_text = Column(Text, nullable=False)
    response_text = Column(Text)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship to the User table.
    user = relationship("User", back_populates="queries")

# New model for fine-tuning data on intent and general response.
class FineTuningData(Base):
    """
    Represents the 'fine_tuning_data' table for LLM fine-tuning.
    Stores user queries, their intent, the language, and the agent's final response.
    """
    __tablename__ = "fine_tuning_data"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    # user_id = Column(String, ForeignKey("users.id")) # Removed
    user_query = Column(Text, nullable=False)
    llm_intent = Column(String)
    identified_language = Column(String)
    generated_response = Column(Text)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # user = relationship("User", back_populates="fine_tuning_data") # Removed

# New model for storing feedback on generated SQL queries.
class SQLFeedback(Base):
    """
    Represents the 'sql_feedback' table for fine-tuning NL-to-SQL models.
    Stores the user query, the generated SQL, and correctness feedback.
    """
    __tablename__ = "sql_feedback"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    #user_id = Column(String, ForeignKey("users.id"))
    user_query = Column(Text, nullable=False)
    generated_sql = Column(Text)
    is_correct = Column(Boolean, default=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="sql_feedback")
