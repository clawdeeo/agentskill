# AGENTS.md

> **Example: single-language repo.**
> Fictional Go HTTP service — `harbor`. All data is fabricated for illustration.
> The structure and level of detail here represent the target quality for any single-language output.

---

## 1. Overview

harbor is a Go HTTP service that proxies requests to upstream container registries, enforces pull-through caching via a local BoltDB store, and exposes a REST API for cache inspection and invalidation. The codebase is structured as a single Go module with no sub-packages — all logic lives in package `main`. Error handling is explicit throughout: every function that can fail returns an `error`; `log.Fatal` is reserved for startup failures only.

---

## 2. Repository Structure

```
harbor/
  main.go           # entry point — flag parsing and server bootstrap only
  server.go         # HTTP handler registration and middleware wiring
  proxy.go          # upstream request forwarding and response streaming
  cache.go          # BoltDB read/write and TTL eviction
  registry.go       # upstream registry client and auth token exchange
  config.go         # config struct and environment variable loading
  errors.go         # sentinel error values
  middleware.go     # request logging, recovery, and auth middleware
  go.mod
  go.sum
  Makefile
  .github/
    workflows/
      ci.yml
  testdata/
    responses/      # canned upstream responses for handler tests
```

- New functionality goes in a new `.go` file at the repo root — not in a subdirectory. There are no sub-packages.
- `main.go` contains only `main()`. No business logic belongs there.
- `errors.go` is the canonical home for all sentinel errors. Do not define `var Err...` values anywhere else.
- No `internal/` or `pkg/` directories. The single-package structure is intentional.

---

## 5. Commands and Workflows

```bash
# Build
make build

# Run locally
./harbor --port 8080 --upstream https://registry-1.docker.io

# Test
make test

# Test with race detector
go test -race ./...

# Lint
golangci-lint run

# Format (enforced by CI)
gofmt -w .
```

---

## 6. Code Formatting

Formatted by `gofmt`. Config lives in `.golangci.yml`. All patterns below are enforced by the formatter unless noted otherwise.

### Go

**Indentation:** Tabs. One tab per level. Never spaces.

```go
func (c *Cache) Get(key string) ([]byte, error) {
	err := c.db.View(func(tx *bolt.Tx) error {
		b := tx.Bucket(cacheBucket)
		if b == nil {
			return ErrBucketMissing
		}
		val = b.Get([]byte(key))
		return nil
	})
	return val, err
}
```

**Line length:** No hard limit configured. Keep lines under 100 characters in practice; the 95th percentile is 84. Wrap function call chains at the dot, not in the middle of an argument list.

```go
resp, err := c.client.
	Do(req.WithContext(ctx))
```

**Blank lines — top-level:** One blank line between top-level function definitions. Two blank lines before a type declaration that opens a new conceptual group.

```go
func (p *Proxy) forward(r *http.Request) (*http.Response, error) {
	...
}

func (p *Proxy) rewriteURL(upstream string, r *http.Request) (*url.URL, error) {
	...
}
```

**Blank lines — methods:** One blank line between methods on the same type.

**Blank lines — after imports:** One blank line after the import block before the first declaration.

**Blank lines — end of file:** Every file ends with exactly one trailing newline.

**Trailing whitespace:** Never present.

**Quote style:** Double quotes for all string literals. Backtick strings only for raw literals containing double quotes or backslashes.

