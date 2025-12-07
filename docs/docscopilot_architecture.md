# DocsCopilot Architecture Document

## Overview
DocsCopilot is an AI‑driven documentation automation system built using MCP servers and a single orchestration agent. It enables developers to generate consistent, style‑compliant product documentation directly from their code repositories or documentation repositories without needing knowledge of templates, structure, or style guides.

## Core Principles
- Developers focus only on feature intent and behaviour.
- The system handles templates, style, reusable content, and repo structure.
- Documentation can be generated regardless of whether docs live in a separate repo or the same repo.
- Copilot Chat acts as the user interface.

## High‑Level Architecture
```
Developer → Copilot Chat → DocsCopilot Agent
                          ↓
                +----------------------+
                |   MCP Servers        |
                +----------------------+
                | Code Context Server  |
                | Templates Server     |
                | Docs Repo Server     |
                | Snippets Server      |
                +----------------------+
```

## Components

### 1. DocsCopilot Agent
A single orchestration agent responsible for:
- Collecting feature metadata from code
- Selecting doc type and template
- Querying reusable content
- Generating drafts
- Enforcing style and structure rules
- Writing files into the correct repository
- Creating PRs

### 2. Code Context MCP Server
Provides:
- Feature metadata (linked issue/PR, code paths, tests)
- API signatures extracted from code
- Change diff context

APIs:
- `get_feature_metadata(feature_id)`
- `get_code_examples(path)`
- `get_changed_endpoints(diff)`

### 3. Templates + Style MCP Server
Provides:
- Documentation templates (Concept, Task, Reference, etc.)
- Style guide rules
- Tone and terminology guidance

APIs:
- `get_template(doc_type)`
- `get_style_guide(product)`
- `get_glossary()`

### 4. Reusable Content MCP Server
Provides:
- Snippets for prerequisites, common tasks, glossary items, shared instructions
- Tagged reusable blocks

APIs:
- `find_reusable_blocks(tags)`
- `get_block(block_id)`

### 5. Docs Repo MCP Server
Abstracts the documentation repository location:
- Supports *same‑repo* or *external‑repo* docs
- Suggests correct path based on feature or module
- Writes documentation files
- Opens PRs

APIs:
- `suggest_doc_location(feature_id)`
- `write_doc(path, content)`
- `open_pr(branch, title, description)`

## Data Flow (Same Repo or External Repo)
1. Developer triggers doc generation in Copilot Chat.
2. DocsCopilot Agent extracts context from the code repo.
3. Templates + style + reusable content retrieved from MCP servers.
4. Agent produces fully‑structured documentation.
5. Docs Repo Server determines actual file path.
6. Documentation file is committed and PR created.
7. Developer reviews PR.

## Trigger Scenarios

### A. Trigger from Code Repo
- Agent reads code changes
- Writes docs to external docs repo or same repo

### B. Trigger from Docs Repo
- Agent reads code metadata from external repository
- Writes docs in local docs folder

### C. Trigger from PR Comment
- Automated doc generation workflow for CI/CD

### D. CLI Trigger
```
docs-copilot generate --feature FEAT-217
```

## Benefits
- Zero dependency on developer knowledge of templates or structure
- Automatic cross‑repo handling
- Consistent documentation quality
- Reusable content ensures uniformity
- Fully auditable via PRs

