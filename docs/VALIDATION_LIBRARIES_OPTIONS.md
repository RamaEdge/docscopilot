# Validation Libraries Options

This document outlines options for replacing custom validation logic in `src/shared/security.py` with standard validation libraries.

## Current Situation

We have a custom `SecurityValidator` class with manual validation logic for:
- Feature IDs
- Branch names
- Product names
- Document types
- File paths
- Git patterns
- Commit hashes

**Problem:** We're reinventing validation that standard libraries already provide.

### ✅ Phase 1 Complete: Configuration Validation

**Status:** Configuration field validation has been implemented (Phase 1).

All new configurable values now have proper validation:
- ✅ URL validation for API endpoints (prevents SSRF)
- ✅ Hostname validation (RFC 1123)
- ✅ Timeout range validation (prevents DoS)
- ✅ Retry configuration validation
- ✅ Enum validation for `repo_mode`
- ✅ Directory name validation
- ✅ Document type directories mapping validation

## Available Libraries

### Already in Use
- **Pydantic 2.0** - Already a dependency, has excellent validation capabilities
- **pathlib** - Standard library, already partially used

### Could Add
- **validators** - Common validation functions
- **python-validators** - Another validation library
- **cerberus** - Data validation library

---

## Immediate Priority: Validate Configuration Fields

Before migrating user input validation, we **must** add validation to new configuration fields to prevent security vulnerabilities.

### Config Field Validation Examples

#### 1. API URL Validation (High Priority)

```python
from pydantic import field_validator
from urllib.parse import urlparse
import re

class DocsRepoConfig(ServerConfig):
    github_api_base_url: str = Field(
        default="https://api.github.com",
        description="GitHub API base URL (supports GitHub Enterprise)",
    )
    
    @field_validator("github_api_base_url", "gitlab_api_base_url")
    @classmethod
    def validate_api_url(cls, v: str) -> str:
        """Validate API base URL format."""
        if not isinstance(v, str):
            raise ValueError("URL must be a string")
        
        v = v.strip()
        if not v:
            raise ValueError("URL cannot be empty")
        
        # Parse URL
        parsed = urlparse(v)
        
        # Must be HTTPS (security requirement)
        if parsed.scheme != "https":
            raise ValueError("API URL must use HTTPS scheme")
        
        # Must have netloc
        if not parsed.netloc:
            raise ValueError("Invalid URL format: missing hostname")
        
        # Check for dangerous patterns
        if any(char in v for char in ["\x00", "\n", "\r", "\t"]):
            raise ValueError("URL contains dangerous characters")
        
        # Length limit
        if len(v) > 500:
            raise ValueError("URL too long (max 500 characters)")
        
        return v
```

#### 2. Hostname Validation (High Priority)

```python
@field_validator("github_host", "gitlab_host")
@classmethod
def validate_hostname(cls, v: str) -> str:
    """Validate hostname format (RFC 1123)."""
    if not isinstance(v, str):
        raise ValueError("Hostname must be a string")
    
    v = v.strip().lower()
    if not v:
        raise ValueError("Hostname cannot be empty")
    
    # Basic hostname validation (RFC 1123)
    hostname_pattern = r"^[a-z0-9]([a-z0-9\-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9\-]{0,61}[a-z0-9])?)*$"
    if not re.match(hostname_pattern, v):
        raise ValueError("Invalid hostname format")
    
    # Length limit (RFC 1123: max 253 characters)
    if len(v) > 253:
        raise ValueError("Hostname too long (max 253 characters)")
    
    # Check for dangerous patterns
    if any(char in v for char in ["\x00", "\n", "\r", "\t", " "]):
        raise ValueError("Hostname contains dangerous characters")
    
    return v
```

#### 3. Timeout Validation (High Priority)

```python
class ServerConfig(BaseModel):
    git_command_timeout: int = Field(
        default=30, description="Timeout for git commands in seconds"
    )
    api_request_timeout: int = Field(
        default=30, description="Timeout for API requests in seconds"
    )
    
    @field_validator("git_command_timeout", "api_request_timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        """Validate timeout value."""
        if not isinstance(v, int):
            raise ValueError("Timeout must be an integer")
        
        if v < 1:
            raise ValueError("Timeout must be at least 1 second")
        
        if v > 3600:  # 1 hour max
            raise ValueError("Timeout cannot exceed 3600 seconds (1 hour)")
        
        return v
```

