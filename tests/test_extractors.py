"""Tests de extracción de texto de documentos (sin red, bytes en memoria)."""

import io
from types import SimpleNamespace

import pytest

from app.modules.gap_analysis import extractors


def _upload(filename: str, data: bytes):
    return SimpleNamespace(filename=filename, file=io.BytesIO(data))


def test_extract_txt_ok():
    text = "Python developer con experiencia en FastAPI y SQLAlchemy. " * 2
    assert extractors.extract_text(_upload("cv.txt", text.encode())) == text.strip()


def test_extract_unsupported_extension():
    with pytest.raises(extractors.UnsupportedDocumentError):
        extractors.extract_text(_upload("cv.xlsx", b"x" * 100))


def test_extract_too_large():
    big = b"a" * (extractors.MAX_BYTES + 1)
    with pytest.raises(extractors.DocumentTooLargeError):
        extractors.extract_text(_upload("cv.txt", big))


def test_extract_too_short():
    with pytest.raises(extractors.EmptyDocumentError):
        extractors.extract_text(_upload("cv.txt", b"corto"))


def test_extract_pdf_invalid_bytes():
    with pytest.raises(extractors.EmptyDocumentError):
        extractors.extract_text(_upload("cv.pdf", b"no soy un pdf" * 10))


def test_parse_txt_decodes_replacing_errors():
    assert extractors._parse_txt(b"hola \xff mundo").startswith("hola")
