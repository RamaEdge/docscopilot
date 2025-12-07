# DocsCopilot

AI-driven documentation automation system built using MCP (Model Context Protocol) servers.

## Overview

DocsCopilot enables developers to generate consistent, style-compliant product documentation directly from their code repositories without needing knowledge of templates, structure, or style guides.

## Installation

### Prerequisites

- Python 3.11 or higher
- pip

### Development Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd docscopilot
   ```

2. Install the project in development mode:
   ```bash
   pip install -e .
   ```

3. Install development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```

## Project Structure

```
docscopilot/
├── src/
│   ├── code_context_server/    # Code Context MCP Server
│   ├── templates_style_server/  # Templates + Style MCP Server
│   └── docs_repo_server/        # Docs Repo MCP Server
├── tests/
│   ├── unit/                    # Unit tests
│   └── integration/             # Integration tests
├── config/                      # Configuration files
├── scripts/                     # Utility scripts
└── container/                   # Container configuration
```

## Documentation

- [Architecture Document](docs/docscopilot_architecture.md) - High-level system architecture
- [Specification Document](docs/docscopilot_spec.md) - Functional and technical specifications
- [Implementation Plan](docs/IMPLEMENTATION_PLAN.md) - Detailed implementation plan with issues

## Project Status

🚧 **In Development** - See [Implementation Plan](docs/IMPLEMENTATION_PLAN.md) for current status and roadmap.

## Quick Links

- [Implementation Plan with Issues](docs/IMPLEMENTATION_PLAN.md)