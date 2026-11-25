"""Extraction utilities for documents (PDF, DOCX, TXT) and web URLs with SSRF protection."""

import io
import ipaddress
import socket
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup
import trafilatura

# Maximum document length to extract (chars)
MAX_DOCUMENT_CHARS = 100_000


class ExtractorError(Exception):
    """Base error for extraction failures."""
    pass


class SSRFSecurityError(ExtractorError):
    """Raised when a URL targets a private or forbidden IP address."""
    pass


def validate_url_security(url: str) -> None:
    """Validate that a URL does not target private, local, or loopback IPs (SSRF protection)."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise SSRFSecurityError(f"Disallowed URL scheme: {parsed.scheme}. Only HTTP and HTTPS are permitted.")

    hostname = parsed.hostname
    if not hostname:
        raise SSRFSecurityError("URL must contain a valid hostname.")

    # Block localhost literals directly
    if hostname.lower() in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
        raise SSRFSecurityError("Access to localhost is forbidden.")

    # Resolve hostname to IP addresses and check each
    try:
        addr_infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as e:
        raise SSRFSecurityError(f"Could not resolve hostname '{hostname}': {e}")

    for addr_info in addr_infos:
        ip_str = addr_info[4][0]
        ip = ipaddress.ip_address(ip_str)

        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            raise SSRFSecurityError(
                f"URL resolves to forbidden private or local IP address: {ip_str}"
            )


def extract_text_from_url(url: str, timeout_seconds: float = 10.0) -> tuple[str, str | None]:
    """Fetch URL and extract clean text. Returns (cleaned_text, title)."""
    validate_url_security(url)

    headers = {
        "User-Agent": "TruthLensAI/1.0 (Fact-Verification Engine; +https://github.com/truthlens)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    try:
        with httpx.Client(timeout=timeout_seconds, follow_redirects=True, max_redirects=3) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()

            # Verify final redirected URL for SSRF as well
            if str(resp.url) != url:
                validate_url_security(str(resp.url))

            html_content = resp.text
    except SSRFSecurityError:
        raise
    except Exception as e:
        raise ExtractorError(f"Failed to fetch URL '{url}': {e}")

    # Use trafilatura first for primary extraction
    extracted = trafilatura.extract(
        html_content,
        include_links=False,
        include_images=False,
        output_format="txt",
    )

    # Extract page title via BeautifulSoup
    soup = BeautifulSoup(html_content, "html.parser")
    # Strip script, style, nav, footer, header tags
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()

    title = None
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    if extracted and extracted.strip():
        return extracted[:MAX_DOCUMENT_CHARS], title

    # Fallback to BeautifulSoup clean text if trafilatura extracts nothing
    body = soup.find("body") or soup
    text = body.get_text(separator="\n", strip=True)
    if not text.strip():
        raise ExtractorError("No readable text could be extracted from the page.")

    return text[:MAX_DOCUMENT_CHARS], title


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract plain text from a PDF file using PyMuPDF (fitz)."""
    import fitz  # PyMuPDF

    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        pages_text: list[str] = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            if text.strip():
                pages_text.append(text.strip())

        doc.close()
    except Exception as e:
        raise ExtractorError(f"Failed to parse PDF document: {e}")

    combined = "\n\n".join(pages_text)
    if not combined.strip():
        raise ExtractorError("The PDF document contains no readable text.")

    return combined[:MAX_DOCUMENT_CHARS]


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract plain text from a DOCX document using python-docx."""
    import docx

    try:
        doc = docx.Document(io.BytesIO(file_bytes))
        paragraphs: list[str] = []

        for p in doc.paragraphs:
            if p.text.strip():
                paragraphs.append(p.text.strip())

        # Also extract table contents
        for table in doc.tables:
            for row in table.rows:
                row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_cells:
                    paragraphs.append(" | ".join(row_cells))

    except Exception as e:
        raise ExtractorError(f"Failed to parse DOCX document: {e}")

    combined = "\n\n".join(paragraphs)
    if not combined.strip():
        raise ExtractorError("The DOCX document contains no readable text.")

    return combined[:MAX_DOCUMENT_CHARS]


def extract_text_from_txt(file_bytes: bytes) -> str:
    """Decode plain text file with UTF-8 fallback."""
    for encoding in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            return file_bytes.decode(encoding)[:MAX_DOCUMENT_CHARS]
        except (UnicodeDecodeError, LookupError):
            continue
    raise ExtractorError("Unable to decode text file with standard encodings.")
