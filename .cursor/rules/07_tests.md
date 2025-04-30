path: tests/

# Context for the Tests Package

Contains automated tests using pytest.

- Mirrors `src/` structure.
- Uses `pytest` fixtures (`conftest.py`) for setup.
- Uses `unittest.mock` / `pytest-mock` (`mocker`) for isolating units.
- Uses `pytest-asyncio` for async code.
- Uses `pytest-cov` for coverage.
- API tests use Litestar's `AsyncTestClient`.
- Uses `pytest.raises` for exception testing.
    