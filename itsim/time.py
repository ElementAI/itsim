import datetime

"""
    Helper functions to handle time consistently across itsim
"""


def now_iso8601():
    return datetime.datetime.now().isoformat()
