# AGENTS.md

> **Example: monorepo with multiple services.**
> Fictional monorepo — `helix`, a developer platform with a Rust API gateway, a Go worker service, and a Python data pipeline. All data is fabricated for illustration.
> The structure and level of detail here represent the target quality for any monorepo output.

---

## 1. Overview

helix is a developer platform monorepo containing three services: a Rust HTTP API gateway (`gateway/`), a Go background worker (`worker/`), and a Python data pipeline (`pipeline/`). The gateway handles authentication and request routing; the worker processes job queues from Redis; the pipeline ingests telemetry events, transforms them, and writes to a ClickHouse cluster. Services communicate via a shared Protobuf schema (`proto/`). Each service is independently buildable and deployable. No service imports from another at the source level.

---

## 2. Repository Structure

```
helix/
  gateway/            # Rust HTTP API gateway
    src/
      main.rs
      router.rs
      handlers/
        auth.rs
        jobs.rs
        health.rs
      middleware/
        logging.rs
        rate_limit.rs
      models.rs
      errors.rs
      config.rs
    tests/
      integration.rs
    Cargo.toml
    Cargo.lock
  worker/             # Go background worker
    cmd/
      worker/
        main.go       # entry point — flag parsing and worker bootstrap only
    internal/
      queue/
        consumer.go
        producer.go
      jobs/
        executor.go
        registry.go
      store/
        redis.go
    go.mod
    go.sum
    Makefile
  pipeline/           # Python data pipeline
    pipeline/
      __init__.py
      cli.py          # entry point — argparse dispatch only
      ingest.py
      transform.py
      sink.py
      config.py
      errors.py
      models.py
    tests/
      conftest.py
      test_ingest.py
      test_transform.py
    pyproject.toml
  proto/              # Protobuf schema shared across services
    helix.proto
    generated/
      rust/
      go/
      python/
  scripts/            # repo-wide dev scripts (not part of any service)
    gen-proto.sh
    check-versions.sh
  .github/
    workflows/
      gateway.yml
      worker.yml
      pipeline.yml
```

- Each service is its own independent unit. Add new services as new top-level directories.
- `proto/` is the only cross-service shared code. Generated client stubs live in `proto/generated/<lang>/`.
- `scripts/` contains repo-wide shell scripts only — no business logic.
- Nothing other than `proto/`, `scripts/`, `.github/`, and top-level config files belongs at the repo root.
- Never add a shared library directory that multiple services import directly. Use `proto/` for contracts; duplicate utilities if needed.

---

## 3. Service Map

**gateway** (`gateway/`) — Rust. HTTP API gateway. Handles authentication token validation, job submission, and proxies health checks to downstream services. Entry point: `gateway/src/main.rs`. Package manager: Cargo. CI: `.github/workflows/gateway.yml`.

**worker** (`worker/`) — Go. Background job processor. Consumes job queues from Redis, dispatches to registered handlers, and writes results to the shared ClickHouse sink. Entry point: `worker/cmd/worker/main.go`. Package manager: Go modules. CI: `.github/workflows/worker.yml`.

**pipeline** (`pipeline/`) — Python. Telemetry ingestion pipeline. Reads events from Kafka, applies transformation rules, and writes batches to ClickHouse. Entry point: `pipeline/pipeline/cli.py`. Package manager: pip with `pyproject.toml`. CI: `.github/workflows/pipeline.yml`.

---

## 4. Cross-Service Boundaries

Direct source-level imports between services are prohibited. `gateway/src/` must not reference `worker/` or `pipeline/` source files, and vice versa.

Shared types and contracts are defined in `proto/helix.proto`. Generated stubs in `proto/generated/<lang>/` are the only sanctioned cross-service interface. Consume generated stubs directly — do not copy or re-define their types inside a service.

No contract testing layer exists. Breaking changes to `helix.proto` must be backwards-compatible or coordinated across all three services in a single pull request. Additive changes (new fields, new message types) are safe. Renaming or removing fields requires a migration plan noted in the PR description.

---

## 5. Commands and Workflows

### gateway (Rust)

```bash
# Build
cargo build

# Build release
cargo build --release

# Test
cargo test

# Lint
cargo clippy -- -D warnings

# Format
cargo fmt
```

### worker (Go)

