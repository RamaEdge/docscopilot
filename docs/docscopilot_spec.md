# DocsCopilot Specification Document

## Purpose
This document defines the functional and technical specifications for DocsCopilot, including agent behaviour, MCP interfaces, workflows, and expected outputs.

## 1. Functional Requirements

### 1.1 Developer Experience
- Trigger documentation generation using Copilot Chat from:
  - Code repo
  - Docs repo
  - Pull Request comments
  - CLI tool
- Developer only provides missing contextual information.
- Developer never manipulates:
  - Templates
  - Style guides
  - Docs repo structure

### 1.2 Output Requirements
- Fully structured documentation draft
- Style‑compliant, template‑correct
- Contains reusable snippets when appropriate
- Written into correct repo location
- Pull Request automatically created

### 1.3 Supported Doc Types
- Concept
- Task / How‑To
- API Reference
- Release Notes
- Feature Overview
- Configuration Reference

The agent selects doc type automatically unless developer overrides.

---

## 2. Agent Behaviour Specification

### 2.1 Inputs
- Feature ID
- Code diff or branch context
- Developer responses to clarifying questions
- Existing documentation (via docs repo server)
- Templates / style guide / snippets

### 2.2 Processing Logic
1. Fetch feature metadata  
2. Infer doc type  
3. Retrieve appropriate template  
4. Generate outline  
5. Pull reusable content blocks  
6. Draft documentation  
7. Validate against style rules  
8. Determine repo path  
9. Write documentation  
10. Open PR  

### 2.3 Decision Rules
- If code changes affect API surface → include API reference
- If new feature → include Concept + Task doc
- If config changes → generate Configuration Reference update
- If documentation already exists → update instead of creating new file

---

## 3. MCP Server Specifications

### 3.1 Code Context Server
**Functions**
```
get_feature_metadata(feature_id)
get_changed_endpoints(diff)
get_code_examples(path)
```

### 3.2 Templates + Style Server
**Functions**
```
get_template(doc_type)
get_style_guide(product)
get_glossary()
```

### 3.3 Snippets Server
**Functions**
```
find_reusable_blocks(tags)
get_block(block_id)
```

### 3.4 Docs Repo Server
Supports:
- Same‑repo mode
- External‑repo mode

**Functions**
```
suggest_doc_location(feature_id)
write_doc(path, content)
open_pr(branch, title, description)
```

---

## 4. Trigger Flows

### 4.1 Code Repo Trigger
```
@docscopilot generate docs
```

### 4.2 Docs Repo Trigger
```
@docscopilot create docs for FEAT-217 using backend repo
```

### 4.3 PR Comment Trigger
```
@docscopilot update docs
```

### 4.4 CLI Trigger
```
docs-copilot generate --feature FEAT-217
```

---

## 5. Repository Structure Rules

### Same Repo Example
```
/docs/features/<feature-name>.md
/docs/api/<service>/<endpoint>.md
```

### External Repo Example
```
company-docs/product-x/features/<feature>.md
```

Repo paths are abstracted by Docs Repo MCP server.

---

## 6. File Format Requirements
- All docs generated in Markdown
- Heading structure enforced via style guide
- Code blocks annotated with correct language identifiers
- Metadata header included if required by docs system (e.g., Docusaurus, MkDocs)

---

## 7. Security Considerations
- Agent must not modify code
- Agent must operate only in allowed repo paths
- PR creation must use secure tokens
- No template leakage outside repo bounds

---

## 8. Future Enhancements
- Automatic diagram generation
- Release‑level doc sweep
- Docs linting as CI gate
- Semantic search in docs repo for cross‑links