#### 4. Retry Configuration Validation (Medium Priority)

```python
class RetryConfig(BaseModel):
    total: int = Field(default=3, description="Total number of retry attempts")
    backoff_factor: int = Field(
        default=1, description="Backoff factor for exponential backoff"
    )
    status_forcelist: list[int] = Field(
        default_factory=lambda: [429, 500, 502, 503, 504],
        description="HTTP status codes that should trigger a retry",
    )
    
    @field_validator("total")
    @classmethod
    def validate_total(cls, v: int) -> int:
        """Validate retry total."""
        if not isinstance(v, int):
            raise ValueError("Total must be an integer")
        if v < 0:
            raise ValueError("Total cannot be negative")
        if v > 10:
            raise ValueError("Total cannot exceed 10 retries")
        return v
    
    @field_validator("backoff_factor")
    @classmethod
    def validate_backoff_factor(cls, v: int) -> int:
        """Validate backoff factor."""
        if not isinstance(v, int):
            raise ValueError("Backoff factor must be an integer")
        if v < 0:
            raise ValueError("Backoff factor cannot be negative")
        if v > 10:
            raise ValueError("Backoff factor cannot exceed 10")
        return v
    
    @field_validator("status_forcelist")
    @classmethod
    def validate_status_codes(cls, v: list[int]) -> list[int]:
        """Validate HTTP status codes."""
        if not isinstance(v, list):
            raise ValueError("Status forcelist must be a list")
        
        valid_status_codes = set(range(100, 600))  # Valid HTTP status code range
        for code in v:
            if not isinstance(code, int):
                raise ValueError(f"Status code must be an integer: {code}")
            if code not in valid_status_codes:
                raise ValueError(f"Invalid HTTP status code: {code}")
        
        return sorted(set(v))  # Remove duplicates and sort
```

#### 5. Enum and Directory Validation (Low Priority)

```python
from typing import Literal

class DocsRepoConfig(ServerConfig):
    repo_mode: Literal["same", "external"] = Field(
        default="same",
        description="Repository mode: 'same' or 'external'"
    )
    
    docs_directory: str = Field(
        default="docs", description="Directory name for documentation files"
    )
    
    @field_validator("docs_directory")
    @classmethod
    def validate_docs_directory(cls, v: str) -> str:
        """Validate docs directory name."""
        if not isinstance(v, str):
            raise ValueError("Directory name must be a string")
        
        v = v.strip()
        if not v:
            raise ValueError("Directory name cannot be empty")
        
        # Check for dangerous patterns
        if any(char in v for char in ["/", "\\", "..", "\x00", "\n", "\r", "\t"]):
            raise ValueError("Directory name contains invalid characters")
        
        # Length limit
        if len(v) > 255:
            raise ValueError("Directory name too long (max 255 characters)")
        
        return v
    
    @field_validator("doc_type_directories")
    @classmethod
    def validate_doc_type_directories(cls, v: dict[str, str]) -> dict[str, str]:
        """Validate doc type directories mapping."""
        if not isinstance(v, dict):
            raise ValueError("doc_type_directories must be a dictionary")
        
        from src.shared.security import SecurityValidator
        allowed_types = SecurityValidator.ALLOWED_DOC_TYPES
        
        for doc_type, dir_name in v.items():
            # Validate key is an allowed doc type
            if doc_type not in allowed_types:
                raise ValueError(f"Invalid doc type: {doc_type}. Allowed: {allowed_types}")
            
            # Validate directory name
            if not isinstance(dir_name, str):
                raise ValueError(f"Directory name must be a string for {doc_type}")
            
            dir_name = dir_name.strip()
            if not dir_name:
                raise ValueError(f"Directory name cannot be empty for {doc_type}")
            
            # Check for dangerous patterns
            if any(char in dir_name for char in ["/", "\\", "..", "\x00", "\n", "\r", "\t"]):
                raise ValueError(f"Directory name contains invalid characters for {doc_type}")
            
            if len(dir_name) > 255:
                raise ValueError(f"Directory name too long for {doc_type}")
        
        return v
```

---

## Option 1: Use Pydantic Validators (Recommended)