```bash
# Build
make build

# Test
make test

# Test with race detector
go test -race ./...

# Lint
golangci-lint run ./...

# Format
gofmt -w .
```

### pipeline (Python)

```bash
# Install (dev mode)
pip install -e ".[dev]"

# Test
pytest

# Lint
ruff check pipeline/ tests/

# Format
ruff format pipeline/ tests/

# Type check
mypy pipeline/
```

### Repo-wide

```bash
# Regenerate Protobuf stubs for all languages
./scripts/gen-proto.sh

# Check that all service versions agree on the proto revision
./scripts/check-versions.sh
```

---

## 6. Code Formatting

### Rust (gateway)

Formatted by `rustfmt`. Config in `gateway/rustfmt.toml`.

**Indentation:** 4 spaces. Never tabs.

```rust
pub async fn handle_submit(
    State(ctx): State<AppContext>,
    Json(req): Json<SubmitRequest>,
) -> Result<Json<SubmitResponse>, AppError> {
    let job_id = ctx.queue.enqueue(req.into()).await?;
    Ok(Json(SubmitResponse { job_id }))
}
```

**Line length:** 100 characters. Configured as `max_width = 100` in `rustfmt.toml`. The 95th percentile is 87.

**Blank lines — top-level:** One blank line between top-level function and `impl` block definitions.

**Blank lines — methods:** One blank line between methods inside an `impl` block.

**Blank lines — after imports:** One blank line after the `use` block before the first item.

**Trailing commas:** Present on the last element of multi-line struct expressions, `match` arms, and function parameters.

```rust
let config = Config {
    host: env::var("HOST").unwrap_or_else(|_| "0.0.0.0".into()),
    port: env::var("PORT").unwrap_or_else(|_| "8080".into()).parse()?,
    redis_url: env::var("REDIS_URL")?,
};
```

**Import block formatting:** Three groups separated by blank lines — `std`, then external crates, then `crate`. Sorted alphabetically within each group.

```rust
use std::collections::HashMap;
use std::sync::Arc;

use axum::{extract::State, Json, Router};
use tokio::sync::RwLock;

use crate::errors::AppError;
use crate::models::{Job, JobStatus};
```

---

### Go (worker)

Formatted by `gofmt`. All patterns enforced by the formatter.

**Indentation:** Tabs. One tab per level.

```go
func (e *Executor) Run(ctx context.Context, job Job) error {
	handler, ok := e.registry[job.Type]
	if !ok {
		return fmt.Errorf("no handler registered for job type %q", job.Type)
	}
	return handler(ctx, job.Payload)
}
```

**Line length:** No configured limit. Keep lines under 100 characters in practice; the 95th percentile is 79.

**Blank lines — top-level:** One blank line between top-level function definitions.

**Import block formatting:** Two groups — stdlib then external. Blank line between groups. `goimports` enforces ordering.

```go
import (
	"context"
	"fmt"
	"time"

	"github.com/redis/go-redis/v9"
	"go.uber.org/zap"
)
```

**Brace placement:** Opening brace always on the same line. No exceptions.

**Trailing commas:** Required on the last element of multi-line composite literals.

```go
rdb := redis.NewClient(&redis.Options{
	Addr:     cfg.RedisAddr,
	Password: cfg.RedisPassword,
	DB:       0,
})
```

---

### Python (pipeline)

Formatted by `ruff format`. Config in `pipeline/pyproject.toml` under `[tool.ruff.format]`.

**Indentation:** 4 spaces. Never tabs.

**Line length:** 88 characters. Configured as `line-length = 88`.

**Blank lines — top-level:** Two blank lines between top-level function and class definitions.

**Blank lines — methods:** One blank line between methods inside a class.

**Quote style:** Double quotes. Configured as `quote-style = "double"`.

```python
def transform(event: RawEvent, rules: list[TransformRule]) -> Event | None:
    for rule in rules:
        if rule.matches(event):
            return rule.apply(event)
    return None
```

**Import block formatting:** Three groups — stdlib, third-party, local. `isort` profile `"black"`.

```python
import json
import sys
from datetime import datetime
from pathlib import Path

import clickhouse_connect
import confluent_kafka

from pipeline.errors import IngestError
from pipeline.models import RawEvent
```

---

## 7. Naming Conventions

### Rust (gateway)

**Functions and methods:** `snake_case`. Handlers named `handle_<action>`: `handle_submit`, `handle_auth`, `handle_health`.

