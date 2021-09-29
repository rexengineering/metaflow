#!python3
"""Test flowlib.utils"""

from flowlib.utils import get_log_format

def test_get_log_format():
    log_format = get_log_format("marzipan")
    assert "|marzipan|" in log_format, "program name is in-between pipes"
