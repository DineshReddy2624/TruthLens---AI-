"""Unit tests for document and URL extraction with SSRF security protection."""

import pytest
from app.services.extractor import (
    validate_url_security,
    extract_text_from_txt,
    extract_text_from_pdf,
    extract_text_from_docx,
    SSRFSecurityError,
    ExtractorError,
)


class TestSSRFProtection:
    def test_blocks_localhost(self):
        with pytest.raises(SSRFSecurityError, match="Access to localhost is forbidden"):
            validate_url_security("http://localhost:8000/secret")

    def test_blocks_loopback_ip(self):
        with pytest.raises(SSRFSecurityError, match="Access to localhost is forbidden"):
            validate_url_security("http://127.0.0.1/admin")

    def test_blocks_zero_ip(self):
        with pytest.raises(SSRFSecurityError, match="Access to localhost is forbidden"):
            validate_url_security("http://0.0.0.0/test")

    def test_blocks_private_class_c(self):
        with pytest.raises(SSRFSecurityError, match="forbidden private or local IP"):
            validate_url_security("http://192.168.1.100/router")

    def test_blocks_private_class_a(self):
        with pytest.raises(SSRFSecurityError, match="forbidden private or local IP"):
            validate_url_security("http://10.0.0.1/metadata")

    def test_blocks_non_http_schemes(self):
        with pytest.raises(SSRFSecurityError, match="Disallowed URL scheme"):
            validate_url_security("ftp://example.com/file.txt")

        with pytest.raises(SSRFSecurityError, match="Disallowed URL scheme"):
            validate_url_security("file:///etc/passwd")

        with pytest.raises(SSRFSecurityError, match="Disallowed URL scheme"):
            validate_url_security("gopher://example.com")


class TestTextExtraction:
    def test_extract_utf8_txt(self):
        content = "The Great Wall of China is over 13,000 miles long.".encode("utf-8")
        extracted = extract_text_from_txt(content)
        assert "Great Wall of China" in extracted

    def test_extract_latin1_txt(self):
        content = "Café au lait costs 5£ in Paris.".encode("latin-1")
        extracted = extract_text_from_txt(content)
        assert "Caf" in extracted

    def test_extract_empty_txt(self):
        assert extract_text_from_txt(b"") == ""


class TestDocumentExtraction:
    def test_extract_pdf(self):
        import fitz
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 72), "Albert Einstein developed the theory of relativity.")
        pdf_bytes = doc.tobytes()
        doc.close()

        extracted = extract_text_from_pdf(pdf_bytes)
        assert "Albert Einstein developed the theory of relativity" in extracted

    def test_extract_docx(self):
        import docx
        import io
        doc = docx.Document()
        doc.add_paragraph("Water boils at 100 degrees Celsius at standard atmospheric pressure.")
        buf = io.BytesIO()
        doc.save(buf)
        docx_bytes = buf.getvalue()

        extracted = extract_text_from_docx(docx_bytes)
        assert "Water boils at 100 degrees Celsius" in extracted

    def test_corrupt_pdf_raises(self):
        with pytest.raises(ExtractorError, match="Failed to parse PDF document"):
            extract_text_from_pdf(b"not a valid pdf content")
