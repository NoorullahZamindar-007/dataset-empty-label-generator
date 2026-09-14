import pytest

from label_generator import build_label_mappings
from validators import is_supported_image, validate_extension, validate_filename


@pytest.mark.parametrize("name", ["bird.jpg", "owl.PNG", "x.JPEG", "photo.WEBP", "scan.TIFF"])
def test_supported_extensions_are_case_insensitive(name):
    assert is_supported_image(name)


@pytest.mark.parametrize("name", ["README.txt", "desktop.ini", "Thumbs.db", "notes.pdf", "archive.zip"])
def test_unrelated_files_are_unsupported(name):
    assert not is_supported_image(name)


def test_macos_appledouble_files_are_unsupported():
    assert not is_supported_image("photos/._AIRPLANE_000001.JPG")
    assert build_label_mappings(["photos/._AIRPLANE_000001.JPG"], ".txt")[0].status == "Unsupported"


def test_case_insensitive_collision_is_detected():
    mappings = build_label_mappings(["Bird01.jpg", "bird01.png"], ".txt")
    assert [mapping.status for mapping in mappings] == ["Collision", "Collision"]


@pytest.mark.parametrize("extension", ["./ann", ".a\\b", ".a:b", ".a*", '.a"', ".a<", ".a>", ".a|"])
def test_unsafe_extensions_are_rejected(extension):
    assert validate_extension(extension)[0] is False


@pytest.mark.parametrize("filename", ["bird image.jpg", "پرنده01.jpg", "طائر01.png", "image_001_final.v2.jpeg"])
def test_valid_unicode_and_complex_filenames(filename):
    assert validate_filename(filename)[0] is True


@pytest.mark.parametrize("filename", ["CON", "con.txt", "LPT1.jpg", "aux.anything.png"])
def test_windows_reserved_filenames_are_rejected(filename):
    assert validate_filename(filename)[0] is False
