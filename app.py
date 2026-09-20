"""
Enterprise Infrastructure Copilot
---------------------------------
An automated root-cause analysis and incident resolution system powered by
Retrieval-Augmented Generation (RAG) with conversational multi-turn memory.
"""

import os
import glob
from typing import Tuple, List, Dict
import chromadb
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from groq import Groq


def initialize_vector_store() -> Tuple[SentenceTransformer, chromadb.Collection]:
    """
    Initializes the local embedding model and sets up an in-memory ChromaDB collection.
    """
    print("[INFO] Initializing embedding model (all-MiniLM-L6-v2)...")
    embedder = SentenceTransformer("all-MiniLM-L6-v2")
    
    chroma_client = chromadb.Client()
    collection = chroma_client.create_collection(name="infra_troubleshooting_kb")
    return embedder, collection


def ingest_runbooks(
    embedder: SentenceTransformer, 
    collection: chromadb.Collection, 
    docs_path: str = "docs/*.md"
) -> bool:
    """
    Parses markdown runbooks, splits them into semantic chunks, and persists them into ChromaDB.
    """
    print(f"[INFO] Scanning and indexing runbooks from: '{docs_path}'...")
    doc_chunks: List[str] = []
    doc_ids: List[str] = []

    for filepath in glob.glob(docs_path):
        with open(filepath, "r", encoding="utf-8") as file:
            content = file.read()
            sections = content.split("## ")
            for idx, section in enumerate(sections):
                cleaned_text = section.strip()
                if cleaned_text and not cleaned_text.startswith("# Enterprise"):
                    doc_chunks.append("## " + cleaned_text)
                    doc_ids.append(f"{os.path.basename(filepath)}_section_{idx}")

    if not doc_chunks:
        print("[ERROR] No operational runbooks discovered in target directory.")
        return False

    print(f"[INFO] Extracted {len(doc_chunks)} distinct operational chunks.")
    
    chunk_embeddings = embedder.encode(doc_chunks).tolist()
    collection.add(ids=doc_ids, documents=doc_chunks, embeddings=chunk_embeddings)
    print("[INFO] Knowledge base successfully vectorized and indexed.\n")
    return True


def execute_incident_query(
    groq_client: Groq,
    embedder: SentenceTransformer,
    collection: chromadb.Collection,
    user_query: str,
    chat_history: List[Dict[str, str]]
) -> Tuple[str, str]:
    """
    Executes dense retrieval and leverages multi-turn conversation history
    to generate grounded diagnostic steps.
    """
    system_instruction = (
        "You are an Enterprise Infrastructure Site Reliability Engineer (SRE) Copilot.\n"
        "Your objective is to diagnose server, storage, and container incidents based on the provided runbook context "
        "and active conversation history.\n\n"
        "Rules:\n"
        "1. For questions about prior conversation turns or session context, answer directly using the chat history.\n"
        "2. For operational issues, prioritize the runbook context. If an incident resolution is completely absent from both "
        "the context and history, state: 'Resolution context is not available in the ingested knowledge base.'\n"
        "3. Provide structured, actionable CLI steps where applicable."
    )

    # Perform dense retrieval
    query_vector = embedder.encode([user_query]).tolist()
    search_results = collection.query(query_embeddings=query_vector, n_results=1)

    retrieved_context = search_results["documents"][0][0]
    matched_chunk_id = search_results["ids"][0][0]

    # Current prompt combining retrieved context with the active incident
    current_turn_prompt = (
        f"Retrieved Runbook Context:\n{retrieved_context}\n\n"
        f"Current Engineer Input:\n{user_query}"
    )

    # Build multi-turn payload: System prompt + Previous conversation turns + Current turn
    messages_payload = [{"role": "system", "content": system_instruction}]
    messages_payload.extend(chat_history)
    messages_payload.append({"role": "user", "content": current_turn_prompt})

    response = groq_client.chat.completions.create(
        messages=messages_payload,
        model="openai/gpt-oss-120b",
        temperature=0.1
    )

    answer = response.choices[0].message.content
    return matched_chunk_id, answer


def main() -> None:
    """Application entry point with stateful conversational loop."""
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError("GROQ_API_KEY environment variable is missing. Check your .env file.")

    client = Groq(api_key=api_key)
    embedder, collection = initialize_vector_store()

    if not ingest_runbooks(embedder, collection):
        return

    # In-memory conversational state buffer
    conversation_history: List[Dict[str, str]] = []

    print("=" * 65)
    print("  ENTERPRISE INFRASTRUCTURE COPILOT (MULTI-TURN CLI)")
    print("  Type 'exit' or 'q' to terminate the session.")
    print("=" * 65)

    while True:
        try:
            incident_query = input("\n[Incident Input] > ").strip()
            if incident_query.lower() in ["exit", "q"]:
                print("[INFO] Terminating session. Goodbye.")
                break

            if not incident_query:
                continue

            chunk_id, resolution = execute_incident_query(
                client, embedder, collection, incident_query, conversation_history
            )

            print("\n" + "-" * 60)
            print(f"[Correlated Knowledge Base Reference]: {chunk_id}")
            print("-" * 60)
            print(resolution)
            print("-" * 60)

            # Append turns to history (keeping window compact, e.g., last 6 turns)
            conversation_history.append({"role": "user", "content": incident_query})
            conversation_history.append({"role": "assistant", "content": resolution})
            if len(conversation_history) > 6:
                conversation_history = conversation_history[-6:]

        except KeyboardInterrupt:
            print("\n[INFO] Session interrupted by user. Exiting.")
            break
        except Exception as err:
            print(f"[ERROR] Failed to process query: {err}")


if __name__ == "__main__":
    main()