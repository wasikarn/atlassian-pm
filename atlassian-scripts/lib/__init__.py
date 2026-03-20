"""Shared library modules for Atlassian scripts.

Modules:
    exceptions: Custom exception classes (Confluence + Jira)
    auth: SSL context, credentials loading, authentication
    api: Confluence REST API client
    jira_api: Jira REST API v3 client (ADF manipulation)
    converters: Content conversion utilities
"""

from .adf_validator import (
    AdfValidator,
    CheckResult,
    CheckStatus,
    ValidationReport,
    detect_format,
    extract_text,
    find_adf_nodes,
    walk_adf,
)
from .api import ConfluenceAPI
from .auth import (
    create_ssl_context,
    get_auth_header,
    load_credentials,
)
from .converters import (
    convert_inline,
    create_code_macro,
    fix_code_blocks,
    markdown_to_storage,
)
from .exceptions import (
    APIError,
    ConfluenceError,
    ContentConversionError,
    CredentialsError,
    IssueNotFoundError,
    JiraError,
    PageNotFoundError,
    ValidationError,
    WorkflowError,
)
from .jira_api import (
    JiraAPI,
    derive_jira_url,
    walk_and_replace,
)

__all__ = [
    "APIError",
    # ADF Validator
    "AdfValidator",
    "CheckResult",
    "CheckStatus",
    # API - Confluence
    "ConfluenceAPI",
    # Exceptions
    "ConfluenceError",
    "ContentConversionError",
    "CredentialsError",
    "IssueNotFoundError",
    # API - Jira
    "JiraAPI",
    "JiraError",
    "PageNotFoundError",
    "ValidationError",
    "ValidationReport",
    "WorkflowError",
    "convert_inline",
    "create_code_macro",
    # Auth
    "create_ssl_context",
    "derive_jira_url",
    "detect_format",
    "extract_text",
    "find_adf_nodes",
    "fix_code_blocks",
    "get_auth_header",
    "load_credentials",
    # Converters
    "markdown_to_storage",
    "walk_adf",
    "walk_and_replace",
]
