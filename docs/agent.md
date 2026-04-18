# 🤖 AI Agent System Documentation

## 📌 Overview

This project implements an **AI Teaching Assistant Agent** based on a Retrieval-Augmented Generation (RAG) architecture, enhanced with:

- Hybrid retrieval (Dense + Sparse + RRF)
- Cross-encoder reranking
- Tool-calling agent loop (OpenAI function calling)
- Vector-based long-term memory (ChromaDB)
- User personalization layer

The system is designed to answer course-related questions accurately using grounded knowledge from course materials while maintaining user-specific memory.

---

## 🏗️ System Architecture

### High-level pipeline:
```
User Query
↓
Memory Retrieval (ChromaDB)
↓
Query → Retrieval Layer
├── Dense Retrieval (Embeddings)
├── Sparse Retrieval (BM25)
└── Hybrid (RRF fusion)
↓
Reranking (Cross-Encoder)
↓
Context Builder
↓
Prompt Generator (with memory injection)
↓
LLM (OpenAI GPT-4o-mini)
↓
Tool Execution Loop (if needed)
↓
Final Answer
↓
Memory Storage Update
```

---

## 🧠 Memory System (in progress)

### Type
- Vector-based long-term memory

### Storage
- ChromaDB persistent vector store

### Embedding model
- `all-MiniLM-L6-v2`

### Memory behavior
- Stores user preferences and stable facts only
- Retrieves semantically relevant memories per query
- Injects memory into LLM prompt

### Example stored memories:
- "User prefers hybrid retrieval for RAG systems"
- "User is building an AI agent with tool calling"
- "User works with cross-encoder reranking"

### Memory flow:
User Input → Extract Memory → Embed → Store in Vector DB
User Query → Embed → Retrieve Relevant Memories → Inject into Prompt

---

## 🔎 Retrieval System

### 1. Dense Retrieval
- Uses embedding similarity search
- Best for semantic queries

### 2. Sparse Retrieval
- BM25 keyword-based search
- Best for:
  - error codes
  - exact terms
  - named entities

### 3. Hybrid Retrieval
- Combines Dense + Sparse using **Reciprocal Rank Fusion (RRF)**

Formula:
```
RRF_score = 1 / (60 + rank_dense) + 1 / (60 + rank_sparse)
```

---

## 🎯 Reranking Layer

### Model
- Cross-encoder: `cross-encoder/ms-marco-MiniLM-L-6-v2`

### Purpose
- Re-score retrieved chunks
- Improve relevance
- Remove noisy documents

### Funnel strategy:

Retrieve top 20 → Rerank → Select top 5 → Send to LLM

---

## 🧩 Tool Calling System

### Framework
- OpenAI function calling API

### Tool flow:
LLM decides → Tool selected → execute_tool() → result returned → LLM synthesizes answer


### Key tool:
- `search_course_material`

### Tool rules:
- Must be used for course-related questions
- If no relevant result → agent must say it doesn't know
- Multiple chunks are merged and summarized

---

## 🧾 Prompt Design

### Core principles:
- Evidence-only reasoning
- No hallucination
- Mandatory citation from retrieved chunks
- Memory-aware responses

### Prompt structure:
System Instructions
User Memory
Retrieved Context
User Question
## ⚙️ Agent Loop

The agent follows iterative tool-calling logic:

1. Receive user input
2. Call LLM with tools enabled
3. If tool is requested:
   - execute tool
   - append result
   - continue loop
4. If no tool:
   - return final answer
5. Store memory after completion

---

## 🧪 Key Features

### ✔ Retrieval Augmentation
- Dense + Sparse + Hybrid search

### ✔ Reranking
- Cross-encoder based ranking refinement

### ✔ Tool-augmented reasoning
- Dynamic function calling

### ✔ Memory system
- Vector-based user personalization

### ✔ Multi-turn reasoning
- Iterative agent loop (max_turns control)

---

## 📊 Design Goals

- High factual accuracy (grounded in documents)
- Low hallucination rate
- Personalized responses per user
- Scalable retrieval architecture
- Modular agent design (pluggable components)

---

## 🚀 Future Improvements

Planned upgrades:

- Memory summarization (compression of long-term memory)
- Query rewriting (multi-query expansion)
- Semantic caching layer
- Multi-agent architecture (planner + executor)
- Evaluation framework (faithfulness / recall metrics)

---
