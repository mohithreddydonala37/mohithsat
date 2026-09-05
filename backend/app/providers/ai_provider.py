from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class AIProvider(ABC):
    """
    Abstract interface for AI providers.
    
    This interface defines provider-neutral contracts for AI operations.
    Implementations (e.g., GroqProvider) must adapt to this interface.
    The frontend and domain services depend only on this interface.
    """
    
    @abstractmethod
    async def extract(
        self,
        document_text: str,
        schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract structured information from document text.
        
        Args:
            document_text: Text content from medical document
            schema: JSON schema for structured output
            
        Returns:
            Extracted data matching the schema
        """
        pass
    
    @abstractmethod
    async def summarize(
        self,
        verified_data: Dict[str, Any]
    ) -> str:
        """
        Generate a summary from verified structured data.
        
        Args:
            verified_data: Verified structured medical information
            
        Returns:
            Factual, source-grounded summary
        """
        pass
    
    @abstractmethod
    async def classify_safety(
        self,
        query: str
    ) -> str:
        """
        Classify a user query for safety.
        
        Args:
            query: User question or request
            
        Returns:
            "ALLOWED" or "RESTRICTED"
        """
        pass
    
    @abstractmethod
    async def answer(
        self,
        question: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Answer a question about documented records.
        
        Args:
            question: User question
            context: Relevant medical record context
            
        Returns:
            Factual answer based on documented information
        """
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """
        Get the name of the AI provider.
        
        Returns:
            Provider name (e.g., "groq", "openai", "anthropic")
        """
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """
        Get the name of the AI model.
        
        Returns:
            Model name (e.g., "llama3-70b-8192")
        """
        pass
