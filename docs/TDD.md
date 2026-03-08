# Test-Driven Development (TDD) Guide

## Overview

This project follows Test-Driven Development principles to ensure code quality, maintainability, and reliability. All features should be developed using the TDD cycle: **Red → Green → Refactor**.

## TDD Principles

### 1. Red-Green-Refactor Cycle

1. **Red**: Write a failing test first
   - Define the expected behavior
   - Write the minimal test that fails
   - Run tests to confirm failure

2. **Green**: Write the minimum code to pass
   - Implement only what's needed to pass the test
   - Don't worry about perfection
   - Run tests to confirm success

3. **Refactor**: Improve the code
   - Clean up implementation
   - Remove duplication
   - Optimize if needed
   - Ensure tests still pass

### 2. Test First, Always

- Write tests before implementation
- Tests serve as documentation
- Tests define requirements
- Tests catch regressions

### 3. Small Steps

- Write one test at a time
- Make small, incremental changes
- Run tests frequently
- Commit after each passing test

## Python Late Binding Considerations

### The Problem

Python closures have late binding, which can cause issues in tests:

```python
# WRONG - Late binding issue
def test_wrong():
    results = []
    for i in range(3):
        def action():
            results.append(i)
        action()
    # results = [2, 2, 2] - not [0, 1, 2]!
```

### Solutions

#### 1. Use Default Arguments (Early Binding)

```python
# CORRECT - Early binding with default argument
def test_correct():
    results = []
    for i in range(3):
        def action(i=i):  # Capture i by value
            results.append(i)
        action()
    # results = [0, 1, 2] ✓
```

#### 2. Use functools.partial

```python
from functools import partial

def test_with_partial():
    results = []
    for i in range(3):
        action = partial(lambda x: results.append(x), i)
        action()
    # results = [0, 1, 2] ✓
```

#### 3. Use Lambda with Immediate Capture

```python
def test_with_lambda():
    results = []
    for i in range(3):
        (lambda x: results.append(x))(i)
    # results = [0, 1, 2] ✓
```

#### 4. Use List Comprehensions

```python
def test_with_comprehension():
    results = [i for i in range(3)]
    # results = [0, 1, 2] ✓
```

## Test Structure

### Test File Organization

```
myTTS/
├── mytts/
│   ├── __init__.py
│   ├── client.py
│   ├── server.py
│   └── tui.py
├── tests/
│   ├── __init__.py
│   ├── test_client.py
│   ├── test_server.py
│   ├── test_tui.py
│   └── conftest.py
├── test_comprehensive.py
├── test_server_durability.py
└── pytest.ini
```

### Test Class Structure

```python
import pytest
from unittest.mock import Mock, patch, MagicMock

class TestFeature:
    """Test suite for Feature X."""
    
    @pytest.fixture
    def setup_data(self):
        """Provide test data."""
        return {"key": "value"}
    
    def test_happy_path(self, setup_data):
        """Test normal operation."""
        # Arrange
        expected = "value"
        
        # Act
        result = setup_data["key"]
        
        # Assert
        assert result == expected
    
    def test_edge_case(self):
        """Test boundary conditions."""
        pass
    
    def test_error_handling(self):
        """Test error conditions."""
        with pytest.raises(ValueError):
            raise ValueError("Expected error")
```

## Code Coverage Requirements

### Coverage Targets

- **Minimum**: 80% line coverage
- **Target**: 90% line coverage
- **Critical paths**: 100% coverage
  - Error handling
  - Audio playback
  - Server requests
  - TUI interactions

### Running Coverage

```bash
# Install coverage tools
pip install pytest pytest-cov

# Run tests with coverage
pytest --cov=mytts --cov-report=term-missing

# Generate HTML report
pytest --cov=mytts --cov-report=html
open htmlcov/index.html

# Run specific test file with coverage
pytest test_comprehensive.py --cov=mytts.client -v
```

### Coverage Configuration

Create `.coveragerc`:

```ini
[run]
source = mytts
omit = 
    */tests/*
    */venv/*
    */__pycache__/*
    */site-packages/*

[report]
precision = 2
show_missing = True
skip_covered = False

[html]
directory = htmlcov
```

## Test Categories

### 1. Unit Tests

Test individual functions/methods in isolation:

```python
def test_split_into_sentences():
    """Test sentence splitting logic."""
    client = ProgressiveTTSClient(mock_engine)
    
    # Test cases
    assert client.split_into_sentences("One. Two.") == ["One.", "Two."]
    assert client.split_into_sentences("") == []
    assert client.split_into_sentences("No ending") == ["No ending."]
```

### 2. Integration Tests

Test component interactions:

```python
def test_client_server_integration():
    """Test client communicating with server."""
    response = requests.post(
        f"{SERVER_URL}/tts",
        json={"text": "Test", "voice": "en_US-lessac-medium"}
    )
    assert response.status_code == 200
```

### 3. Durability Tests

Test error recovery and resilience:

```python
def test_server_recovers_from_error():
    """Test server handles errors gracefully."""
    # Trigger error
    requests.post(f"{SERVER_URL}/tts", json={"text": ""})
    
    # Verify recovery
    response = requests.post(
        f"{SERVER_URL}/tts",
        json={"text": "Valid text"}
    )
    assert response.status_code == 200
```

### 4. Performance Tests

Test under load:

```python
def test_concurrent_requests():
    """Test handling concurrent requests."""
    threads = []
    for i in range(10):
        thread = threading.Thread(target=make_request, args=(i,))
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join(timeout=30)
```

## Mocking Strategies

### 1. Mock External Dependencies

```python
@patch('mytts.client.sd.play')
@patch('mytts.client.sd.wait')
def test_audio_playback(mock_wait, mock_play):
    """Test audio playback without actual sound."""
    client = ProgressiveTTSClient(mock_engine)
    client._play_chunk(chunk)
    
    mock_play.assert_called_once()
    mock_wait.assert_called_once()
```

### 2. Mock Network Requests

```python
@patch('requests.post')
def test_tts_request(mock_post):
    """Test TTS request without network."""
    mock_post.return_value = Mock(status_code=200)
    
    response = requests.post(f"{SERVER_URL}/tts", json={})
    assert response.status_code == 200
```

### 3. Mock File I/O

```python
@patch('builtins.open', read_data="test content")
def test_file_reading(mock_open):
    """Test file reading without actual file."""
    content = Path("test.txt").read_text()
    assert content == "test content"
```

## TDD Workflow Example

### Feature: Add Voice Cycling to TUI

#### Step 1: Write Failing Test (Red)

```python
def test_voice_cycling():
    """Test that 'v' key cycles through voices."""
    app = TTSReaderApp(file_path="test.txt")
    
    # Initial voice
    assert app.current_voice_index == 0
    
    # Cycle voice
    app.action_cycle_voice()
    assert app.current_voice_index == 1
    
    # Cycle again
    app.action_cycle_voice()
    assert app.current_voice_index == 2
```