**Types and structs:** `PascalCase`: `AppContext`, `SubmitRequest`, `JobStatus`, `AppError`.

**Variables:** `snake_case`. Short names for short scopes (`req`, `ctx`, `cfg`, `err`).

**Constants:** `SCREAMING_SNAKE_CASE` for `const` and `static`.

```rust
const MAX_QUEUE_DEPTH: usize = 10_000;
static DEFAULT_TIMEOUT: Duration = Duration::from_secs(30);
```

**Error types:** In `gateway/src/errors.rs`. All implement `std::error::Error`. Named with `Error` suffix.

**File names:** `snake_case`: `router.rs`, `rate_limit.rs`, `models.rs`.

---

### Go (worker)

**Functions and methods:** `camelCase` unexported, `PascalCase` exported. Verb-first: `enqueue`, `Consume`, `registerHandler`.

**Types and interfaces:** `PascalCase`. Interfaces named after behavior, not implementation: `Consumer`, `Executor`, `Store`.

**Variables:** `camelCase`. Short idiomatic names for loop vars and errors (`j`, `err`, `ctx`).

**Constants and package-level vars:** `camelCase` unexported, `PascalCase` exported.

**File names:** `snake_case`: `consumer.go`, `executor.go`, `redis.go`.

---

### Python (pipeline)

**Functions:** `snake_case`: `ingest_batch`, `transform`, `flush_sink`.

**Classes:** `PascalCase`: `IngestionWorker`, `TransformRule`, `ClickHouseSink`.

**Variables:** `snake_case`.

**Constants:** `SCREAMING_SNAKE_CASE` at module level.

```python
DEFAULT_BATCH_SIZE: int = 500
MAX_RETRIES: int = 3
```

**Exception classes:** In `pipeline/errors.py`. All inherit from `PipelineError`. Named with `Error` suffix.

**File names:** `snake_case`, single noun: `ingest.py`, `transform.py`, `sink.py`.

---

## 8. Type Annotations

### Rust (gateway)

- All function signatures are fully typed — the compiler enforces this.
- Use `Result<T, AppError>` for all fallible functions. Do not return `Result<T, Box<dyn Error>>` in public API functions.
- Use `Option<T>` for optional values. Never represent absence with a sentinel value.

### Go (worker)

- All exported functions have explicit parameter and return types — the compiler enforces this.
- `error` is always the last return value when a function can fail.
- `context.Context` is the first parameter of all functions that perform I/O.

### Python (pipeline)

- Annotate every function signature — both parameters and return type.
- Use built-in generics: `list[str]`, `dict[str, Any]`. Never import from `typing` for these.
- Use `X | None` for optional types. Never `Optional[X]`.
- Type checker: `mypy`. Config in `pyproject.toml` under `[tool.mypy]`.

---

## 9. Imports

### Rust (gateway)

- Three groups: `std`, external crates, `crate`. Blank lines between groups. Alphabetical within groups.
- No glob imports (`use foo::*`) except in test modules where `use super::*` is acceptable.

### Go (worker)

- Two groups: stdlib, external. Blank line between groups. `goimports` manages ordering.
- No dot imports. No blank import aliases except for side-effect registration.

### Python (pipeline)

- Three groups: stdlib, third-party, local. `isort` profile `"black"`. Never `import *`.
- Local imports use the full package path: `from pipeline.models import RawEvent`.

---

## 10. Error Handling

### Rust (gateway)

- All fallible functions return `Result<T, AppError>`. `AppError` is defined in `gateway/src/errors.rs` and implements `IntoResponse` for automatic HTTP error conversion.
- Propagate with `?`. Wrap external errors with context using `.map_err(|e| AppError::upstream(e))`.
- No `.unwrap()` in non-test code. Use `?`, `unwrap_or_else`, or explicit `match`.
- No `panic!` outside of `main.rs` startup checks.

```rust
pub async fn handle_auth(
    State(ctx): State<AppContext>,
    headers: HeaderMap,
) -> Result<Json<AuthResponse>, AppError> {
    let token = headers
        .get(AUTHORIZATION)
        .ok_or(AppError::unauthorized("missing Authorization header"))?;
    let claims = ctx.validator.validate(token.to_str()?).await?;
    Ok(Json(AuthResponse { claims }))
}
```

