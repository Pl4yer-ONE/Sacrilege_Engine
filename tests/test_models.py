"""Unit tests for the Vector3 model."""

from src.models import Vector3

def test_distance_squared_to(self):
    """Test the distance_squared_to method."""
    assert v1.distance_squared_to(v2) == 27

def test_distance_2d_squared(v1, v2):
    """Test the distance_2d_squared method."""
    assert v1.distance_2d_squared(v2) == 18

def test_magnitude_squared(v1):
    """Test the magnitude_squared method."""
    assert v1.magnitude_squared() == 14

def test_distance_to(v1, v2):
    """Test the distance_to method."""
    assert v1.distance_to(v2) == pytest.approx(5.1961524227)

def test_distance_2d(v1, v2):
    """Test the distance_2d method."""
    assert v1.distance_2d(v2) == pytest.approx(4.2426406871)

def test_magnitude(v1):
    """Test the magnitude method."""
    assert v1.magnitude() == pytest.approx(3.7416573868)
