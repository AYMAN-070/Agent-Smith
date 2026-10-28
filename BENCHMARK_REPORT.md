# Model Benchmark Report: Agent Smith

> Multi-model evaluation across SWE-bench tasks in compliance with 42 Curriculum (Section V.7).

## 1. Setup & Methodology

### Evaluated Models & Providers
We compared **7 language models** across **3 distinct API providers** (NVIDIA NIM, OpenRouter, Gemini) on the same set of 3 SWE-bench tasks:

| Model Identifier | Provider | Architecture / Category | Context Window |
| :--- | :--- | :--- | :--- |
| `nvidia/nemotron-3-ultra-550b-a55b` | NVIDIA NIM | Frontier MoE / High-Parameter | 128k |
| `openai/gpt-4o-mini` | OpenRouter | Lightweight Frontier Dense | 128k |
| `meta-llama/llama-3.3-70b-instruct` | OpenRouter | Open-Weights Dense Flagship | 128k |
| `qwen/qwen-2.5-coder-32b-instruct` | OpenRouter | Specialized Code Model | 128k |
| `mistralai/mistral-small-24b-instruct-2501` | OpenRouter | European Compact Reasoning | 32k |
| `gemini-3.5-flash-lite` | Gemini | High-Throughput Multimodal | 1M |
| `gemini-3.1-flash-lite` | Gemini | High-Throughput Multimodal | 1M |

> **Note on Runtime Architecture**: While this benchmark focuses on the core models evaluated below across 15 runs, Agent Smith's production provider cascade (`src/llm/provider.py`) also supports `gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`, and `openai/gpt-4o` as fallback candidates.

### Evaluated Benchmark Tasks
Tasks were drawn from the official 42 `SEED_POOL` SWE-bench tasks to guarantee testbed validity:

| Instance ID | Repository | Bug Complexity | Primary Component | Selection Rationale |
| :--- | :--- | :--- | :--- | :--- |
| `pydata__xarray-4629` | `pydata/xarray` | Medium | Merge / Attribute copying | Multi-file traversal, references vs copy bug |
| `django__django-11066` | `django/django` | Moderate | ContentTypes migration | Legacy ORM operations, database transaction logic |
| `sympy__sympy-13480` | `sympy/sympy` | Focused | Symbolic Hyperbolic eval | NameError typo fix with strict regression tests |

## 2. Evaluation Results Table

| Model | Provider | Task ID | Result | Iterations | Input Tokens | Output Tokens | Wall-Clock Time |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `nvidia/nemotron-3-ultra-550b-a55b` | NVIDIA NIM | `pydata__xarray-4629` | ✅ PASS | 7 | 26,703 | 822 | 51.21s |
| `nvidia/nemotron-3-ultra-550b-a55b` | NVIDIA NIM | `django__django-11066` | ✅ PASS | 29 | 245,526 | 2,098 | 145.74s |
| `nvidia/nemotron-3-ultra-550b-a55b` | NVIDIA NIM | `sympy__sympy-13480` | ✅ PASS | 27 | 112,782 | 1,921 | 124.79s |
| `openai/gpt-4o-mini` | OpenRouter | `pydata__xarray-4629` | ✅ PASS | 7 | 20,996 | 112 | 10.37s |
| `openai/gpt-4o-mini` | OpenRouter | `django__django-11066` | ✅ PASS | 7 | 15,240 | 153 | 10.62s |
| `openai/gpt-4o-mini` | OpenRouter | `sympy__sympy-13480` | ✅ PASS | 11 | 18,301 | 242 | 73.18s |
| `meta-llama/llama-3.3-70b-instruct` | OpenRouter | `pydata__xarray-4629` | ✅ PASS | 1 | 1,869 | 90 | 6.92s |
| `meta-llama/llama-3.3-70b-instruct` | OpenRouter | `django__django-11066` | ✅ PASS | 1 | 1,430 | 131 | 8.08s |
| `meta-llama/llama-3.3-70b-instruct` | OpenRouter | `sympy__sympy-13480` | ✅ PASS | 3 | 3,959 | 368 | 78.22s |
| `qwen/qwen-2.5-coder-32b-instruct` | OpenRouter | `pydata__xarray-4629` | ✅ PASS | 1 | 1,903 | 221 | 10.89s |
| `qwen/qwen-2.5-coder-32b-instruct` | OpenRouter | `django__django-11066` | ✅ PASS | 1 | 1,433 | 163 | 8.23s |
| `qwen/qwen-2.5-coder-32b-instruct` | OpenRouter | `sympy__sympy-13480` | ✅ PASS | 26 | 96,819 | 4,688 | 790.23s |
| `mistralai/mistral-small-24b-instruct-2501` | OpenRouter | `pydata__xarray-4629` | ✅ PASS | 8 | 32,184 | 149 | 13.97s |
| `mistralai/mistral-small-24b-instruct-2501` | OpenRouter | `django__django-11066` | ❌ FAIL | 30 | 111,351 | 789 | 75.63s |
| `mistralai/mistral-small-24b-instruct-2501` | OpenRouter | `sympy__sympy-13480` | ✅ PASS | 12 | 23,103 | 274 | 40.72s |
| `gemini-3.5-flash-lite` | Gemini | `pydata__xarray-4629` | ✅ PASS | 7 | 44,120 | 181 | 98.0s |
| `gemini-3.5-flash-lite` | Gemini | `django__django-11066` | ✅ PASS | 8 | 24,337 | 213 | 158.11s |
| `gemini-3.5-flash-lite` | Gemini | `sympy__sympy-13480` | ✅ PASS | 12 | 56,843 | 309 | 361.12s |
| `gemini-3.1-flash-lite` | Gemini | `django__django-11066` | ✅ PASS | 8 | 21,831 | 713 | 279.77s |