**Pros:**
- Already a dependency (no new packages)
- Type-safe validation
- Integrates with existing Pydantic models
- Excellent error messages
- Supports custom validators

**Cons:**
- Requires restructuring validation to work with Pydantic models
- Some validations might need to be at model level rather than function level

### Implementation Approach

#### A. Create Pydantic Models for Inputs

```python
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic import StringConstraints
from typing import Annotated
from pathlib import Path

# Constrained string types
FeatureID = Annotated[
    str,
    StringConstraints(
        pattern=r"^[a-zA-Z0-9_\-/]{1,200}$",
        min_length=1,
        max_length=200,
    ),
]

BranchName = Annotated[
    str,
    StringConstraints(
        pattern=r"^[a-zA-Z0-9_\-/]{1,255}$",
        min_length=1,
        max_length=255,
    ),
]

ProductName = Annotated[
    str,
    StringConstraints(
        pattern=r"^[a-zA-Z0-9_\-]{1,100}$",
        min_length=1,
        max_length=100,
    ),
]

CommitHash = Annotated[
    str,
    StringConstraints(
        pattern=r"^[a-fA-F0-9]{7,40}$",
        min_length=7,
        max_length=40,
    ),
]

class FeatureIDInput(BaseModel):
    """Validated feature ID input."""
    
    feature_id: FeatureID
    
    @field_validator("feature_id")
    @classmethod
    def validate_feature_id(cls, v: str) -> str:
        v = v.strip()
        # Check for dangerous patterns
        dangerous = ["..", "\x00", "\n", "\r", "\t"]
        for pattern in dangerous:
            if pattern in v:
                raise ValueError(f"feature_id cannot contain: {pattern!r}")
        return v

class BranchNameInput(BaseModel):
    """Validated branch name input."""
    
    branch_name: BranchName
    
    @field_validator("branch_name")
    @classmethod
    def validate_branch_name(cls, v: str) -> str:
        v = v.strip()
        if v.startswith(".") or v.endswith("."):
            raise ValueError("Branch name cannot start or end with a dot")
        if v.endswith(".lock"):
            raise ValueError("Branch name cannot end with .lock")
        if ".." in v or "@{" in v:
            raise ValueError("Branch name cannot contain '..' or '@{'")
        return v

class PathInput(BaseModel):
    """Validated path input."""
    
    path: str
    workspace_root: Path
    
    @field_validator("path")
    @classmethod
    def validate_path_string(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("path cannot be empty")
        # Check for dangerous characters
        dangerous = ["\x00", "\n", "\r"]
        for char in dangerous:
            if char in v:
                raise ValueError(f"path cannot contain: {char!r}")
        return v
    
    @model_validator(mode="after")
    def validate_path_within_workspace(self) -> "PathInput":
        file_path = Path(self.path)
        
        # Resolve path
        if not file_path.is_absolute():
            file_path = self.workspace_root / file_path
        else:
            try:
                file_path.resolve().relative_to(self.workspace_root.resolve())
            except ValueError:
                raise ValueError(f"Path outside workspace: {self.path}")
        
        # Ensure resolved path is within workspace
        resolved_path = file_path.resolve()
        try:
            resolved_path.relative_to(self.workspace_root.resolve())
        except ValueError:
            raise ValueError(f"Resolved path outside workspace: {self.path}")
        
        # Check for path traversal
        relative_path = resolved_path.relative_to(self.workspace_root.resolve())
        if ".." in str(relative_path):
            raise ValueError("Path traversal is not allowed")
        
        return self
```

#### B. Use Literal Types for Enums

```python
from typing import Literal

DocType = Literal[
    "concept",
    "task",
    "api_reference",
    "release_notes",
    "feature_overview",
    "configuration_reference",
]

class DocTypeInput(BaseModel):
    """Validated document type input."""
    
    doc_type: DocType
    
    @field_validator("doc_type", mode="before")
    @classmethod
    def normalize_doc_type(cls, v: str) -> str:
        return v.strip().lower()
```

#### C. Usage in Server Code

```python
# Instead of:
feature_id = SecurityValidator.validate_feature_id(feature_id)

# Use:
try:
    validated = FeatureIDInput(feature_id=feature_id)
    feature_id = validated.feature_id
except ValidationError as e:
    raise SecurityError(str(e))
```