### Go (worker)

- All errors are returned to the caller. No silent swallowing.
- Wrap errors at every layer with `fmt.Errorf("context: %w", err)`.
- `log.Fatal` is used only in `cmd/worker/main.go` for unrecoverable startup failures.

```go
func (c *Consumer) poll(ctx context.Context) (*Job, error) {
	result, err := c.rdb.BLPop(ctx, 5*time.Second, c.queueKey).Result()
	if err != nil {
		return nil, fmt.Errorf("queue poll: %w", err)
	}
	var job Job
	if err := json.Unmarshal([]byte(result[1]), &job); err != nil {
		return nil, fmt.Errorf("job unmarshal: %w", err)
	}
	return &job, nil
}
```

### Python (pipeline)

- All custom exceptions defined in `pipeline/errors.py`, inheriting from `PipelineError`.
- Public functions raise typed exceptions — never bare `Exception` or `ValueError`.
- `cli.py` catches `PipelineError` at the top level, prints to stderr, exits with code 1.
- Never use bare `except:`. Always `except Exception` at minimum.

```python
def ingest_batch(messages: list[bytes]) -> list[RawEvent]:
    events: list[RawEvent] = []
    for msg in messages:
        try:
            events.append(RawEvent.from_bytes(msg))
        except Exception as exc:
            raise IngestError(f"failed to deserialize message: {exc}") from exc
    return events
```

---

## 11. Comments and Docstrings

### Rust (gateway)

**Exported items:** `///` doc comments on all exported structs, enums, functions, and trait implementations. One sentence minimum. Full `rustdoc` format for complex items.

```rust
/// Validate a JWT token against the configured JWKS endpoint.
///
/// Returns the decoded claims on success or `AppError::unauthorized` on failure.
pub async fn validate(&self, token: &str) -> Result<Claims, AppError> {
```

**Module-level:** `//!` for module docs.

**Inline:** `//` with one space. Two spaces before when appended to a line of code.

### Go (worker)

**Exported symbols:** GoDoc comment starting with the symbol name. One sentence minimum.

```go
// Executor dispatches jobs to registered handlers based on job type.
type Executor struct {
```

**Inline:** `//` with one space.

### Python (pipeline)

**Modules:** One-sentence module docstring describing the module's role.

**Public functions:** One-line docstring. Multi-line only when the contract is non-obvious.

**Inline:** Two spaces before `#`, one space after. Non-obvious logic only.

**Never (all services):** Commented-out code. `TODO` without a linked issue. Comments restating what the code does.

---

## 12. Testing

### gateway (Rust)

Framework: `cargo test` + `tokio::test` for async.

```bash
cargo test
cargo test -- --nocapture   # show println output
```

- Integration tests in `gateway/tests/integration.rs`.
- Unit tests as `#[cfg(test)]` modules at the bottom of source files.

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_handle_health_returns_ok() {
        let response = handle_health().await;
        assert_eq!(response.status(), StatusCode::OK);
    }
}
```

### worker (Go)

Framework: standard library `testing` + `testify/assert`.

```bash
make test
go test -race ./...
```

- Test files in the same directory as source: `consumer_test.go` next to `consumer.go`.
- Test function names: `Test<Type>_<method>_<scenario>`.
- Table-driven tests for functions with multiple input cases.

```go
func TestConsumer_poll_malformedJSON(t *testing.T) {
	rdb := miniredis.RunT(t)
	rdb.Lpush("jobs", "not-json")
	c := &Consumer{rdb: newTestClient(rdb), queueKey: "jobs"}

	_, err := c.poll(context.Background())
	assert.ErrorContains(t, err, "job unmarshal")
}
```

### pipeline (Python)

Framework: `pytest`. Config in `pyproject.toml` under `[tool.pytest.ini_options]`.

```bash
pytest
pytest -x
pytest -k ingest
```

- Test files in `pipeline/tests/`, named `test_<module>.py`.
- Shared fixtures in `pipeline/tests/conftest.py`.
- No `unittest.TestCase`. All tests are plain functions.

```python
def test_transform_drops_unknown_events(sample_rules: list[TransformRule]) -> None:
    raw = RawEvent(type="unknown", payload={})
    result = transform(raw, sample_rules)
    assert result is None
