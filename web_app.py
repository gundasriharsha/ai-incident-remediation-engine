"""
AI Incident Remediation Engine (AI-IRE) - Web Control Plane
Integrated with:
1. Dense Vector RAG (ChromaDB + Sentence-Transformers)
2. Ultra-low Latency Inference (Groq LPU)
3. Multi-Turn Conversational Memory
4. Automated Host Log Diagnostics
5. Dynamic Runbook Ingestion
6. Safe Whitelisted Subprocess Remediation Agent
"""

import os
import glob
import subprocess
import shlex
from typing import Tuple, List, Dict
import streamlit as st
import chromadb
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from groq import Groq

# Page layout configuration
st.set_page_config(
    page_title="AI Incident Remediation Engine",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

DOCS_DIR = "docs"
os.makedirs(DOCS_DIR, exist_ok=True)

# Whitelist allowed commands for safe execution
ALLOWED_EXECUTABLES = {
    "ping", "curl", "nslookup", "dig", "traceroute", "tracert",
    "ip", "lsblk", "hostname", "uptime", "whoami"
}

def execute_safe_command(command_str: str) -> Tuple[bool, str]:
    """
    Validates and securely executes whitelisted diagnostic commands.
    Prevents execution of arbitrary or destructive shell operations.
    """
    trimmed_cmd = command_str.strip()
    if not trimmed_cmd:
        return False, "Error: Empty command provided."

    try:
        parsed_args = shlex.split(trimmed_cmd)
    except Exception as parse_err:
        return False, f"Command parsing failed: {parse_err}"

    binary = os.path.basename(parsed_args[0]).lower()

    if binary not in ALLOWED_EXECUTABLES:
        return False, f"Security Policy Violation: Executable '{binary}' is not permitted in the safe diagnostics whitelist."

    try:
        # Run process safely without raw shell=True to avoid injection
        process_run = subprocess.run(
            parsed_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=12
        )
        output = process_run.stdout if process_run.stdout else process_run.stderr
        return True, output if output else "[Process executed successfully with no standard output]"
    except subprocess.TimeoutExpired:
        return False, "Execution timed out (12s limit exceeded)."
    except FileNotFoundError:
        return False, f"Command '{binary}' not found on host system."
    except Exception as ex:
        return False, f"Execution failed: {str(ex)}"


@st.cache_resource
def initialize_backend() -> Tuple[SentenceTransformer, chromadb.Client, Groq]:
    """Loads embedding model, builds vector database client, and initializes Groq client."""
    if not GROQ_API_KEY:
        st.error("GROQ_API_KEY not found in .env file!")
        st.stop()

    embedder = SentenceTransformer("all-MiniLM-L6-v2")
    chroma_client = chromadb.Client()
    groq_client = Groq(api_key=GROQ_API_KEY)
    return embedder, chroma_client, groq_client


def get_or_build_collection(embedder: SentenceTransformer, chroma_client: chromadb.Client):
    """Parses all markdown runbooks and returns the populated collection."""
    try:
        chroma_client.delete_collection("web_infra_kb")
    except Exception:
        pass

    collection = chroma_client.create_collection(name="web_infra_kb")
    doc_chunks: List[str] = []
    doc_ids: List[str] = []

    for filepath in glob.glob(os.path.join(DOCS_DIR, "*.md")):
        with open(filepath, "r", encoding="utf-8") as file:
            content = file.read()
            sections = content.split("## ")
            for idx, section in enumerate(sections):
                cleaned_text = section.strip()
                if cleaned_text and not cleaned_text.startswith("# Enterprise"):
                    doc_chunks.append("## " + cleaned_text)
                    doc_ids.append(f"{os.path.basename(filepath)}_section_{idx}")

    if doc_chunks:
        embeddings = embedder.encode(doc_chunks).tolist()
        collection.add(ids=doc_ids, documents=doc_chunks, embeddings=embeddings)

    return collection, len(doc_chunks)


# Initialize backend
embedder, chroma_client, groq_client = initialize_backend()

if "collection" not in st.session_state:
    st.session_state.collection, st.session_state.chunk_count = get_or_build_collection(embedder, chroma_client)

if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar configuration
with st.sidebar:
    st.title("🛡️ AI-IRE")
    st.caption("AI Incident Remediation Engine")
    st.divider()

    st.subheader("System Telemetry")
    st.success("Vector DB: ChromaDB (Online)")
    st.info(f"Indexed Runbook Chunks: {st.session_state.chunk_count}")
    st.info("Embedding: all-MiniLM-L6-v2")
    st.info("Inference: Groq LPU (gpt-oss-120b)")

    st.divider()
    st.subheader("⚡ Remediation Agent (Safe Execution)")
    st.caption("Execute verified non-destructive diagnostic commands directly.")
    agent_cmd = st.text_input("Diagnostic Command", value="ping -c 3 8.8.8.8" if os.name != 'nt' else "ping -n 3 8.8.8.8")
    
    if st.button("Run Remediation Command", use_container_width=True):
        with st.spinner("Executing command on host environment..."):
            success, result = execute_safe_command(agent_cmd)
            if success:
                st.success("Execution Successful")
                st.code(result, language="bash")
            else:
                st.error("Execution Blocked / Failed")
                st.code(result, language="bash")

    st.divider()
    st.subheader("📚 Dynamic Runbook Ingestion")
    uploaded_runbook = st.file_uploader(
        "Upload new runbook (.md)",
        type=["md"],
        help="Upload markdown runbooks to dynamically re-index vector knowledge base."
    )

    if uploaded_runbook is not None:
        if st.button("Index Runbook", use_container_width=True):
            save_path = os.path.join(DOCS_DIR, uploaded_runbook.name)
            with open(save_path, "wb") as f:
                f.write(uploaded_runbook.getbuffer())
            
            st.session_state.collection, st.session_state.chunk_count = get_or_build_collection(embedder, chroma_client)
            st.success(f"Ingested '{uploaded_runbook.name}' ({st.session_state.chunk_count} chunks)")
            st.rerun()

    st.divider()
    st.subheader("📂 Diagnostic Log Triage")
    uploaded_file = st.file_uploader(
        "Upload host log file (.log, .txt)",
        type=["log", "txt"]
    )

    if uploaded_file is not None:
        if st.button("Analyze Uploaded Log", use_container_width=True):
            log_bytes = uploaded_file.read()
            log_text = log_bytes.decode("utf-8", errors="ignore")
            log_sample = "\n".join(log_text.splitlines()[-40:])

            query_vector = embedder.encode([log_sample]).tolist()
            search_results = st.session_state.collection.query(query_embeddings=query_vector, n_results=1)

            matched_context = search_results["documents"][0][0]
            matched_id = search_results["ids"][0][0]

            triage_prompt = (
                f"You are the AI Incident Remediation Engine analyzing raw infrastructure logs.\n\n"
                f"Runbook Context:\n{matched_context}\n\n"
                f"Log Snippet:\n```\n{log_sample}\n```\n\n"
                f"Task: Identify failure pattern, correlate with runbook, and provide immediate root cause and CLI remediation steps."
            )

            with st.spinner("Triaging log dump against runbook..."):
                try:
                    response = groq_client.chat.completions.create(
                        messages=[
                            {"role": "system", "content": "Provide crisp, operational root-cause analysis and remediation steps from logs."},
                            {"role": "user", "content": triage_prompt}
                        ],
                        model="openai/gpt-oss-120b",
                        temperature=0.1
                    )
                    triage_result = response.choices[0].message.content

                    st.session_state.messages.append({
                        "role": "user",
                        "content": f"Uploaded log file: `{uploaded_file.name}` for triage."
                    })
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": triage_result,
                        "reference": matched_id
                    })
                    st.rerun()

                except Exception as ex:
                    st.error(f"Log analysis failed: {ex}")

    st.divider()
    if st.button("Clear Chat Session", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# Main Chat View
st.title("🛡️ AI Incident Remediation Engine")
st.markdown(
    "Runbook-grounded autonomous diagnostics, host log parsing, and safe operational remediation."
)

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "reference" in msg and msg["reference"]:
            st.caption(f"📂 Runbook Match: `{msg['reference']}`")

if user_prompt := st.chat_input("Describe the infrastructure incident or paste an error message..."):
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.markdown(user_prompt)

    query_vector = embedder.encode([user_prompt]).tolist()
    search_results = st.session_state.collection.query(query_embeddings=query_vector, n_results=1)

    matched_context = search_results["documents"][0][0]
    matched_id = search_results["ids"][0][0]

    system_instruction = (
        "You are the AI Incident Remediation Engine (AI-IRE).\n"
        "Your objective is to diagnose server, storage, and container incidents based on the provided runbook context "
        "and active conversation history.\n\n"
        "Rules:\n"
        "1. For questions about prior conversation turns or session context, answer directly using the chat history.\n"
        "2. For operational issues, prioritize the runbook context. If an incident resolution is completely absent from both "
        "the context and history, state: 'Resolution context is not available in the ingested knowledge base.'\n"
        "3. Provide structured, actionable CLI steps with code blocks where applicable."
    )

    history_payload = [{"role": "system", "content": system_instruction}]
    for m in st.session_state.messages[:-1]:
        history_payload.append({"role": m["role"], "content": m["content"]})

    current_turn = (
        f"Retrieved Runbook Context:\n{matched_context}\n\n"
        f"Current Engineer Input:\n{user_prompt}"
    )
    history_payload.append({"role": "user", "content": current_turn})

    with st.chat_message("assistant"):
        with st.spinner("Analyzing runbook context & correlating root cause..."):
            try:
                response = groq_client.chat.completions.create(
                    messages=history_payload,
                    model="openai/gpt-oss-120b",
                    temperature=0.1
                )
                resolution_text = response.choices[0].message.content
                st.markdown(resolution_text)
                st.caption(f"📂 Runbook Match: `{matched_id}`")

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": resolution_text,
                    "reference": matched_id
                })

            except Exception as e:
                st.error(f"Inference failed: {e}")