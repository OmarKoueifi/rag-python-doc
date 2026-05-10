from typing import Final

DOCS_BASE_URL: Final = "https://docs.python.org"

# All in approximate tokens (cl100k_base).
CHUNK_MIN_TOKENS: Final = 400
CHUNK_TARGET_TOKENS: Final = 900
CHUNK_MAX_TOKENS: Final = 1200

DEFAULT_TOP_K: Final = 5
MAX_QUESTION_CHARS: Final = 1000

ARCHIVE_URL_TEMPLATE: Final = (
    "https://www.python.org/ftp/python/doc/{version}/python-{version}-docs-html.zip"
)
