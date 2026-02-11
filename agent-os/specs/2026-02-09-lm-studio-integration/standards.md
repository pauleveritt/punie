# Standards: LM Studio Integration

This implementation follows these Agent OS standards:

## agent-verification

- Every public function has corresponding tests
- Tests verify both success and error cases
- Test coverage maintained after removing MLX tests

## protocol-first-design

- Use OpenAI-compatible API protocol (industry standard)
- Let server handle model details (loading, templates, tool calling)
- Client only needs URL + model name

## protocol-satisfaction-test

- Verify connection errors are handled gracefully
- Test fallback behavior when server unreachable
- Document protocol expectations in tests

## function-based-tests

- All new tests use function-based approach (no test classes)
- Test files: `test_local_model_spec.py`, `test_local_server_fallback.py`
- Clear, focused test functions with descriptive names

## fakes-over-mocks

- Use fake implementations where possible
- Avoid excessive mocking in tests
- Test against real data structures (LocalModelSpec)

## Additional Standards Applied

### Simplicity
- Replace 2,400 lines with ~5 lines of factory logic
- Remove complexity (chat templates, quantization, format parsing)
- Clear, minimal API surface

### Documentation
- Comprehensive docstrings with examples
- Spec documents capture decisions
- README updated with LM Studio setup

### Error Handling
- Helpful error messages for missing server
- Guide users to LM Studio setup
- Graceful degradation when unavailable

### Testability
- Pure functions for parsing logic
- Clear separation of concerns
- Easy to test in isolation
