# Local AI Workflows - Project Plan

## Overview

Desktop application for building and executing visual workflows between local AI models via Ollama.

**Stack:** Tauri (Rust) + Vue 3 (Composition API) + Vite + Vue Flow

---

## Docker Architecture

### Simplified Setup (Ollama on Host)

| Component | Location | Purpose |
|-----------|----------|---------|
| **dev-frontend** | Docker | Vue 3 + Vite dev server (hot reload) |
| **Tauri** | Host (Windows) | Desktop app shell, system APIs |
| **Ollama** | Host (Windows) | Already installed, GPU access native |

### Why Tauri on Host?

Tauri requires native Windows SDK and Rust toolchain to build desktop apps. It's not practical to run in Docker because:
- Needs access to Windows APIs for native window management
- Requires WebView2 (Edge-based) which is Windows-specific
- GPU acceleration for the UI works better natively
- Build process creates `.exe` files for Windows

**Development workflow:**
1. Frontend (Vue/Vite) runs in Docker with hot reload
2. Tauri dev mode runs on host, connects to Vite dev server
3. Ollama runs on host at `localhost:11434`

---

## Phase 1: Core Infrastructure

### Tasks
- [ ] 1.1 Install Rust + Tauri CLI on Windows host
- [ ] 1.2 Create Docker Compose for Vue/Vite dev environment
- [ ] 1.3 Scaffold Vue 3 + Vite + TypeScript project
- [ ] 1.4 Initialize Tauri in the project
- [ ] 1.5 Setup basic tab navigation structure (Vue Router or component tabs)
- [ ] 1.6 Configure Tailwind CSS + dark mode
- [ ] 1.7 Verify Ollama connection from frontend (`http://localhost:11434`)

### Deliverable
Basic Tauri app with tabbed interface, dark theme, connecting to local Ollama.

---

## Phase 2: Workflow Builder Canvas

### Tasks
- [ ] 2.1 Install and configure Vue Flow
- [ ] 2.2 Create WorkflowBuilder tab/view
- [ ] 2.3 Implement canvas with zoom, pan, minimap, controls
- [ ] 2.4 Create sidebar with draggable node types
- [ ] 2.5 Implement drag & drop from sidebar to canvas
- [ ] 2.6 Create base custom node component (consistent styling)
- [ ] 2.7 Implement workflow save/load (JSON to local file via Tauri)
- [ ] 2.8 Add workflow execution engine (traverse nodes in order)

### Deliverable
Functional canvas where nodes can be placed, connected, saved, and loaded.

---

## Phase 3: Node System

### Core Nodes to Implement

| Node | Priority | Description |
|------|----------|-------------|
| **UserInput** | P0 | Textarea for initial instruction |
| **LLMCall** | P0 | Call Ollama model with prompt template |
| **Output** | P0 | Display text/code/logs |
| **Condition** | P1 | If/else branching on output |
| **FileRead** | P1 | Read file content into workflow |
| **FileWrite** | P1 | Write output to file |
| **ShellExecute** | P1 | Run commands (npm, pytest, etc.) |
| **HumanReview** | P2 | Pause workflow for manual validation |
| **Memory** | P2 | Persist variables between nodes |

### Tasks
- [ ] 3.1 Define node data schema (inputs, outputs, config)
- [ ] 3.2 Implement UserInput node
- [ ] 3.3 Implement LLMCall node with Ollama integration
- [ ] 3.4 Implement Output node (markdown/code rendering)
- [ ] 3.5 Implement Condition node with expression evaluation
- [ ] 3.6 Implement FileRead/FileWrite nodes (via Tauri fs API)
- [ ] 3.7 Implement ShellExecute node (via Tauri shell API)
- [ ] 3.8 Implement HumanReview node with modal popup
- [ ] 3.9 Implement Memory node for context persistence

### Deliverable
All core nodes functional and executable in workflows.

---

## Phase 4: Ollama Integration

### Tasks
- [ ] 4.1 Create Ollama service layer (TypeScript)
- [ ] 4.2 Implement model listing (`GET /api/tags`)
- [ ] 4.3 Implement chat completion (`POST /api/chat`)
- [ ] 4.4 Add streaming response support
- [ ] 4.5 Create model selector component
- [ ] 4.6 Add parameter controls (temperature, top_p, etc.)
- [ ] 4.7 Handle connection errors gracefully
- [ ] 4.8 Add model presets for roles (Planner, Coder)

### Deliverable
Robust Ollama integration with model selection and streaming.

---

## Phase 5: Additional Tabs

### 5A - Simple Chat Tab
- [ ] 5A.1 Create Chat view component
- [ ] 5A.2 Implement message list (user/assistant)
- [ ] 5A.3 Add model selector
- [ ] 5A.4 Implement streaming responses
- [ ] 5A.5 Add chat history persistence

### 5B - Code Editor Tab
- [ ] 5B.1 Integrate Monaco Editor or CodeMirror
- [ ] 5B.2 Create file tree sidebar (via Tauri fs)
- [ ] 5B.3 Implement file open/save
- [ ] 5B.4 Add diff preview component
- [ ] 5B.5 Integrate terminal panel (via Tauri shell)

### Deliverable
Fully functional Chat and Code Editor tabs.

---

## Phase 6: Polish & Advanced Features (Future)

- [ ] History & Debug tab (execution logs, replay)
- [ ] Models Hub (manage Ollama models)
- [ ] Pre-configured agent templates
- [ ] Workflow import/export
- [ ] Keyboard shortcuts
- [ ] Settings panel

---

## Technical Notes

### Host Requirements (Windows 11)
- **Rust:** Install via rustup.rs
- **Tauri CLI:** `cargo install tauri-cli`
- **Node.js:** v18+ for Vite/Vue
- **Ollama:** Already installed at `localhost:11434`
- **WebView2:** Usually pre-installed on Windows 11

### Docker Dev Container
```dockerfile
# For Vue/Vite development only
FROM node:20-alpine
WORKDIR /app
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host"]
```

### Ollama API Endpoints
- `GET http://localhost:11434/api/tags` - List models
- `POST http://localhost:11434/api/chat` - Chat completion
- `POST http://localhost:11434/api/generate` - Text generation

---

## Getting Started (Next Steps)

1. Install Rust on Windows: https://rustup.rs
2. Install Tauri CLI: `cargo install tauri-cli`
3. Create the Docker Compose file
4. Scaffold the Vue + Tauri project
5. Start building Phase 1
