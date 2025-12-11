import os
import httpx
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from pgvector.sqlalchemy import Vector
import json
from dotenv import load_dotenv
import logging
from datetime import datetime

from . import models, schemas

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables for Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_EMBED_URL = os.getenv("GEMINI_EMBED_URL")
GEMINI_GEN_URL = os.getenv("GEMINI_GEN_URL")

from asyncio import sleep # Added for retry mechanism

async def embed_text_with_gemini(text: str) -> List[float]:
    """Calls the Gemini embeddings model to get the embedding for a given text with retries."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY must be set in environment variables.")

    if not GEMINI_EMBED_URL:
        raise ValueError("GEMINI_EMBED_URL must be set in environment variables.")

    headers = {
        "x-goog-api-key": GEMINI_API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "models/gemini-embedding-001",
        "content": {
            "parts": [{
                "text": text
            }]
        },
        "output_dimensionality": 768
    }

    logger.info(f"Sending payload to Gemini API to URL: {GEMINI_EMBED_URL}")
    logger.info(f"Payload: {json.dumps(payload, indent=2)}")

    retries = 3
    delay = 2
    for i in range(retries):
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(GEMINI_EMBED_URL, headers=headers, json=payload)
                response.raise_for_status()
                embedding_data = response.json()
                
                if "embedding" in embedding_data and "values" in embedding_data["embedding"]:
                    embedding_values = embedding_data["embedding"]["values"]
                    logger.info(f"Generated embedding with {len(embedding_values)} dimensions.")
                    return embedding_values
                else:
                    raise ValueError(f"Unexpected embedding response format from Gemini API: {embedding_data}")
            except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.RemoteProtocolError) as e:
                logger.error(f"Attempt {i+1}/{retries}: Timeout or connection error occurred while calling Gemini Embedding API: {e}")
                if i < retries - 1:
                    await sleep(delay)
                    delay *= 2
                    continue
                raise # Re-raise if all retries fail
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error occurred while calling Gemini Embedding API: {e.response.text}")
                raise
            except Exception as e:
                logger.error(f"An unexpected error occurred while calling Gemini Embedding API: {e}")
                raise
    raise Exception("Failed to get embedding after multiple retries.") # Should not be reached

def retrieve_similar_rags(db: Session, query_vector: List[float], top_k: int, id_user: Optional[int] = None) -> List[models.RAGSEmbedding]:
    """Performs similarity search in the database using pgvector, optionally filtered by user ID."""
    query = db.query(models.RAGSEmbedding)
    
    if id_user is not None:
        query = query.filter(models.RAGSEmbedding.id_user == id_user)

    result = query.order_by(
        models.RAGSEmbedding.embedding.l2_distance(query_vector)
    ).limit(top_k).all()
    
    return result

def augment_prompt(question: str, context_docs: List[models.RAGSEmbedding], client_local_time: Optional[datetime] = None) -> str:
    """Constructs an augmented prompt with retrieved context and optional client local time."""
    context_str = "\n\n".join([
        f"Source: {doc.source_type} (ID: {doc.source_id or doc.id_embedding})\nContent: {doc.text_original}"
        for doc in context_docs
    ])

    time_context = ""
    if client_local_time:
        formatted_time = client_local_time.strftime("%A, %d %B %Y, %H:%M:%S")
        time_context = f"For your information, the user's current local date and time is {formatted_time}. Please use this for any time-sensitive queries about schedules or deadlines."

    system_instruction = (
        "You are a smart, helpful personal assistant. "
        "You have DIRECT ACCESS to the user's personal database, which includes:\n"
        "1. Complete Profile (Name, Email, Bio)\n"
        "2. To-Do List (Tasks, Deadlines)\n"
        "3. Class Schedule/Jadwal Matkul (Day, Time, SKS)\n"
        "4. UKM Activities (Organization Name, Role)\n\n"
        "IMPORTANT: You MUST answer based on the provided context below. "
        "Do NOT say 'I cannot access your calendar' or 'I don't have access to your data'. "
        "You HAVE the data in the context. "
        "If the specific answer is not in the context, state 'Based on your saved data, I couldn't find that specific information.' "
        "Always be concise and actionable."
    )

    if not context_docs:
        context_str = "No relevant information found in the user's database to answer this question."

    return (
        f"{system_instruction}\n\n"
        "------------------\n\n"
        f"{time_context}\n\n"
        "CONTEXT FROM DATABASE:\n"
        "------------------\n"
        f"{context_str}\n\n"
        "------------------\n\n"
        f"QUESTION: {question}\n\n"
        "------------------\n\n"
        "Based on the context, provide a concise and actionable answer in Bahasa Indonesia."
    )

async def generate_answer_with_gemini(augmented_prompt: str) -> str:
    """Calls the Gemini generation model to get an answer based on the prompt."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY must be set in environment variables.")

    if not GEMINI_GEN_URL:
        raise ValueError("GEMINI_GEN_URL must be set in environment variables.")

    headers = {
        "x-goog-api-key": GEMINI_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": augmented_prompt}
                ]
            }
        ]
    }

    async with httpx.AsyncClient(timeout=30.0) as client: # Increased timeout to 30 seconds
        try:
            response = await client.post(GEMINI_GEN_URL, headers=headers, json=payload)
            response.raise_for_status()
            generation_data = response.json()
            # Assume response structure like: {"candidates": [{"content": {"parts": [{"text": "..."}]}}]}}
            if "candidates" in generation_data and len(generation_data["candidates"]) > 0:
                candidate = generation_data["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"] and len(candidate["content"]["parts"]) > 0:
                    return candidate["content"]["parts"][0]["text"]
            
            raise ValueError(f"Unexpected generation response format from Gemini API: {generation_data}")
        except (httpx.ConnectTimeout, httpx.ReadTimeout) as e:
            logger.error(f"Timeout error occurred while calling Gemini Generation API: {e}")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred while calling Gemini Generation API: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred while calling Gemini Generation API: {e}")
            raise