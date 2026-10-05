# Steward (Code-Daemon)
### Next-Generation Autonomous Software Engineering Platform

Steward is an enterprise-grade autonomous software engineering platform capable of operating as a high-density local desktop application and as a detached, headless cloud worker daemon.

Developers can dispatch long-running engineering tasks from their desktop workstation, close their laptop or disconnect from the network, and allow the agent to execute in the cloud or background server. Upon reconnection, the desktop client automatically synchronizes session state, journals, terminal outputs, and file diffs via an $O(\log N)$ B-Tree indexed catch-up protocol.

---

## Key Capabilities

1. **Dual-Engine Brain (NVIDIA NIM)**:
   - High-level architectural reasoning via **DeepSeek-R1** (`<think>` CoT stream).
   - High-precision discrete tool execution via **Llama 3.3 70B Instruct** / **Nemotron 70B**.
   - Context distillation: CoT reasoning tokens are routed exclusively to the developer UI reasoning pane, preserving the actor's context window.
   - Robust lookahead buffer streaming state machine handling split tags across chunk boundaries.

2. **Dual-Tier Hybrid Persistence Engine**:
   - Sub-millisecond local SQLite with WAL mode (`journal_mode=WAL`), busy timeouts, and indexed timeline tables (`timeline_events(session_id, seq)`).
   - Outbox pattern replication worker syncing transactions to **Render Cloud PostgreSQL** with exponential backoff and full jitter.
   - Zero latency offline operation: if cloud connection drops, local execution continues unaffected.

3. **Universal Execution Engines**:
   - **File Engine**: Atomic writes with staging and `os.replace`, mtime concurrency guards, 3-tier fuzzy search-and-replace (Exact -> Whitespace -> Difflib Sequence Matcher), snapshot rollbacks.
   - **Terminal Engine**: Asyncio subprocess execution wrapped in **Win32 Job Objects** (`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`), guaranteeing zero orphaned processes (`node.exe`, `python.exe`, `cargo.exe`), with native ConPTY support.
   - **Computer Use Engine**: Per-Monitor DPI awareness (v2), MSS DirectX screen capture, native WinRT OCR, `SendInput` hardware synthesis, and UI window inspection.
   - **Universal MCP Client**: Model Context Protocol (stdio JSON-RPC 2.0 & SSE).

4. **Security & Sandboxing**:
   - PowerShell cmdlet and alias canonicalization (`ri`, `rm`, `del` -> `Remove-Item`; `kill` -> `Stop-Process`).
   - Destructive command heuristics (blocking catastrophic system commands like `diskpart`, `format`, `reg delete`, `git push --force`).
   - Workspace boundary enforcer preventing directory escape.
   - Interactive security clearance dialogs in Guarded mode.

5. **High-Density Dark Developer Desktop UI**:
   - PyQt6 / QtPy interface with Linear/Cursor dark developer aesthetic (zero emojis).
   - Dedicated secondary `DaemonClientThread` (`QThread`) running asyncio WebSocket communications, communicating exclusively via thread-safe `pyqtSignal` events.
   - Live collapsible reasoning pane, terminal output stream, unified/side-by-side diff viewer, and session tree.

6. **Production Multi-Binary Packaging**:
   - PyInstaller pipeline building `agent_daemon.exe` and `agent_app.exe`.
   - Inno Setup 6 script (`setup_installer.iss`) for single-click Windows installation.

---

## Quickstart

### Prerequisites
- Python 3.10+ (Tested on Windows with Python 3.14)
- Verified libraries: `PyQt6`, `qtpy`, `httpx`, `aiohttp`, `websockets`, `pywin32`, `mss`, `psycopg2`, `pg8000`, `pytest`

### Running the Headless Daemon
```powershell
python run_daemon.py --port 8765
```

### Launching the Desktop Client
```powershell
python run_app.py --port 8765
```

### Configuration (.env)
```env
# NVIDIA NIM API Key
NVIDIA_API_KEY=nvapi-your-key-here

# Cloud Database Synchronization (Optional)
RENDER_POSTGRES_DSN=postgres://user:pass@host.render.com:5432/dbname
RENDER_SYNC_ENABLED=true

# Security Mode (autonomous | guarded | sandboxed)
STEWARD_PERMISSION_MODE=guarded
```

---

## Running the Automated Test Suite

```powershell
pytest -v
```
All unit and integration tests verify the reasoning parser, file tools, terminal job objects, timeline journal reconnects, storage sync, and permission guard.
