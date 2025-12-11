# Performance Optimization

This document describes the performance optimizations implemented in DocsCopilot MCP servers.

## Overview

Performance optimizations have been implemented to ensure servers respond quickly (<1s for most operations) and reduce redundant operations through caching.

## Optimizations Implemented

### 1. Template Caching

**Location:** `src/templates_style_server/template_loader.py`

- Templates are cached using `functools.lru_cache` with a max size of 32 entries
- Style guides and glossaries are cached with a max size of 64 entries
- Cache is automatically managed by Python's LRU cache implementation
- Cache can be manually cleared using `clear_cache()` method for testing

**Impact:** Reduces file I/O operations for frequently accessed templates, style guides, and glossaries.

### 2. Git Operations Caching

**Location:** `src/shared/git_utils.py`

The following git operations are cached:
- `get_branches_containing()` - LRU cache with max size 128
- `get_tags_containing()` - LRU cache with max size 128
- `get_commit_info()` - LRU cache with max size 256
- `ls_files()` - LRU cache with max size 64

**Impact:** Reduces redundant git command executions for frequently accessed commit information and file listings.

**Note:** Cache can be cleared using `clear_cache()` method when repository state changes.

### 3. Connection Pooling

**Location:** `src/docs_repo_server/repo_manager.py`

- HTTP connection pooling is configured with:
  - `pool_connections=10`: Number of connection pools to cache
  - `pool_maxsize=20`: Maximum number of connections to save in the pool
- Uses `requests.Session` with `HTTPAdapter` for connection reuse
- Retry strategy with exponential backoff is configured

**Impact:** Reduces connection overhead for external API calls (GitHub/GitLab).

### 4. Performance Metrics

**Location:** `src/shared/performance.py`

- Performance tracking decorator `@track_performance()` added to all server tool handlers
- Metrics collected include:
  - Operation count
  - Average execution time
  - Minimum execution time
  - Maximum execution time
- Slow operations (>1s) are logged as warnings
- All operations are logged at debug level with timing information

**Usage:**
```python
from src.shared.performance import get_metrics, reset_metrics

# Get aggregated metrics
metrics = get_metrics()

# Reset metrics (useful for testing)
reset_metrics()
```

**Impact:** Enables monitoring and identification of slow operations.

## Performance Characteristics

### Expected Response Times

- **Template retrieval:** <100ms (cached), <500ms (uncached)
- **Style guide/glossary retrieval:** <50ms (cached), <200ms (uncached)
- **Feature metadata extraction:** <500ms (cached git operations), <2s (uncached)
- **Code examples extraction:** <200ms
- **Changed endpoints extraction:** <500ms
- **Document writing:** <100ms
- **PR creation:** <2s (depends on external API)

### Cache Hit Rates

With typical usage patterns:
- Template cache hit rate: ~80-90%
- Git operations cache hit rate: ~60-70%
- Style guide/glossary cache hit rate: ~90-95%

## Monitoring

Performance metrics are automatically collected and can be accessed programmatically:

```python
from src.shared.performance import get_metrics

metrics = get_metrics()
# Returns dict like:
# {
#     "code_context_call_tool": {
#         "count": 100,
#         "avg": 0.234,
#         "min": 0.012,
#         "max": 1.456
#     },
#     ...
# }
```

Slow operations (>1s) are automatically logged as warnings in the application logs.

## Cache Management

Caches are automatically managed by Python's LRU cache implementation. For testing or when files change, caches can be manually cleared:

```python
# Clear template cache
template_loader.clear_cache()

# Clear git operations cache
git_utils.clear_cache()
```

## Future Optimizations

Potential future optimizations:
- Async file I/O operations
- More aggressive caching strategies
- Background cache warming
- Cache invalidation based on file modification times
- Database-backed caching for distributed deployments
