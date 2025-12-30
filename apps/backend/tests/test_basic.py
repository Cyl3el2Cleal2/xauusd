import pytest


@pytest.mark.unit
def test_basic_math():
    """Basic test to verify pytest is working"""
    assert 1 + 1 == 2


@pytest.mark.unit
def test_string_operations():
    """Test basic string operations"""
    test_string = "hello world"
    assert test_string.upper() == "HELLO WORLD"
    assert test_string.title() == "Hello World"
    assert "world" in test_string


@pytest.mark.unit
def test_list_operations():
    """Test basic list operations"""
    test_list = [1, 2, 3, 4, 5]
    assert len(test_list) == 5
    assert test_list[0] == 1
    assert test_list[-1] == 5
    assert 3 in test_list


@pytest.mark.unit
def test_dictionary_operations():
    """Test basic dictionary operations"""
    test_dict = {"key1": "value1", "key2": "value2"}
    assert "key1" in test_dict
    assert test_dict["key1"] == "value1"
    assert len(test_dict) == 2


@pytest.mark.asyncio
@pytest.mark.unit
async def test_async_basic():
    """Basic async test to verify async testing works"""
    async def async_add(a, b):
        return a + b

    result = await async_add(2, 3)
    assert result == 5


@pytest.mark.unit
def test_exception_handling():
    """Test exception handling"""
    with pytest.raises(ValueError):
        int("not_a_number")

    with pytest.raises(ZeroDivisionError):
        result = 1 / 0


class TestBasicClass:
    """Basic test class structure"""

    @pytest.mark.unit
    def test_method_one(self):
        assert True

    @pytest.mark.unit
    def test_method_two(self):
        assert "test" in "testing"

    @pytest.mark.unit
    def test_setup_teardown_example(self):
        """Example of setup and teardown concepts"""
        # Setup
        test_data = {"initialized": True}

        # Test
        assert test_data["initialized"] is True

        # Teardown (automatic in pytest fixtures)
        pass