---

## Option 2: Use Pydantic with Custom Validators (Hybrid)

Keep some custom logic but use Pydantic's validation framework.

**Pros:**
- Leverages Pydantic's error handling
- Can keep some custom validation logic
- Better error messages

**Cons:**
- Still requires some custom code
- Less standard than pure Pydantic

### Implementation

```python
from pydantic import BaseModel, field_validator, ValidationError
from pydantic_core import core_schema

class SecurityValidator:
    """Validates inputs using Pydantic under the hood."""
    
    @staticmethod
    def validate_feature_id(feature_id: str) -> str:
        class FeatureIDModel(BaseModel):
            value: str = Field(
                pattern=r"^[a-zA-Z0-9_\-/]{1,200}$",
                min_length=1,
                max_length=200,
            )
            
            @field_validator("value")
            @classmethod
            def check_dangerous_patterns(cls, v: str) -> str:
                v = v.strip()
                dangerous = ["..", "\x00", "\n", "\r", "\t"]
                for pattern in dangerous:
                    if pattern in v:
                        raise ValueError(f"Cannot contain: {pattern!r}")
                return v
        
        try:
            model = FeatureIDModel(value=feature_id)
            return model.value
        except ValidationError as e:
            raise SecurityError(str(e.errors()[0]["msg"]))
```

---

## Option 3: Use `validators` Library

**Pros:**
- Standard library of common validators
- Well-tested
- Simple API

**Cons:**
- Adds new dependency
- May not cover all our needs
- Less type-safe than Pydantic

### Installation
```bash
pip install validators
```

### Implementation

```python
import validators
from validators import url, email  # etc.

# For our use case, validators library doesn't have:
# - Feature ID validation
# - Branch name validation
# - Path validation
# So we'd still need custom logic
```

**Verdict:** Not suitable for our needs - doesn't cover our validation requirements.

---

## Option 4: Use `python-validators` Library

**Pros:**
- More comprehensive than `validators`
- Supports custom validators

**Cons:**
- Adds new dependency
- Less integrated with Pydantic
- Still may need custom logic

### Installation
```bash
pip install python-validators
```

**Verdict:** Not recommended - Pydantic already provides better validation.

---

## Option 5: Use Standard Library + Pydantic (Recommended Hybrid)

Combine standard library features with Pydantic validators.

**Pros:**
- No new dependencies
- Uses best of both worlds
- Leverages pathlib for path validation
- Uses Pydantic for string validation

**Cons:**
- Still requires some custom logic for complex validations

### Implementation

```python
from pydantic import BaseModel, Field, field_validator
from pydantic import StringConstraints
from typing import Annotated, Literal
from pathlib import Path
import re

# Type aliases with constraints
FeatureID = Annotated[
    str,
    StringConstraints(
        pattern=r"^[a-zA-Z0-9_\-/]{1,200}$",
        min_length=1,
        max_length=200,
    ),
]

DocType = Literal[
    "concept", "task", "api_reference", 
    "release_notes", "feature_overview", 
    "configuration_reference"
]

class SecurityValidator:
    """Validates inputs using Pydantic and standard library."""
    
    @staticmethod
    def validate_feature_id(feature_id: str) -> str:
        class Model(BaseModel):
            value: FeatureID
            
            @field_validator("value")
            @classmethod
            def check_dangerous(cls, v: str) -> str:
                v = v.strip()
                if any(p in v for p in ["..", "\x00", "\n", "\r", "\t"]):
                    raise ValueError("Contains dangerous characters")
                return v
        
        return Model(value=feature_id).value
    
    @staticmethod
    def validate_path(path: str, workspace_root: Path) -> Path:
        # Use pathlib for path validation
        file_path = Path(path)
        
        if not file_path.is_absolute():
            file_path = workspace_root / file_path
        
        resolved = file_path.resolve()
        try:
            resolved.relative_to(workspace_root.resolve())
        except ValueError:
            raise SecurityError("Path outside workspace")
        
        if ".." in str(resolved.relative_to(workspace_root.resolve())):
            raise SecurityError("Path traversal not allowed")
        
        return resolved
```

---

## Option 6: Use Pydantic Models in Server Endpoints

Create Pydantic models for all tool inputs and validate at the API boundary.