```go
const defaultUpstream = "https://registry-1.docker.io"
const tokenEndpoint = `https://auth.docker.io/token?service=registry.docker.io&scope=repository:%s:pull`
```

**Brace placement:** Opening brace always on the same line as the statement. No Allman style.

```go
if err != nil {
	return nil, fmt.Errorf("cache lookup failed: %w", err)
}
```

**Import block formatting:** Three groups separated by blank lines — stdlib, then external, then none (this repo has no internal packages). Sorted alphabetically within each group. `goimports` enforces this.

```go
import (
	"context"
	"errors"
	"fmt"
	"net/http"
	"time"

	"github.com/boltdb/bolt"
	"go.uber.org/zap"
)
```

**Spacing — operators:** Standard Go: space on both sides of binary operators, no space inside parentheses or brackets.

**Trailing commas:** Required on the last element of multi-line struct literals and function call argument lists.

```go
srv := &http.Server{
	Addr:         cfg.Addr,
	Handler:      mux,
	ReadTimeout:  10 * time.Second,
	WriteTimeout: 30 * time.Second,
}
```

---

## 7. Naming Conventions

### Go

**Functions and methods:** `camelCase` for unexported, `PascalCase` for exported. Named after their primary action and noun: `parseConfig`, `ServeHTTP`, `forwardRequest`, `evictExpired`.

```go
func (p *Proxy) forwardRequest(ctx context.Context, r *http.Request) (*http.Response, error)
func (c *Cache) Invalidate(key string) error
func parseConfig() (*Config, error)
```

**Types and structs:** `PascalCase`. Named after the domain concept they represent.

```go
type Proxy struct { ... }
type Cache struct { ... }
type Config struct { ... }
type RegistryClient struct { ... }
```

**Variables:** `camelCase`. Short names for short scopes (`r`, `w`, `err`, `ctx`, `cfg`). Full descriptive names for package-level variables.

```go
var defaultTTL = 24 * time.Hour
var cacheBucket = []byte("blobs")
```

**Constants:** `camelCase` for unexported, `PascalCase` for exported. No `SCREAMING_SNAKE_CASE` anywhere in this codebase.

```go
const defaultPort = 8080
const MaxRetries = 3
```

**Sentinel errors:** `Err` prefix, `PascalCase`.

```go
var ErrBucketMissing = errors.New("cache bucket not initialized")
var ErrUpstreamTimeout = errors.New("upstream registry did not respond in time")
```

**File names:** `snake_case`, matching the primary concern of the file: `proxy.go`, `cache.go`, `registry.go`.

**Test files:** `<source>_test.go` in the same directory.

---

## 8. Type Annotations

### Go

- Every exported function has explicit parameter types and return types. This is enforced by the compiler.
- Error is always the last return value when a function can fail.
- Use `context.Context` as the first parameter of any function that performs I/O or can be cancelled.

```go
func (r *RegistryClient) FetchToken(ctx context.Context, repo string) (string, error)
func (c *Cache) Set(key string, val []byte, ttl time.Duration) error
```

- No type aliases except for domain-specific clarity.
- Interfaces are defined where they are consumed, not where the type is defined.

```go
// In proxy.go — defined where used
type tokenFetcher interface {
	FetchToken(ctx context.Context, repo string) (string, error)
}
```

---

## 9. Imports

### Go

- Three groups: stdlib, external, internal. One blank line between each group.
- No dot imports (`import . "pkg"`). No blank import aliases except for side-effect registration (e.g. `_ "net/http/pprof"`).
- `goimports` manages ordering automatically — do not sort by hand.

```go
import (
	"context"
	"fmt"
	"net/http"
	"time"

	"github.com/boltdb/bolt"
	"go.uber.org/zap"

	"github.com/example/harbor/testutil"
)
```

---

## 10. Error Handling

### Go

- Every error is returned to the caller. No silent swallowing.
- Wrap errors at every layer with `fmt.Errorf("context: %w", err)`. The outermost caller decides whether to log or surface.
- `log.Fatal` is used only in `main()` for unrecoverable startup failures. Everywhere else, return the error.
- Sentinel errors in `errors.go` are used for programmatic matching via `errors.Is`.

```go
func (c *Cache) Get(key string) ([]byte, error) {
	var val []byte
	err := c.db.View(func(tx *bolt.Tx) error {
		b := tx.Bucket(cacheBucket)
		if b == nil {
			return ErrBucketMissing
		}
		val = b.Get([]byte(key))
		return nil
	})
	if err != nil {
		return nil, fmt.Errorf("cache get %q: %w", key, err)
	}
	return val, nil
}
```

- No `panic` anywhere except inside `init()` for programmer errors that indicate a broken build (missing required env vars that are validated at compile time). These panics have a comment explaining why.

---

## 11. Comments and Docstrings

### Go

**Exported symbols:** Every exported type, function, method, and constant has a GoDoc comment. One sentence minimum. Starts with the symbol name.

```go
// Proxy forwards incoming requests to the upstream registry and writes
// responses to the local cache for subsequent retrieval.
type Proxy struct {
	...
}

