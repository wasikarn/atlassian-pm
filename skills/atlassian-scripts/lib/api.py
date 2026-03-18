"""Confluence REST API client.

This module provides a class-based API client for Confluence operations:
- Get page content and metadata
- Create new pages
- Update existing pages
- Move pages to new parent

Usage:
    from lib.api import ConfluenceAPI
    from lib.auth import create_ssl_context, load_credentials, get_auth_header

    creds = load_credentials()
    api = ConfluenceAPI(
        base_url=creds["CONFLUENCE_URL"],
        auth_header=get_auth_header(creds["CONFLUENCE_USERNAME"], creds["CONFLUENCE_API_TOKEN"]),
        ssl_context=create_ssl_context()
    )

    page = api.get_page("123456")
    api.update_page("123456", "Title", "<p>Content</p>", version=2)
"""

import json
import logging
import ssl
import urllib.error
import urllib.request
from typing import Any, TypedDict

from .exceptions import APIError, PageNotFoundError

logger = logging.getLogger(__name__)


class PageInfo(TypedDict, total=False):
    """Type definition for page information."""

    id: str
    title: str
    type: str
    version: dict[str, Any]
    space: dict[str, Any]
    body: dict[str, Any]
    ancestors: list[dict[str, Any]]


class ConfluenceAPI:
    """Confluence REST API client.

    This class provides methods for interacting with the Confluence REST API.
    It handles authentication, SSL context, and error handling.

    Attributes:
        base_url: Confluence wiki base URL (e.g., https://example.atlassian.net/wiki)
        auth_header: Authorization header value (Basic auth)
        ssl_context: SSL context for HTTPS requests

    Example:
        >>> api = ConfluenceAPI(base_url, auth_header, ssl_context)
        >>> page = api.get_page("123456")
        >>> print(page["title"])
    """

    def __init__(
        self,
        base_url: str,
        auth_header: str,
        ssl_context: ssl.SSLContext | None = None,
    ) -> None:
        """Initialize Confluence API client.

        Args:
            base_url: Confluence wiki base URL (e.g., https://example.atlassian.net/wiki)
            auth_header: Authorization header value from get_auth_header()
            ssl_context: SSL context for HTTPS requests. If None, default context is used.
        """
        self.base_url = base_url.rstrip("/")
        self.auth_header = auth_header
        self.ssl_context = ssl_context
        logger.debug("ConfluenceAPI initialized for %s", self.base_url)

    def _request(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an HTTP request to the Confluence API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (e.g., /rest/api/content/123456)
            data: Request body data (will be JSON encoded)

        Returns:
            Parsed JSON response.

        Raises:
            PageNotFoundError: If page not found (404)
            APIError: If API request fails
        """
        url = f"{self.base_url}{endpoint}"
        logger.debug("%s %s", method, url)

        req = urllib.request.Request(url, method=method)
        req.add_header("Authorization", self.auth_header)
        req.add_header("Content-Type", "application/json")

        if data is not None:
            req.data = json.dumps(data).encode("utf-8")

        try:
            with urllib.request.urlopen(req, context=self.ssl_context) as response:
                response_data = response.read().decode("utf-8")
                if response_data:
                    return json.loads(response_data)
                return {}

        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            logger.error("API error: %s %s - %s", e.code, e.reason, error_body[:200])

            if e.code == 404:
                raise PageNotFoundError("unknown", f"Resource not found: {endpoint}") from e

            raise APIError(e.code, e.reason, error_body) from e

        except urllib.error.URLError as e:
            logger.error("URL error: %s", e.reason)
            raise APIError(0, str(e.reason), "") from e

    def get_page(
        self,
        page_id: str,
        expand: str = "body.storage,version,space,ancestors",
    ) -> PageInfo:
        """Get Confluence page by ID.

        Args:
            page_id: Confluence page ID
            expand: Fields to expand (comma-separated)

        Returns:
            Page information including content and metadata.

        Raises:
            PageNotFoundError: If page ID doesn't exist
            APIError: If API request fails
        """
        logger.info("Getting page %s", page_id)

        try:
            result = self._request("GET", f"/rest/api/content/{page_id}?expand={expand}")
            return PageInfo(**result)
        except PageNotFoundError:
            raise PageNotFoundError(page_id) from None

    def create_page(
        self,
        space_key: str,
        title: str,
        content: str,
        parent_id: str | None = None,
    ) -> PageInfo:
        """Create a new Confluence page.

        Args:
            space_key: Space key (e.g., "BEP")
            title: Page title
            content: Page content in storage format (HTML)
            parent_id: Optional parent page ID

        Returns:
            Created page information.

        Raises:
            APIError: If page creation fails
        """
        logger.info("Creating page '%s' in space %s", title, space_key)

        data: dict[str, Any] = {
            "type": "page",
            "title": title,
            "space": {"key": space_key},
            "body": {
                "storage": {
                    "value": content,
                    "representation": "storage",
                }
            },
        }

        if parent_id:
            data["ancestors"] = [{"id": str(parent_id)}]
            logger.debug("Setting parent page: %s", parent_id)

        result = self._request("POST", "/rest/api/content", data)
        logger.info("Created page %s", result.get("id"))
        return PageInfo(**result)

    def update_page(
        self,
        page_id: str,
        title: str,
        content: str,
        version: int,
    ) -> PageInfo:
        """Update an existing Confluence page.

        Args:
            page_id: Page ID to update
            title: New page title
            content: New page content in storage format (HTML)
            version: Current page version (will be incremented)

        Returns:
            Updated page information.

        Raises:
            PageNotFoundError: If page ID doesn't exist
            APIError: If page update fails
        """
        logger.info("Updating page %s to version %d", page_id, version + 1)

        data = {
            "id": page_id,
            "type": "page",
            "title": title,
            "body": {
                "storage": {
                    "value": content,
                    "representation": "storage",
                }
            },
            "version": {
                "number": version + 1,
            },
        }

        result = self._request("PUT", f"/rest/api/content/{page_id}", data)
        logger.info("Updated page to version %s", result.get("version", {}).get("number"))
        return PageInfo(**result)

    def move_page(
        self,
        page_id: str,
        target_parent_id: str,
        position: str = "append",
    ) -> PageInfo:
        """Move a page to be a child of another page.

        Args:
            page_id: Page ID to move
            target_parent_id: Target parent page ID
            position: Position relative to target (append, prepend, before, after)

        Returns:
            Moved page information.

        Raises:
            PageNotFoundError: If page or target doesn't exist
            APIError: If move operation fails
        """
        logger.info("Moving page %s to parent %s (%s)", page_id, target_parent_id, position)

        # Move API requires empty body
        result = self._request(
            "PUT",
            f"/rest/api/content/{page_id}/move/{position}/{target_parent_id}",
            {},
        )
        logger.info("Page moved successfully")
        return PageInfo(**result)

    def get_page_url(self, page_id: str) -> str:
        """Get the view URL for a page.

        Args:
            page_id: Page ID

        Returns:
            Full URL to view the page.
        """
        return f"{self.base_url}/pages/viewpage.action?pageId={page_id}"
