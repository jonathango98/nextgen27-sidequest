"""Keeps query strings out of the server's access log (ARCH-051).

An usher's name search is in the URL of GET /usher/players, and the log must never hold a last name.
"""

import logging


def _drop_query(record: logging.LogRecord) -> bool:
    if isinstance(record.args, tuple):
        record.args = tuple(
            arg.partition("?")[0] if isinstance(arg, str) else arg
            for arg in record.args
        )
    return True


def keep_queries_out_of_log() -> None:
    # Called once uvicorn has set up its loggers. Adding the same filter twice changes nothing.
    logging.getLogger("uvicorn.access").addFilter(_drop_query)
