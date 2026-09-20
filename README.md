# ai-incident-remediation-engine
AI incident remediation engine for automated host log triage and safe CLI operations.
# 🛡️ AI Incident Remediation Engine (AI-IRE)

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Groq LPU](https://img.shields.io/badge/Inference-Groq%20LPU%20(gpt--oss--120b)-orange?logo=fastapi)](https://groq.com/)
[![ChromaDB](https://img.shields.io/badge/Vector%20DB-ChromaDB-red)](https://www.trychroma.com/)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An enterprise-grade, runbook-grounded **Autonomous SRE Incident Remediation Engine** that accelerates incident triage, parses noisy production logs, inspects live host telemetry, and safely executes non-destructive diagnostic procedures through a whitelisted remediation agent.

---

## 🚀 Key Architectural Capabilities

- **Dense Vector RAG Pipeline:** Ingests and dynamically segments enterprise Markdown runbooks into semantic chunks using `sentence-transformers/all-MiniLM-L6-v2` and persists them in an in-memory `ChromaDB` vector space with top-$k$ context retrieval.
- **Ultra-Low Latency Inference:** Powered by Groq LPUs running high-parameter open models (`gpt-oss-120b`) for real-time root-cause analysis and operational diagnosis.
- **Kernel-Level Host Telemetry:** Direct OS and kernel interface integration via `psutil` providing real-time CPU, RAM, and Disk storage saturation gauges.
- **Security-First Execution Guardrail:** Protects against shell injection attacks using `shlex` POSIX tokenization, strict executable whitelisting (`ping`, `dig`, `curl`, `nslookup`, `ip`, etc.), subprocess timeouts, and OS-aware cross-platform translation (e.g., Linux `-c` vs. Windows `-n`).
- **One-Click In-Chat Remediation:** Automatically parses recommended CLI checks from LLM diagnostics and provides interactive execution buttons directly inside the chat interface.
- **Dynamic Runbook Ingestion & Log Triage:** Operators can upload real-time incident logs (`.log`, `.txt`) and new `.md` runbooks on the fly to trigger instantaneous context re-indexing.

---

## 🏗️ High-Level System Architecture

```text
       +-------------------------------------------------------------+
       |                  SRE Engineer / Operator                    |
       +-------------------------------------------------------------+
                                      |
                      Web UI / CLI Telemetry Stream
                                      v
       +-------------------------------------------------------------+
       |               Streamlit Web Control Plane                   |
       |  - Host Telemetry (psutil)     - File Ingestion (.md/.log)  |
       |  - Conversational History      - One-Click Execution UI     |
       +-------------------------------------------------------------+
                 |                                      |
       Dense Embedding Vector                   Extracted CLI Command
                 v                                      v
       +--------------------+                 +----------------------+
       |   ChromaDB RAG     |                 |  Execution Guardrail |
       | (all-MiniLM-L6-v2) |                 | (Whitelist + shlex)  |
       +--------------------+                 +----------------------+
                 |                                      |
        Runbook Context (Top-2)                 Subprocess Dispatch
                 v                                      v
       +--------------------+                 +----------------------+
       |      Groq LPU      |                 | Host Operating System|
       |   (gpt-oss-120b)   |                 | (Linux / Windows OS) |
       +--------------------+                 +----------------------+
