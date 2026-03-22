# How to structure error responses in the API

## Decision
Use RFC 7807 Problem Details format with a wrapper envelope: `{"error": {"type": "...", "title": "...", "detail": "...", "status": 400}}`.

## Why
- RFC 7807 is a widely adopted standard — clients and tools already know how to parse it
- The envelope wrapper (`{"error": ...}`) keeps top-level response structure consistent between success and error cases
- Including `status` in the body allows clients to inspect errors without checking HTTP headers

## Rejected alternatives

### Plain string messages
Returns `{"message": "something went wrong"}`. Too unstructured — clients cannot programmatically distinguish error types without parsing strings.

### Nested error codes with numeric IDs
Custom numeric codes (e.g., `{"code": 40102, "message": "..."}`) require a lookup table and are harder to debug than human-readable `type` URIs.