Run test: **FAILS** (method doesn't exist)

#### Step 2: Implement Feature (Green)

```python
def action_cycle_voice(self):
    """Cycle to next voice."""
    self.current_voice_index = (self.current_voice_index + 1) % len(self.available_voices)
```

Run test: **PASSES** ✓

#### Step 3: Refactor

```python
def action_cycle_voice(self):
    """Cycle to next voice with error handling."""
    self.current_voice_index = (self.current_voice_index + 1) % len(self.available_voices)
    new_voice = self.available_voices[self.current_voice_index]
    
    # Update engine and restart playback
    self._restart_with_new_voice(new_voice)
```

Run test: **STILL PASSES** ✓

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.10
    
    - name: Install dependencies
      run: |
        pip install -e .
        pip install pytest pytest-cov
    
    - name: Run tests with coverage
      run: |
        pytest --cov=mytts --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v2
```

## Best Practices

### 1. Test Naming

```python
# Good: Descriptive name
def test_client_handles_empty_text_gracefully():
    pass

# Bad: Vague name
def test_error():
    pass
```

### 2. Arrange-Act-Assert Pattern

```python
def test_speed_adjustment():
    # Arrange
    client = ProgressiveTTSClient(mock_engine)
    initial_speed = client.speed
    
    # Act
    client.increase_speed()
    
    # Assert
    assert client.speed == initial_speed + 0.1
```

### 3. One Assertion Per Test (Mostly)

```python
# Good: Focused test
def test_increase_speed():
    client = ProgressiveTTSClient(mock_engine)
    client.increase_speed()
    assert client.speed == 1.1

# Also acceptable: Related assertions
def test_speed_bounds():
    client = ProgressiveTTSClient(mock_engine)
    client.speed = 4.0
    client.increase_speed()  # Should not exceed 4.0
    assert client.speed == 4.0
```

### 4. Test Edge Cases

```python
@pytest.mark.parametrize("input,expected", [
    ("", []),
    ("One sentence", ["One sentence."]),
    ("Two. Sentences.", ["Two.", "Sentences."]),
    ("Already ends!", ["Already ends!"]),
])
def test_sentence_splitting(input, expected):
    client = ProgressiveTTSClient(mock_engine)
    result = client.split_into_sentences(input)
    assert result == expected
```

### 5. Test Error Conditions

```python
def test_empty_text_raises_error():
    """Test that empty text is handled."""
    with pytest.raises(ValueError):
        validate_text("")
```

## Test Maintenance

### 1. Keep Tests Fast

- Use mocks for slow operations
- Avoid network calls in unit tests
- Use in-memory databases/files

### 2. Keep Tests Independent

- Each test should run alone
- No shared mutable state
- Use fixtures for setup

### 3. Keep Tests Readable

- Clear test names
- Simple logic
- Well-structured code

### 4. Update Tests with Code

- Tests are living documentation
- Update tests when changing behavior
- Remove tests for removed features

## Coverage Reports

### Interpreting Coverage

```
Name                    Stmts   Miss  Cover   Missing
-----------------------------------------------------
mytts/client.py           150      5    97%   45-47
mytts/server.py           200     10    95%   123, 145-150
mytts/tui.py              300     15    95%   78-82
-----------------------------------------------------
TOTAL                     650     30    95%
```

- **Stmts**: Total statements
- **Miss**: Uncovered statements
- **Cover**: Coverage percentage
- **Missing**: Line numbers not covered

### Improving Coverage

1. Identify missing lines
2. Write tests for those paths
3. Focus on critical paths first
4. Don't chase 100% blindly

## Common Pitfalls

### 1. Late Binding in Loops

```python
# WRONG
for i in range(3):
    thread = Thread(target=lambda: print(i))
    thread.start()
# Prints: 2, 2, 2

# CORRECT
for i in range(3):
    thread = Thread(target=lambda x=i: print(x))
    thread.start()
# Prints: 0, 1, 2
```

### 2. Shared Mutable State

```python
# WRONG
shared_list = []

def test_1():
    shared_list.append(1)

def test_2():
    assert len(shared_list) == 0  # FAILS if test_1 ran first

# CORRECT
def test_1():
    test_list = []
    test_list.append(1)
    assert len(test_list) == 1
```

### 3. Not Testing Error Paths

```python
# WRONG - Only happy path
def test_parse():
    result = parse("valid")
    assert result is not None

# CORRECT - Include error paths
def test_parse_invalid():
    with pytest.raises(ParseError):
        parse("invalid")
```

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [Python Testing with pytest](https://pragprog.com/titles/bopytest/)
- [Test-Driven Development](https://en.wikipedia.org/wiki/Test-driven_development)
- [Coverage.py](https://coverage.readthedocs.io/)

## Summary

1. **Write tests first** (Red-Green-Refactor)
2. **Account for late binding** in Python closures
3. **Aim for 90% coverage**, 100% on critical paths
4. **Use mocks** to isolate units
5. **Keep tests fast, independent, and readable**
6. **Update tests with code changes**
7. **Run tests frequently** during development
