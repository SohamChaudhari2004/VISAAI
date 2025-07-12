import os
import logging
from typing import Dict, List, Any, Optional
import yaml

import chromadb
from chromadb.utils import embedding_functions
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

logger = logging.getLogger(__name__)

# Load configuration
try:
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")
    if os.path.exists(config_path):
        with open(config_path) as f:
            config = yaml.safe_load(f)
    else:
        # Try looking for config in the parent directory
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.yaml")
        with open(config_path) as f:
            config = yaml.safe_load(f)
except Exception as e:
    logger.error(f"Failed to load config: {e}")
    config = {"rag": {"persist_directory": "data/chroma_db", "embedding_model": "sentence-transformers/all-MiniLM-L6-v2"}}

class RAGPipeline:
    """Retrieval-Augmented Generation pipeline for visa interview questions"""
    
    def __init__(self):
        """Initialize RAG pipeline with ChromaDB"""
        self.persist_directory = config["rag"].get("persist_directory", "data/chroma_db")
        self.embedding_model = config["rag"].get("embedding_model", "sentence-transformers/all-MiniLM-L6-v2")
        
        # Create persistence directory if it doesn't exist
        os.makedirs(self.persist_directory, exist_ok=True)
        
        # Initialize embeddings
        self.embeddings = HuggingFaceEmbeddings(model_name=self.embedding_model)
        
        # Connect to ChromaDB
        try:
            self.db = Chroma(
                persist_directory=self.persist_directory, 
                embedding_function=self.embeddings
            )
            logger.info(f"Connected to ChromaDB at {self.persist_directory}")
            
            # Check if we have documents
            collection = self.db.get()
            if not collection['documents']:
                logger.warning("ChromaDB is empty. Initializing with default questions.")
                self._initialize_with_default_questions()
        except Exception as e:
            logger.error(f"Error connecting to ChromaDB: {e}")
            # Create a new ChromaDB instance
            self._initialize_with_default_questions()

    def _initialize_with_default_questions(self):
        """Initialize ChromaDB with default visa interview questions if empty"""
        logger.info("Initializing ChromaDB with default questions")
        
        # Default tourist visa questions
        tourist_visa_questions = [
            "What is the purpose of your trip to the United States?",
            "How long are you planning to stay in the US?",
            "What places do you plan to visit during your trip?",
            "What is your occupation in your home country?",
            "How will you finance your trip to the US?",
            "Do you have any family members or friends in the United States?",
            "Have you visited the United States before?",
            "What ties do you have to your home country that ensure you will return?",
            "How much money are you bringing for your trip?",
            "Have you purchased your return ticket?",
            "Where will you be staying during your visit?",
            "Are you traveling alone or with family?",
            "Do you have travel medical insurance for your trip?",
            "What is your monthly income in your home country?",
            "Have you ever been denied a visa to any country before?"
        ]
        
        # Default student visa questions
        student_visa_questions = [
            "Which university have you been accepted to in the United States?",
            "What program or major will you be studying?",
            "Why did you choose this particular institution?",
            "How does this program align with your career goals?",
            "How will you finance your education in the US?",
            "Do you have any scholarships or financial aid?",
            "What are your plans after completing your studies?",
            "Do you intend to return to your home country after graduation?",
            "Have you ever studied in the US before?",
            "What is your academic background?",
            "How good is your English proficiency?",
            "Where will you be staying during your studies?",
            "Do you have any relatives currently in the United States?",
            "How much is your total tuition and living expenses for one year?",
            "How will this degree benefit your career in your home country?"
        ]
        
        # Add metadata to questions
        tourist_docs = [{"text": q, "metadata": {"type": "tourist"}} for q in tourist_visa_questions]
        student_docs = [{"text": q, "metadata": {"type": "student"}} for q in student_visa_questions]
        all_docs = tourist_docs + student_docs
        
        # Create a new ChromaDB instance
        try:
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
            texts = [doc["text"] for doc in all_docs]
            metadatas = [doc["metadata"] for doc in all_docs]
            
            self.db = Chroma.from_texts(
                texts=texts,
                embedding=self.embeddings,
                metadatas=metadatas,
                persist_directory=self.persist_directory
            )
            self.db.persist()
            logger.info(f"Created new ChromaDB with {len(all_docs)} default questions")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
    
    async def get_questions(
        self, 
        visa_type: str, 
        num_questions: int = 5,
        use_llm_generation: bool = False
    ) -> List[str]:
        """
        Get relevant visa interview questions based on visa type.
        
        Args:
            visa_type: Type of visa (tourist or student)
            num_questions: Number of questions to retrieve
            use_llm_generation: Whether to use LLM to generate new questions
            
        Returns:
            List of questions
        """
        logger.info(f"Retrieving {num_questions} {visa_type} visa questions")
        
        try:
            # Query ChromaDB for questions of the specified type
            filter_dict = {"type": visa_type.lower()}
            results = self.db.similarity_search_with_score(
                query=f"Common {visa_type} visa interview questions",
                k=num_questions * 2,  # Get more than needed to ensure diversity
                filter=filter_dict
            )
            
            # Extract questions and scores
            questions_with_scores = [(doc.page_content, score) for doc, score in results]
            
            # Sort by relevance and take top N unique questions
            questions_with_scores.sort(key=lambda x: x[1])
            unique_questions = []
            for q, _ in questions_with_scores:
                if q not in unique_questions:
                    unique_questions.append(q)
                    if len(unique_questions) >= num_questions:
                        break
            
            # If we don't have enough questions, use defaults
            if len(unique_questions) < num_questions:
                logger.warning(f"Not enough unique questions in DB. Using defaults.")
                defaults = {
                    "tourist": [
                        "What is the purpose of your visit to the United States?",
                        "How long do you plan to stay in the US?",
                        "What places will you visit during your trip?",
                        "Who is financing your trip?",
                        "What ties do you have to your home country?"
                    ],
                    "student": [
                        "Why did you choose this university?",
                        "How will you finance your education?",
                        "What are your plans after completing your studies?",
                        "What is your field of study and why did you choose it?",
                        "How will this degree benefit your career in your home country?"
                    ]
                }
                
                # Add default questions if needed
                while len(unique_questions) < num_questions:
                    idx = len(unique_questions) % len(defaults[visa_type])
                    if defaults[visa_type][idx] not in unique_questions:
                        unique_questions.append(defaults[visa_type][idx])
            
            logger.info(f"Retrieved {len(unique_questions)} questions for {visa_type} visa")
            return unique_questions
            
        except Exception as e:
            logger.error(f"Error retrieving questions: {e}")
            # Return default questions if RAG fails
            if visa_type == "tourist":
                return [
                    "What is the purpose of your visit to the United States?",
                    "How long do you plan to stay in the US?",
                    "What places will you visit during your trip?",
                    "Who is financing your trip?",
                    "What ties do you have to your home country?"
                ][:num_questions]
            else:  # student
                return [
                    "Why did you choose this university?",
                    "How will you finance your education?",
                    "What are your plans after completing your studies?",
                    "What is your field of study and why did you choose it?",
                    "How will this degree benefit your career in your home country?"
                ][:num_questions]
    
    async def add_questions(self, questions: List[Dict[str, Any]]) -> bool:
        """
        Add new questions to the ChromaDB.
        
        Args:
            questions: List of question dictionaries with 'text' and 'type'
            
        Returns:
            Success status
        """
        try:
            texts = [q["text"] for q in questions]
            metadatas = [{"type": q["type"]} for q in questions]
            
            self.db.add_texts(texts=texts, metadatas=metadatas)
            self.db.persist()
            
            logger.info(f"Added {len(questions)} new questions to ChromaDB")
            return True
        except Exception as e:
            logger.error(f"Error adding questions to ChromaDB: {e}")
            return False
