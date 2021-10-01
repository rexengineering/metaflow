'''Defines the IntCounter utility/convenience type.

Developer note: this was removed from flowclib to avoid a circular import.
'''

class IntCounter:
    def __init__(self, value: int = 0):
        self._value = value

    @property
    def value(self) -> int:
        return self._value

    @property
    def postinc(self) -> int:
        result = self._value
        self._value += 1
        return result