```

---

## 13. Git

> **Repo-wide:**

**Commit prefixes — use exactly one per commit:**

- `feat:` — new user-visible feature
- `fix:` — bug correction
- `refactor:` — restructuring without behavior change
- `docs:` — documentation only
- `chore:` — build, CI, dependency, tooling changes
- `test:` — adds or modifies tests
- `perf:` — measurable performance improvement
- `proto:` — changes to `proto/helix.proto` or generated stubs

**Scopes:** Used to identify which service a commit affects.

```
feat(gateway): add rate limiting middleware
fix(worker): retry on Redis connection timeout
chore(pipeline): upgrade clickhouse-connect to 0.7
proto: add JobCancelRequest message
```

**Subject line:** Imperative mood. No period. Under 72 characters.

**Body:** Required for `proto:` commits — must describe backwards-compatibility impact.

**Branch naming:** `<prefix>/<service>/<short-description>` for service-specific changes, `<prefix>/<short-description>` for repo-wide changes.

```
feat/gateway/rate-limiting
fix/worker/redis-retry
chore/upgrade-proto-toolchain
```

**Merge strategy:** Squash and merge. No merge commits.

**GPG signing:** Required for all commits.

---

## 14. Dependencies and Tooling

### gateway (Rust)

- **Package manager:** Cargo. `Cargo.lock` is committed.
- **Add a dependency:** `cargo add <crate>@<version>`.
- **Linter:** `cargo clippy`. Configured with `-D warnings` in CI.
- **Formatter:** `rustfmt`. Config in `gateway/rustfmt.toml`.
- **Minimum Rust:** 1.75 (declared in `gateway/Cargo.toml` under `[workspace.package]`).

### worker (Go)

- **Package manager:** Go modules. `go.sum` is committed.
- **Add a dependency:** `go get <module>@<version>` then `go mod tidy`.
- **Linter:** `golangci-lint`. Config in `worker/.golangci.yml`.
- **Formatter:** `gofmt` via `goimports`.
- **Minimum Go:** 1.22 (declared in `worker/go.mod`).

### pipeline (Python)

- **Package manager:** pip with `pyproject.toml`.
- **Install:** `pip install -e ".[dev]"`.
- **Add a dependency:** Add to `[project.dependencies]` in `pipeline/pyproject.toml`.
- **Linter/formatter:** `ruff`. Config in `pipeline/pyproject.toml`.
- **Type checker:** `mypy`. Config in `pipeline/pyproject.toml`.
- **Minimum Python:** 3.11.

### Repo-wide

- **CI:** GitHub Actions. One workflow per service in `.github/workflows/`.
- **Proto generation:** `buf`. Config in `proto/buf.yaml`. Regenerate with `./scripts/gen-proto.sh`.

---

## 15. Red Lines

**Formatting violations:**

- Never use spaces for indentation in Go or Rust. Both use tabs (Go) and 4-space indentation (Rust) enforced by their respective formatters.
- Never use single quotes in Python. All string literals use double quotes — enforced by `ruff format`.

**Architectural violations:**

- Never import source code from one service into another. `gateway/src/` must never reference `worker/` or `pipeline/` source trees, and vice versa. Use generated stubs from `proto/generated/` for shared contracts.
- Never modify `proto/helix.proto` without updating all three generated stub directories in the same commit. Use `./scripts/gen-proto.sh`.
- Never add business logic to `cmd/worker/main.go` or `pipeline/pipeline/cli.py`. Those files contain only entry point bootstrap.
- Never create a shared library directory that two services import directly. Duplicate utilities within each service.

**Style violations:**

- Never use `Optional[X]` in Python. Use `X | None` exclusively.
- Never use `.unwrap()` in non-test Rust code. Use `?`, `unwrap_or_else`, or explicit `match`.
- Never define exception classes outside `errors.py` in the Python pipeline.
- Never define sentinel error values outside `errors.rs` in the Rust gateway.

**Testing violations:**

- Never write tests that make real network calls. All external service interactions must use fakes or in-process test doubles.
- Never use `unittest.TestCase` in Python tests. All tests are plain `pytest` functions.

**Git violations:**

- Never commit without GPG signing. CI rejects unsigned commits.
- Never commit a `proto:` change without verifying all three generated stub directories are regenerated.
- Never commit without a conventional prefix — including a scope when the change is service-specific.
- Never commit commented-out code.
