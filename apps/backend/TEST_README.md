# Testing Documentation

## Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Pytest configuration and fixtures
├── test_auth_endpoints.py   # Authentication system tests
├── test_price_endpoints.py  # Price API and streaming tests
├── test_trading_endpoints.py # Trading system tests
├── test_database.py         # Database model and operation tests
└── pytest.ini              # Pytest configuration
```

## Setup

### 1. Install Test Dependencies

```bash
# Install test-specific requirements
pip install -r test-requirements.txt

# Or using the test runner
python run_tests.py --install
```

### 2. Environment Setup

Tests use an in-memory SQLite database for isolation. No additional setup required.

### 3. Verify Setup

```bash
python run_tests.py setup
```

## Running Tests

### Quick Start

```bash
# Run all tests
python run_tests.py

# Run with verbose output
python run_tests.py all --verbose

# Run with coverage
python run_tests.py all --coverage
```

### Running Specific Test Categories

```bash
# Unit tests only
python run_tests.py unit

# Integration tests only
python run_tests.py integration

# Authentication tests
python run_tests.py auth

# Trading system tests
python run_tests.py trading

# Price data tests
python run_tests.py price

# Database tests
python run_tests.py database

# Slow tests (may require network)
python run_tests.py slow
```

### Running Specific Files

```bash
# Run a specific test file
python run_tests.py --file tests/test_auth_endpoints.py

# Run a specific test function
python -m pytest tests/test_auth_endpoints.py::TestAuthEndpoints::test_register_user -v
```

### Parallel Execution

```bash
# Run tests in parallel
python run_tests.py all --parallel
```

## Test Fixtures

The `conftest.py` file provides reusable fixtures:

- `db_session`: Fresh database session for each test
- `client`: HTTP test client
- `authenticated_client`: Authenticated HTTP client
- `test_user`: Test user with authentication token
- `sample_gold_price`: Sample gold price data
- `sample_gold96_price`: Sample gold 96 price data
- `sample_transaction_data`: Sample transaction data

## Writing Tests

### Basic Test Structure

```python
import pytest
from httpx import AsyncClient

class TestMyFeature:
    @pytest.mark.asyncio
    async def test_my_functionality(self, client: AsyncClient):
        response = await client.get("/my-endpoint")
        assert response.status_code == 200
        assert response.json()["key"] == "expected_value"
```

### Using Fixtures

```python
@pytest.mark.asyncio
async def test_authenticated_endpoint(self, authenticated_client: AsyncClient):
    response = await authenticated_client.get("/protected-route")
    assert response.status_code == 200
```

### Database Testing

```python
@pytest.mark.asyncio
async def test_database_operation(self, db_session: AsyncSession):
    # Test with fresh database session
    # Changes are automatically rolled back
    pass
```

### Test Markers

Use markers to categorize tests:

```python
@pytest.mark.unit
def test_unit_function():
    pass

@pytest.mark.integration
async def test_integration():
    pass

@pytest.mark.slow
async def test_network_operation():
    pass
```

## Coverage

### Generate Coverage Report

```bash
python run_tests.py coverage
```

Coverage reports are generated in:
- Terminal: Summary with missing lines
- HTML: `htmlcov/index.html`
- XML: `coverage.xml`

### Coverage Threshold

Tests must maintain at least 80% coverage. This is enforced in CI.

## Test Categories

### Unit Tests (`@pytest.mark.unit`)
- Fast tests that don't require external dependencies
- Test individual functions and methods
- Mock external services

### Integration Tests (`@pytest.mark.integration`)
- Test integration between components
- Use real database (SQLite in-memory)
- Test service layer functionality

### Authentication Tests (`@pytest.mark.auth`)
- User registration and login
- Token validation
- Permission checking
- Password security

### Trading Tests (`@pytest.mark.trading`)
- Transaction creation and processing
- Balance management
- Portfolio operations
- Queue functionality

### Price Tests (`@pytest.mark.price`)
- Price data storage and retrieval
- SSE streaming functionality
- Price history queries
- Statistics calculations

### Database Tests (`@pytest.mark.database`)
- Model validation
- Constraint enforcement
- Query optimization
- Transaction management

### Slow Tests (`@pytest.mark.slow`)
- Tests that may require network calls
- Performance benchmarks
- External API integrations

## Best Practices

### 1. Test Organization
- Group related tests in classes
- Use descriptive test names
- Follow the AAA pattern (Arrange, Act, Assert)

### 2. Database Tests
- Each test gets a fresh database
- Tests are automatically cleaned up
- Use fixtures for common data setup

### 3. API Tests
- Test both success and error cases
- Validate response schemas
- Test authentication/authorization

### 4. Async Testing
- Always use `@pytest.mark.asyncio`
- Use `await` for async operations
- Test error handling with `pytest.raises`

### 5. Mocking
- Mock external services for unit tests
- Use `pytest-mock` for fixtures
- Keep mocks simple and focused

## Continuous Integration

The test suite runs automatically in CI with:

```bash
python run_tests.py all --coverage --parallel
```

CI requirements:
- All tests must pass
- Coverage must be ≥ 80%
- No test may take longer than 30 seconds

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   python run_tests.py setup
   python run_tests.py --install
   ```

2. **Database Locks**
   ```bash
   python run_tests.py clean
   ```

3. **Slow Tests**
   ```bash
   # Skip slow tests
   python -m pytest tests/ -m "not slow"
   ```

4. **Coverage Issues**
   ```bash
   # Generate detailed coverage
   python run_tests.py coverage
   # Open htmlcov/index.html in browser
   ```

### Debugging

Run tests with verbose output and stop on first failure:

```bash
python -m pytest tests/ -v -x --tb=long
```

Run specific test with debugging:

```bash
python -m pytest tests/test_file.py::TestClass::test_method -v -s --pdb
```

## Contributing

When adding new features:

1. Write tests for the new functionality
2. Ensure all tests pass
3. Maintain coverage threshold
4. Add appropriate test markers
5. Update documentation if needed

### Test Naming Convention

- Test files: `test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`
- Descriptive names that explain what is being tested

### Example New Test

```python
@pytest.mark.unit
async def test_feature_with_valid_input(self, client: AsyncClient):
    """Test that feature works correctly with valid input"""
    # Arrange
    input_data = {"key": "value"}
    
    # Act
    response = await client.post("/feature", json=input_data)
    
    # Assert
    assert response.status_code == 200
    assert response.json()["result"] == "expected"
```

## Performance Testing

For performance-critical components, use the slow marker:

```python
import time

@pytest.mark.slow
async def test_api_response_time(self, client: AsyncClient):
    """Test that API responds within acceptable time"""
    start_time = time.time()
    response = await client.get("/expensive-endpoint")
    response_time = time.time() - start_time
    
    assert response.status_code == 200
    assert response_time < 2.0  # Should respond within 2 seconds
```

## Security Testing

Security-related tests are in the auth category:

```python
@pytest.mark.auth
async def test_sql_injection_protection(self, client: AsyncClient):
    """Test that SQL injection attempts are blocked"""
    malicious_input = "'; DROP TABLE users; --"
    response = await client.get(f"/search?q={malicious_input}")
    
    assert response.status_code in [400, 422]
    # Verify database still exists and contains expected data
```
