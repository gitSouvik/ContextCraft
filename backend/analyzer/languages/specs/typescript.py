from dataclasses import replace

from .javascript import JAVASCRIPT_SPEC

TYPESCRIPT_SPEC = replace(
    JAVASCRIPT_SPEC,
    language_id="typescript",
    ts_language_name="typescript",
)