**Pros:**
- Validation happens automatically
- Type-safe throughout
- Better error messages
- Less manual validation code

**Cons:**
- Requires refactoring server endpoints
- More upfront work

### Implementation

```python
# In server.py
from pydantic import BaseModel, Field, field_validator
from typing import Literal

class GetFeatureMetadataInput(BaseModel):
    """Input for get_feature_metadata tool."""
    
    feature_id: Annotated[
        str,
        Field(
            pattern=r"^[a-zA-Z0-9_\-/]{1,200}$",
            min_length=1,
            max_length=200,
        ),
    ]
    repo_path: str | None = None
    
    @field_validator("feature_id")
    @classmethod
    def validate_feature_id(cls, v: str) -> str:
        v = v.strip()
        if any(p in v for p in ["..", "\x00", "\n", "\r", "\t"]):
            raise ValueError("Contains dangerous characters")
        return v

@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any] | None = None):
    if name == "get_feature_metadata":
        # Pydantic validates automatically
        input_model = GetFeatureMetadataInput(**arguments)
        # Use input_model.feature_id (already validated)
```

---

## Recommendation: Option 1 + Option 6 (Pydantic Models)

**Best Approach:**
1. Create Pydantic models for all tool inputs (Option 6)
2. Use Pydantic's `StringConstraints` and `Literal` types (Option 1)
3. Keep minimal custom validators only for complex cases
4. Use `pathlib` for path validation (already standard library)

**Benefits:**
- ✅ No new dependencies
- ✅ Type-safe validation
- ✅ Automatic validation at API boundary
- ✅ Better error messages
- ✅ Less custom code
- ✅ Standard approach

**Migration Path:**

**Phase 1: Immediate (Security Critical)**
1. ✅ Add Pydantic field validators to `DocsRepoConfig` and `RetryConfig`
2. ✅ Validate new configurable values (URLs, timeouts, retry config, etc.)
3. ✅ Use `Literal` type for `repo_mode` enum
4. ✅ Keep `SecurityValidator` for user inputs (for now)

**Phase 2: Next (User Input Validation)**
5. Create Pydantic input models for each tool
6. Replace `SecurityValidator` calls with Pydantic model instantiation
7. Keep `SecurityError` for backward compatibility (wrap Pydantic ValidationError)

**Phase 3: Future (Cleanup)**
8. Gradually remove `SecurityValidator` class
9. Update all tests to use Pydantic models
10. Update documentation

---

## Example: Complete Refactored Validation