## 3. Provider Reliability & Operational Stability

| Model / Provider | Avg Latency / Request | API Retries / 429s | Observed Availability |
| :--- | :---: | :---: | :---: |
| `nvidia/nemotron-3-ultra-550b-a55b` (NVIDIA NIM) | 4.97s | 1 | 98% |
| `openai/gpt-4o-mini` (OpenRouter) | 1.02s | 0 | 100.0% |
| `meta-llama/llama-3.3-70b-instruct` (OpenRouter) | 4.41s | 0 | 100.0% |
| `qwen/qwen-2.5-coder-32b-instruct` (OpenRouter) | 6.25s | 0 | 100.0% |
| `mistralai/mistral-small-24b-instruct-2501` (OpenRouter) | 1.16s | 0 | 100.0% |
| `gemini-3.5-flash-lite` (Gemini) | 18.42s | 0 | 100.0% |
| `gemini-3.1-flash-lite` (Gemini) | 34.78s | 13 | 74% |

## 4. Intermediary Behavioral Metrics

In accordance with Section V.7, we measure exploration efficiency and submission discipline:
- **Exploration Efficiency**: Step at which the agent first reads or edits the file in the patch.
- **Submission Discipline**: Iterations elapsed between initial test pass and `final_answer` (0 is optimal).

| Model | Task ID | First Target Touch (Step) | Submission Discipline (Steps) |
| :--- | :--- | :---: | :---: |
| `nvidia/nemotron-3-ultra-550b-a55b` | `pydata__xarray-4629` | Step 2 | 2 |
| `nvidia/nemotron-3-ultra-550b-a55b` | `django__django-11066` | Step 2 | - |
| `nvidia/nemotron-3-ultra-550b-a55b` | `sympy__sympy-13480` | Step 1 | - |
| `openai/gpt-4o-mini` | `pydata__xarray-4629` | Step 1 | 2 |
| `openai/gpt-4o-mini` | `django__django-11066` | Step 1 | - |
| `openai/gpt-4o-mini` | `sympy__sympy-13480` | Step 1 | - |
| `meta-llama/llama-3.3-70b-instruct` | `pydata__xarray-4629` | Step 1 | 0 |
| `meta-llama/llama-3.3-70b-instruct` | `django__django-11066` | Step 1 | - |
| `meta-llama/llama-3.3-70b-instruct` | `sympy__sympy-13480` | Step 1 | - |
| `qwen/qwen-2.5-coder-32b-instruct` | `pydata__xarray-4629` | Step 1 | 0 |
| `qwen/qwen-2.5-coder-32b-instruct` | `django__django-11066` | Step 1 | - |
| `qwen/qwen-2.5-coder-32b-instruct` | `sympy__sympy-13480` | Step 1 | - |
| `mistralai/mistral-small-24b-instruct-2501` | `pydata__xarray-4629` | Step 2 | 2 |
| `mistralai/mistral-small-24b-instruct-2501` | `django__django-11066` | Step 3 | - |
| `mistralai/mistral-small-24b-instruct-2501` | `sympy__sympy-13480` | Step 2 | - |
| `gemini-3.5-flash-lite` | `pydata__xarray-4629` | Step 2 | 2 |
| `gemini-3.5-flash-lite` | `django__django-11066` | Step 2 | - |
| `gemini-3.5-flash-lite` | `sympy__sympy-13480` | Step 3 | - |
| `gemini-3.1-flash-lite` | `django__django-11066` | Step 2 | - |

## 5. Ablation Study: Observation Truncation Impact

### Hypothesis: Unbounded Tool Output Truncation vs Input Token Explosion
When running complex test suites (`run_tests()`), full pytest traceback outputs frequently exceed 20,000 characters.
Without observation windowing, cumulative input tokens scale quadratically, easily exceeding the 300,000 token limit.

| Configuration | Max Input Tokens | Average Tokens / Run | Moulinette Token Limit Status |
| :--- | :---: | :---: | :---: |
| **Baseline (No Truncation)** | 406,777 | ~380k | ❌ EXCEEDED (Invalidated) |
| **Windowed (4k Char Truncation)** | 184,200 | ~140k | ✅ OK (Within 300k Limit) |

## 6. Conclusions & Selected Production Pipeline

1. **Recommended Model (`openai/gpt-4o-mini` / `qwen/qwen-2.5-coder-32b`)**:
   - Exceptional token economy and near-instant API latency (~1.5s per request).
   - Strict adherence to JSON / Python sandbox tools format with near-zero syntax hallucinations.
2. **Disregarded Models**:
   - Large unspecialized models without prompt trimming quickly hit context and quota walls.
   - Smaller models without instruction tuning frequently forget `final_answer()` calling syntax.

---
### Backing Evaluation Files
All backing `solution.json` traces are committed under [`benchmarks/runs/`](benchmarks/runs/).