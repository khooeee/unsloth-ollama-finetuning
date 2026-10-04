"""Intentional bug: divide uses floor division instead of true division."""


def add(a: float, b: float) -> float:
    return a + b


def divide(a: float, b: float) -> float:
    # BUG: should be a / b (true division)
    return a // b
