# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Smart Customer Service System (智能客服系统) v0.1.4 — an open-source, multi-agent intelligent customer service system built with **LangGraph** and **FastAPI**. Originally designed for the airport/aviation domain, currently being **actively refactored** into an e-commerce service system. The refactoring is in progress: old airport-domain code is commented out alongside new e-commerce code, and class/function renames are ongoing (e.g. `AirportMainServiceState` → `EcommerceMainServiceState`, `flight.py` → order logistics, `airport.py` → product info).

## Commands

```bash
# Install dependencies (uv is the package manager)
uv sync

# Run the dev server (starts on http://0.0.0.0:8081)
uv run main.py

# Run a single Python file
uv run python <path/to/file.py>
```

There is no test suite yet (`pytest` and `pytest-asyncio` are in dependencies but no `tests/` directory exists).

## Architecture

### Three LangGraph Graphs

The system registers three StateGraph instances, all managed by the `GraphManager` singleton in `agents/ecommerce_service/graph_compile.py`:

1. **`ecommerce_service_graph`** — the main service graph. User input flows through: translate → emotion detection → (transfer to human OR image analysis) → intent routing → domain agent → translate output → END.
2. **`question_recommend_graph`** — suggests related questions ("guess what you want to ask").
3. **`business_recommend_graph`** — suggests related services ("guess what you want to do").

Graphs are compiled with `AsyncRedisSaver` for checkpoint persistence. Each graph gets a unique Redis index prefix via MD5 hash.

### Main Graph Node Flow

```
User Input
  → translate_input_node (language detection + Chinese translation)
  → emotion_node (sentiment analysis; negative → transfer_to_human)
  → images_thinking_node (multimodal image analysis)
  → router (LLM intent classification)
     → order_logistics_search_node → order_logistics_agent_node  (orders/shipping)
     → product_info_search_node → product_info_agent_node        (product FAQ/knowledge)
     → business_assistant_node                                   (transactions)
     → chitchat_node                                             (casual conversation)
  → translate_output_node
  → END
```

### FastAPI Layer

- `main.py` — app entry point, lifespan management (DB init, graph registration, memory manager init), CORS, static file mounting
- `api/router.py` — aggregates all API sub-routers
- `api/chat.py` — main chat endpoint (largest file, ~45KB)
- `auth/` — JWT + Argon2 auth with SMS verification, SQLAlchemy User model

### Configuration System (Three-Tier)

1. **Environment variables** (`.env`) — loaded by `python-dotenv`, driven by `HZ_FUTURE_SMART_BRAIN_ENV` (dev/prod/test).
2. **Environment-specific Python modules** (`config/dev.py`) — `CONFIG` dict loaded dynamically.
3. **Module-specific configs** (`config/modules/agents.py`, `auth.py`, etc.) — merged on top of base config.

Access config via the `ConfigManager` singleton (`config/utils.py`) or the `ConfigFactory` convenience class (`config/factory.py`).

### State Definitions

`agents/ecommerce_service/state.py` defines the TypedDict/BaseModel classes used across all graphs. `EcommerceMainServiceState` extends LangGraph's `MessagesState` with fields for user query, router result, translation result, emotion result, and retrieval result.

### Memory System

Built on **mem0ai** (`AsyncMemory`), managed by `context_engineering/memory_manager.py`. The memory manager is a singleton initialized at app startup. Memory tiers include conversation-level, session profile, daily profile, and deep profile. User profile extraction and operational analytics live under `context_engineering/profile/`.

### External Service Dependencies

All services in the architecture are **external** and can be run locally or via cloud:

| Service | Purpose |
|---|---|
| **LLM API** (OpenAI-compatible) | Three configurable models: main LLM (`LLM_*`), router LLM (`ROUTER_LLM_*`), image LLM (`IMAGE_LLM_*`). Falls back to main LLM if router/image LLM not configured. |
| **Embedding API** (OpenAI-compatible) | Vector embeddings. Defaults to same provider as main LLM if not configured. |
| **ReRank API** (OpenAI-compatible) | Result reranking. Separate from embedding. |
| **Redis** | LangGraph checkpoint persistence + SMS code caching |
| **ChromaDB** | Vector store for memory/knowledge embeddings |
| **PostgreSQL** | Business data for Text2SQL queries |
| **RAGFlow** | External knowledge base management (RAG) |

### Domain Module Mapping

The refactoring maps airport-domain concepts to e-commerce concepts. Source files still use old names but expose new function names:

| File (old name) | New Function Names | Domain |
|---|---|---|
| `main_nodes/airport.py` | `product_info_search`, `product_info_agent` | Product info/knowledge |
| `main_nodes/flight.py` | `order_logistics_search`, `order_logistics_agent` | Orders & logistics |
| `main_nodes/business.py` | `business_agent` | Transactions (refunds, address changes, etc.) |
| `main_nodes/router.py` | `identify_intent`, `route_to_next_node` | Intent classification |
| `main_nodes/chitchat.py` | `chitchat_agent` | Casual conversation |
| `main_nodes/translator.py` | `translate_input`, `translate_output` | Language detection & translation |
| `main_nodes/artificial.py` | `detect_emotion` | Sentiment analysis |
| `main_nodes/human.py` | `transfer_to_human`, `route_to_next` | Human handoff routing |

### Key Design Decisions

- **All LLM calls use OpenAI-compatible API format** — the system never calls provider-specific SDKs. Any provider (DashScope, GLM, SiliconFlow, Xinference, Ollama, vLLM) works as long as it exposes an OpenAI-compatible endpoint.
- **No database migrations** — dev environment uses `Base.metadata.create_all()` at startup. Production should use Alembic (per CONFIGURATION.md) but isn't set up yet.
- **Retry policies** on all graph nodes — 3 attempts for I/O nodes (translation, emotion), 5 attempts for core processing nodes.
- **Prompt templates** live in `agents/ecommerce_service/context_engineering/prompts/` as Python files returning template strings, not separate template files.
- **`uv`** is the package manager, using Aliyun PyPI mirror for faster installs in China.
