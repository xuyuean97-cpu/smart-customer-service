# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Smart Customer Service System (智能客服系统) v0.1.4 — an open-source, multi-agent e-commerce intelligent customer service system built with **LangGraph** and **FastAPI**. Supports multi-tenant, order/logistics queries via Text2SQL, WeChat/mini-program channel access, and multi-platform API integration (JD, Taobao, etc.).

## Coding Standards (CRITICAL)

These principles are non-negotiable. Every code change must respect them.

### 1. Clean Code & Architecture
- **Single Responsibility**: Files over 300 lines must be split. Classes/functions over 80 lines need justification.
- **Type Hints**: All function signatures must use strict Python 3.12+ type hints (`dict[str, Any]`, `Sequence[T]`, `Callable[[X], Y]`). No bare `dict`/`list`.
- **Docstrings**: Google-style for all public functions. Include `Args:`, `Returns:`, `Raises:` sections.

### 2. AI & Agent Workflow
- **LangGraph nodes** should be pure-ish functions or single-responsibility classes. Inject dependencies, don't hardcode.
- **LLM output parsing** MUST use Pydantic validation. Every parse site must catch `ValidationError` and have a retry/fallback strategy — never let a malformed LLM response crash the node silently.
- **Text2SQL results** must be validated before execution. Reject destructive statements (DROP, DELETE, TRUNCATE).

### 3. Concurrency & Performance
- **Zero tolerance for blocking `asyncio` event loop**. No `requests`, no sync DB drivers, no `time.sleep()`. Use `aiohttp`, `asyncpg`, `asyncio.sleep()`.
- **Every external call** (LLM API, ChromaDB, Redis, PostgreSQL, third-party APIs) must have an explicit timeout and a circuit-breaker/fallback.
- **Parallel I/O** via `asyncio.gather()` or `asyncio.TaskGroup` wherever independent calls can be made concurrently.

### 4. Defensive Programming
- **Never trust external input**: LLM output, API responses, WebSocket messages, callback payloads — all must be validated before use.
- **Every external call** must be wrapped in `try...except` with structured logging (`logger.error(..., exc_info=True)`). Never `except: pass`.
- **SQL injection prevention**: all Text2SQL queries use parameterized placeholders (`$1, $2`), never string concatenation.
- **Data masking**: never log or store plaintext phone numbers, addresses, or real names. Use masked placeholders (`138****0001`, `张**`).

## Commands

```bash
# Install dependencies (uv is the package manager)
uv sync

# Run the dev server (starts on http://0.0.0.0:8081)
uv run main.py

# Run a single Python file
uv run python <path/to/file.py>
```

Tests live in `tests/` with 48 cases across 6 files. Run with `uv run pytest tests/ -v` or a single file: `uv run pytest tests/test_schemas.py -v`.

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

Domain routing through source files (retained old filenames for git history, function names are e-commerce):

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
- **Unified API response format**: all endpoints return `{code: 0, message: "ok", data: {...}}` via `api/response.py` helpers `ok()` and `fail()`.
- **Rate limiting**: `slowapi` with global 100/min default, 10/min on dashboard/admin endpoints. Per-endpoint overrides via `@limiter.limit(...)`.
- **API authentication**: `api/middleware.py` provides `Depends(verify_api_key)` for dashboard/management endpoints that need API-key auth.
- **Data sourcing (Hybrid)**: Text2SQL queries local PostgreSQL first; if stale or empty, falls back to platform API (JD/Taobao) via `EcommercePlatformAdapter`, then UPSERTs to local DB.
- **Platform abstraction**: `agents/ecommerce_service/channels/platforms/__init__.py` defines the `EcommercePlatformAdapter` ABC with TTLCache + `asyncio.Lock` (DCL pattern) for cache stampede prevention.
