from io import BytesIO
from zipfile import ZipFile

import pytest

from label_generator import (
    build_label_mappings,
    create_empty_labels_zip,
    generate_label_name,
    normalize_extension,
)


@pytest.mark.parametrize(
    ("image_name", "expected"),
    [
        ("bird.jpg", "bird.txt"),
        ("bird.final.v2.jpg", "bird.final.v2.txt"),
        ("BIRD.JPG", "BIRD.txt"),
        ("my bird image.jpg", "my bird image.txt"),
        ("پرنده.jpg", "پرنده.txt"),
    ],
)
def test_generate_label_name(image_name, expected):
    assert generate_label_name(image_name, ".txt") == expected


def test_custom_extension_is_normalized():
    assert normalize_extension("bbox") == ".bbox"


def test_zip_labels_are_exactly_empty_and_report_is_separate():
    mappings = build_label_mappings(["Birds/eagle.jpg", "Birds/owl.PNG"], ".txt")
    data = create_empty_labels_zip(mappings, include_report=True).getvalue()

    with ZipFile(BytesIO(data)) as archive:
        label_names = [name for name in archive.namelist() if name.endswith(".txt")]
        assert label_names == ["labels/eagle.txt", "labels/owl.txt"]
        assert all(len(archive.read(name)) == 0 for name in label_names)
        assert archive.read("labels/label_generation_report.csv")


def test_skip_duplicates_never_writes_a_colliding_entry():
    mappings = build_label_mappings(["bird.jpg", "bird.png", "owl.jpg"], ".txt")
    with ZipFile(create_empty_labels_zip(mappings)) as archive:
        assert archive.namelist() == ["labels/owl.txt"]


def test_report_cannot_duplicate_a_generated_zip_entry():
    mappings = build_label_mappings(["label_generation_report.jpg"], ".csv")
    with pytest.raises(ValueError, match="conflicts"):
        create_empty_labels_zip(mappings, include_report=True)


def test_preserved_structure_avoids_cross_folder_collision():
    mappings = build_label_mappings(
        ["birds/item.jpg", "planes/item.png"], ".txt", preserve_structure=True
    )
    assert [mapping.status for mapping in mappings] == ["Ready", "Ready"]
    with ZipFile(create_empty_labels_zip(mappings)) as archive:
        assert archive.namelist() == ["labels/birds/item.txt", "labels/planes/item.txt"]


def test_final_verification_scenario():
    files = [
        "Birds/eagle.jpg",
        "Birds/owl.PNG",
        "Birds/pigeon.final.v2.jpeg",
        "Birds/bird image 01.webp",
        "Birds/پرنده.jpg",
        "Birds/duplicate.jpg",
        "Birds/duplicate.png",
        "Birds/notes.pdf",
    ]
    mappings = build_label_mappings(files, ".txt", preserve_structure=False)
    statuses = {mapping.image_name: mapping.status for mapping in mappings}

    assert statuses["duplicate.jpg"] == statuses["duplicate.png"] == "Collision"
    assert statuses["notes.pdf"] == "Unsupported"
    with ZipFile(create_empty_labels_zip(mappings)) as archive:
        expected = {
            "labels/eagle.txt",
            "labels/owl.txt",
            "labels/pigeon.final.v2.txt",
            "labels/bird image 01.txt",
            "labels/پرنده.txt",
        }
        assert set(archive.namelist()) == expected
        assert all(archive.getinfo(name).file_size == 0 for name in expected)