```python
# src/shared/validation.py
from pydantic import BaseModel, Field, field_validator, ValidationError
from pydantic import StringConstraints
from typing import Annotated, Literal
from pathlib import Path

# Type aliases
FeatureID = Annotated[
    str,
    StringConstraints(
        pattern=r"^[a-zA-Z0-9_\-/]{1,200}$",
        min_length=1,
        max_length=200,
    ),
]

BranchName = Annotated[
    str,
    StringConstraints(
        pattern=r"^[a-zA-Z0-9_\-/]{1,255}$",
        min_length=1,
        max_length=255,
    ),
]

CommitHash = Annotated[
    str,
    StringConstraints(
        pattern=r"^[a-fA-F0-9]{7,40}$",
        min_length=7,
        max_length=40,
    ),
]

DocType = Literal[
    "concept",
    "task",
    "api_reference",
    "release_notes",
    "feature_overview",
    "configuration_reference",
]

# Input models
class FeatureIDInput(BaseModel):
    value: FeatureID
    
    @field_validator("value")
    @classmethod
    def check_dangerous(cls, v: str) -> str:
        v = v.strip()
        dangerous = ["..", "\x00", "\n", "\r", "\t"]
        for pattern in dangerous:
            if pattern in v:
                raise ValueError(f"Cannot contain: {pattern!r}")
        return v

class BranchNameInput(BaseModel):
    value: BranchName
    
    @field_validator("value")
    @classmethod
    def check_git_rules(cls, v: str) -> str:
        v = v.strip()
        if v.startswith(".") or v.endswith("."):
            raise ValueError("Cannot start/end with dot")
        if v.endswith(".lock"):
            raise ValueError("Cannot end with .lock")
        if ".." in v or "@{" in v:
            raise ValueError("Cannot contain '..' or '@{'")
        return v

class PathInput(BaseModel):
    path: str
    workspace_root: Path
    
    @field_validator("path")
    @classmethod
    def validate_path_string(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Cannot be empty")
        if any(c in v for c in ["\x00", "\n", "\r"]):
            raise ValueError("Contains dangerous characters")
        return v
    
    @field_validator("workspace_root", mode="before")
    @classmethod
    def convert_to_path(cls, v: Path | str) -> Path:
        return Path(v)
    
    def get_validated_path(self) -> Path:
        """Return validated Path object."""
        file_path = Path(self.path)
        
        if not file_path.is_absolute():
            file_path = self.workspace_root / file_path
        
        resolved = file_path.resolve()
        try:
            resolved.relative_to(self.workspace_root.resolve())
        except ValueError:
            raise ValueError(f"Path outside workspace: {self.path}")
        
        if ".." in str(resolved.relative_to(self.workspace_root.resolve())):
            raise ValueError("Path traversal not allowed")
        
        return resolved

# Wrapper functions for backward compatibility
def validate_feature_id(value: str) -> str:
    """Validate feature ID using Pydantic."""
    try:
        return FeatureIDInput(value=value).value
    except ValidationError as e:
        from src.shared.errors import SecurityError
        raise SecurityError(str(e.errors()[0]["msg"]))

def validate_branch_name(value: str) -> str:
    """Validate branch name using Pydantic."""
    try:
        return BranchNameInput(value=value).value
    except ValidationError as e:
        from src.shared.errors import SecurityError
        raise SecurityError(str(e.errors()[0]["msg"]))

def validate_path(path: str, workspace_root: Path) -> Path:
    """Validate path using Pydantic."""
    try:
        model = PathInput(path=path, workspace_root=workspace_root)
        return model.get_validated_path()
    except ValidationError as e:
        from src.shared.errors import SecurityError
        raise SecurityError(str(e.errors()[0]["msg"]))
```

---

## Migration Checklist

### Phase 1: Config Validation (Immediate - Security Critical)
- [ ] Add URL validation for `github_api_base_url` and `gitlab_api_base_url`
- [ ] Add hostname validation for `github_host` and `gitlab_host`
- [ ] Add timeout range validation for `git_command_timeout` and `api_request_timeout`
- [ ] Add retry config validation (`total`, `backoff_factor`, `status_forcelist`)
- [ ] Add enum validation for `repo_mode` using `Literal` type
- [ ] Add directory name validation for `docs_directory`
- [ ] Add validation for `doc_type_directories` mapping
- [ ] Test config validation with edge cases
- [ ] Update `CONFIGURATION.md` with validation rules

### Phase 2: User Input Validation (Next)
- [ ] Create Pydantic input models for all tool inputs
- [ ] Replace `SecurityValidator.validate_feature_id()` calls
- [ ] Replace `SecurityValidator.validate_branch_name()` calls
- [ ] Replace `SecurityValidator.validate_path()` calls
- [ ] Replace `SecurityValidator.validate_doc_type()` with `Literal` type
- [ ] Replace `SecurityValidator.sanitize_git_pattern()` with Pydantic validator
- [ ] Replace `SecurityValidator.sanitize_commit_hash()` with Pydantic validator
- [ ] Update tests to use Pydantic models

### Phase 3: Cleanup (Future)
- [ ] Remove `SecurityValidator` class
- [ ] Update all documentation
- [ ] Review and optimize validation performance

---

## Conclusion

**Recommended:** Use Pydantic 2.0's validation features (Option 1 + Option 6)

- Already a dependency
- Type-safe and well-tested
- Better error messages
- Standard approach
- Less custom code to maintain

This approach leverages existing dependencies and follows Python best practices for validation.

### Priority Actions

**Immediate (Security Critical):**
1. Add Pydantic field validators to config models for new fields (URLs, timeouts, retry config)
2. This prevents SSRF and DoS vulnerabilities from misconfigured values
3. See "Immediate Priority: Validate Configuration Fields" section above

**Next:**
4. Migrate user input validation to Pydantic models
5. Replace `SecurityValidator` with Pydantic-based validation

**See Also:**
- Phase 1 (config validation) has been completed - all configuration fields are now validated