// ServeHTTP implements http.Handler. It resolves the upstream URL, checks
// the local cache, and forwards the request if no valid cached entry exists.
func (p *Proxy) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	...
}
```

**Unexported functions:** No doc comment required unless the logic is non-obvious. When present, one line only.

```go
// rewriteURL constructs the upstream URL from the incoming request path and the configured base.
func (p *Proxy) rewriteURL(base string, r *http.Request) (*url.URL, error) {
```

**Inline comments:** Two spaces before `//`, one space after. Used only for non-obvious logic.

```go
ttl := r.Header.Get("Cache-Control")  // may be empty; default applied in cache.Set
```

**Never:** commented-out code, `TODO` without a linked issue, comments that restate what the code does.

---

## 12. Testing

Framework: standard library `testing` package. No third-party test framework.

```bash
# Run all tests
make test

# Run with race detector
go test -race ./...

# Run a specific test
go test -run TestProxy_forwardRequest ./...
```

- Test files live in the same directory as source files: `cache_test.go` next to `cache.go`.
- Test function names: `Test<Type>_<method>` or `Test<function>_<scenario>`.
- Table-driven tests are the default for any function with more than two distinct input cases.
- Canned upstream responses live in `testdata/responses/` and are loaded with `os.ReadFile`.

```go
func TestCache_Get_missingBucket(t *testing.T) {
	db := openTestDB(t)
	c := &Cache{db: db}

	_, err := c.Get("sha256:abc123")
	if !errors.Is(err, ErrBucketMissing) {
		t.Fatalf("expected ErrBucketMissing, got %v", err)
	}
}
```

---

## 13. Git

> **Repo-wide:**

**Commit prefixes — use exactly one per commit:**

- `feat:` — adds new user-visible behavior
- `fix:` — corrects a bug
- `refactor:` — restructures code without changing behavior
- `docs:` — documentation only
- `chore:` — build, CI, dependency, or tooling changes
- `test:` — adds or modifies tests only
- `perf:` — measurable performance improvement

**Scopes:** Not used.

**Subject line:** Imperative mood. No period at end. Under 72 characters.

```
feat: add TTL-based eviction to cache layer
fix: handle empty upstream auth header without panic
chore: upgrade bolt to v1.3.1
```

**Body:** Used when the why is not obvious from the subject. Separated by a blank line. Wrapped at 72 characters.

**Branch naming:** `<prefix>/<short-description>` with hyphens.

```
feat/pull-through-cache
fix/token-refresh-race
chore/ci-go-version
```

**Merge strategy:** Squash and merge. No merge commits. Feature branch history is collapsed to one commit on `main`.

**GPG signing:** Required. All commits must be signed.

---

## 14. Dependencies and Tooling

### Go

- **Module:** `go.mod` + `go.sum`. Both committed.
- **Add a dependency:** `go get github.com/example/pkg@v1.2.3` then `go mod tidy`.
- **Linter:** `golangci-lint`. Config in `.golangci.yml` at repo root.
- **Formatter:** `gofmt` (via `goimports`). Enforced by CI — unformatted commits fail the pipeline.
- **CI:** GitHub Actions. Workflow at `.github/workflows/ci.yml`. Runs `make test` and `golangci-lint run` on every push and pull request.
- **Minimum Go:** 1.21 (declared in `go.mod`).

---

## 15. Red Lines

**Formatting violations:**

- Never use spaces for indentation. Go uses tabs. This is enforced by `gofmt` and will fail CI.
- Never place the opening brace of a block on a new line. Go does not permit this syntactically and `gofmt` will reject it.

**Architectural violations:**

- Never add sub-packages. All Go files belong to `package main` at the repo root. Sub-packages fragment the flat structure this codebase intentionally maintains.
- Never put business logic in `main.go`. That file contains only flag parsing and server bootstrap. Logic belongs in the relevant domain file.
- Never define sentinel errors outside `errors.go`. Scattering `var Err...` declarations across files makes them impossible to audit.

**Style violations:**

- Never use `SCREAMING_SNAKE_CASE` for constants. This codebase uses `camelCase` for unexported and `PascalCase` for exported constants.
- Never define an interface in the same file as its implementation. Interfaces are defined at the call site.

**Testing violations:**

- Never use a third-party assertion library. All test assertions use the standard `testing.T` methods directly.
- Never write tests that require network access. Use `testdata/responses/` fixtures for all upstream responses.

**Git violations:**

- Never commit without GPG signing. The CI pipeline rejects unsigned commits.
- Never commit without a conventional prefix. Bare subject lines are not acceptable.
- Never commit commented-out code.
