agent_smith/
├── pyproject.toml               # Dépendances gérées avec uv (Pydantic, etc.)[cite: 10]
├── README.md                    # Spécifications strictes du sujet (en anglais)[cite: 30, 31]
├── BENCHMARK_REPORT.md          # Rapport comparatif des 5 modèles sur SWE-bench[cite: 24]
├── sandbox_template.json        # Fichier d'exemple de configuration de la sandbox[cite: 14]
│
├── mcp_tools_mbpp.py            # Outils MCP pour le benchmark MBPP (à la racine)[cite: 16, 18]
├── mcp_tools_swebench.py        # Outils MCP pour le benchmark SWE-bench (à la racine)
│
├── agent_mbpp/                  # Module exécutable via `python -m agent_mbpp`[cite: 18]
│   ├── __init__.py
│   └── __main__.py              # Point d'entrée CLI pour MBPP[cite: 18]
│
├── agent_swebench/              # Module exécutable via `python -m agent_swebench`[cite: 20]
│   ├── __init__.py
│   └── __main__.py              # Point d'entrée CLI pour SWE-bench[cite: 20]
│
└── src/                         # Cœur du framework agentique[cite: 10, 11]
    ├── __init__.py
    ├── models.py                # Modèles Pydantic (SandboxConfig, StepMetrics, etc.)[cite: 12, 13, 17]
    │
    ├── sandbox/                 # Moteur du bac à sable[cite: 10, 14]
    │   ├── __init__.py
    │   ├── cli.py               # Point d'entrée du REPL `uv run sandbox`[cite: 14, 15]
    │   ├── executor.py          # Gestionnaire du processus parent / timeout / signaux[cite: 14, 15, 16]
    │   ├── worker.py            # Processus enfant isolé (RLIMIT, builtins, hooks)[cite: 16, 17]
    │   ├── guards.py            # Filtrage des imports, restriction d'open, réseau[cite: 16, 17]
    │   └── manual.py            # Générateur dynamique du manuel d'outils pour le prompt[cite: 16]
    │
    ├── mcp/                     # Intégration Model Context Protocol[cite: 16]
    │   ├── __init__.py
    │   ├── client.py            # Client MCP (connexions stdio et HTTP)[cite: 9, 16]
    │   └── wrappers.py          # Conversion des outils MCP en fonctions Python natives[cite: 16, 17]
    │
    ├── llm/                     # Couche d'interaction avec les LLMs[cite: 10, 23]
    │   ├── __init__.py
    │   ├── client.py            # Client abstrait multi-fournisseurs (OpenRouter, Groq, etc.)[cite: 10, 23, 24]
    │   └── token_manager.py     # Rotation des clés API et gestion des quotas/retries[cite: 13, 24]
    │
    ├── agent/                   # Orchestrateur de la boucle agentique[cite: 9, 10, 11]
    │   ├── __init__.py
    │   ├── loop.py              # Cycle Thought -> Code -> Observation[cite: 6, 11]
    │   ├── parser.py            # Extraction Markdown et conversion XML/JSON vers Python[cite: 11]
    │   └── prompt.py            # Construction du prompt système avec exemples[cite: 12]
    │
    └── docker/                  # Gestion des conteneurs pour SWE-bench[cite: 19]
        ├── __init__.py
        └── manager.py           # Cycle de vie des conteneurs et nettoyage garanti[cite: 19, 27, 28]