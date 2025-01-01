"""Test module for formatting checks."""

from typing import Any


def badly_formatted_function(x: int, y: int, z: int) -> int:
    """Format this docstring properly.

    Parameters
    ----------
    x : int
        First parameter
    y : int
        Second parameter
    z : int
        Third parameter

    Returns
    -------
    int
        Sum of parameters

    """
    return x + y + z


def unused_function() -> None:
    """Do nothing."""
    pass


class BadlyFormattedClass:
    """Class for testing formatting."""

    def __init__(self, name: str = "default", age: int | None = None) -> None:
        """Initialize the class.

        Parameters
        ----------
        name : str
            Name of the instance
        age : int | None
            Age of the instance

        """
        self.name = name
        self._age = age
        self.unused_attr: list[Any] = []

    def method_with_issues(self) -> None:
        """Print a greeting."""
        print(f"Hello, {self.name}")
        if self._age is None:
            print("Age not set")


def function_with_type_issues(items: list[Any], flag: bool = False) -> dict[str, Any]:
    """Process items and return a dictionary.

    Parameters
    ----------
    items : list[Any]
        List of items to process
    flag : bool
        Processing flag

    Returns
    -------
    dict[str, Any]
        Processed items

    """
    result = {}
    for i, item in enumerate(items):
        result[str(i)] = item
    return result


def complex_function(data: dict[str, Any], threshold: int = 10) -> list[str] | None:
    """Process data and return a list of strings.

    Parameters
    ----------
    data : dict[str, Any]
        Data to process
    threshold : int
        Processing threshold

    Returns
    -------
    list[str] | None
        Processed data or None if no data

    """
    if not data:
        return None

    result = []
    for key, value in data.items():
        if isinstance(value, (int | float)) and value > threshold:
            result.append(f"{key}:{value}")
    return result
