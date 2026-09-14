"""Reusable business logic for generating zero-byte dataset labels."""

from __future__ import annotations

import csv
from dataclasses import dataclass, replace
from io import BytesIO, StringIO
from pathlib import Path, PurePosixPath
from typing import Iterable
from zipfile import ZIP_DEFLATED, ZipFile

from validators import (
    detect_collisions,
    is_supported_image,
    validate_extension,
    validate_relative_path,
)


@dataclass(frozen=True, slots=True)
class LabelMapping:
    """One uploaded file and its prospective label output."""

    source_path: PurePosixPath
    image_name: str
    image_extension: str
    relative_folder: PurePosixPath
    label_name: str
    label_path: PurePosixPath
    status: str
    detail: str = ""


def normalize_extension(extension: str) -> str:
    """Trim and prefix a custom label extension, then validate it."""

    normalized = extension.strip()
    if normalized and not normalized.startswith("."):
        normalized = f".{normalized}"
    valid, reason = validate_extension(normalized)
    if not valid:
        raise ValueError(reason)
    return normalized


def generate_label_name(image_name: str | Path, label_extension: str) -> str:
    """Replace only the final suffix of an image filename."""

    extension = normalize_extension(label_extension)
    return f"{Path(str(image_name)).stem}{extension}"


def normalize_uploaded_paths(paths: Iterable[str | Path]) -> list[PurePosixPath]:
    """Convert browser paths to portable relative paths and remove a common root."""

    normalized = [PurePosixPath(str(path).replace("\\", "/")) for path in paths]
    if normalized and all(len(path.parts) > 1 for path in normalized):
        first = normalized[0].parts[0]
        if all(path.parts[0].casefold() == first.casefold() for path in normalized):
            normalized = [PurePosixPath(*path.parts[1:]) for path in normalized]
    return normalized


def build_label_mappings(
    file_paths: Iterable[str | Path],
    label_extension: str,
    *,
    include_subfolders: bool = True,
    preserve_structure: bool = True,
) -> list[LabelMapping]:
    """Build and validate image-to-label mappings without reading file bytes."""

    extension = normalize_extension(label_extension)
    mappings: list[LabelMapping] = []

    for source in normalize_uploaded_paths(file_paths):
        if not include_subfolders and source.parent != PurePosixPath("."):
            continue

        valid_path, reason = validate_relative_path(source)
        supported = is_supported_image(source)
        folder = source.parent
        label_name = generate_label_name(source.name, extension) if supported else ""
        output_folder = folder if preserve_structure else PurePosixPath(".")
        label_path = output_folder / label_name if label_name else PurePosixPath(".")

        if not valid_path:
            status, detail = "Invalid", reason
        elif not supported:
            status, detail = "Unsupported", "Unsupported file extension"
        else:
            status, detail = "Ready", ""

        mappings.append(
            LabelMapping(
                source_path=source,
                image_name=source.name,
                image_extension=source.suffix.lower(),
                relative_folder=folder,
                label_name=label_name,
                label_path=label_path,
                status=status,
                detail=detail,
            )
        )

    candidates = [mapping for mapping in mappings if mapping.status == "Ready"]
    collided_ids = {
        id(mapping)
        for group in detect_collisions(candidates).values()
        for mapping in group
    }
    return [
        replace(mapping, status="Collision", detail="Multiple images map to this label")
        if id(mapping) in collided_ids
        else mapping
        for mapping in mappings
    ]


def _select_for_generation(
    mappings: list[LabelMapping], collision_strategy: str
) -> tuple[list[LabelMapping], dict[PurePosixPath, str]]:
    eligible = [mapping for mapping in mappings if mapping.status in {"Ready", "Collision"}]
    collisions = detect_collisions(eligible)
    collided = {id(item) for group in collisions.values() for item in group}
    selected = [mapping for mapping in eligible if id(mapping) not in collided]
    outcomes = {mapping.source_path: "Created" for mapping in selected}

    if collision_strategy == "keep_first":
        for group in collisions.values():
            selected.append(group[0])
            outcomes[group[0].source_path] = "Created (kept first)"
            outcomes.update(
                {item.source_path: "Skipped collision" for item in group[1:]}
            )
    elif collision_strategy == "skip_duplicates":
        for group in collisions.values():
            outcomes.update({item.source_path: "Skipped collision" for item in group})
    elif collision_strategy == "cancel" and collisions:
        raise ValueError("Generation cancelled because filename collisions exist.")
    elif collision_strategy not in {"skip_duplicates", "keep_first", "cancel"}:
        raise ValueError(f"Unknown collision strategy: {collision_strategy}")

    return selected, outcomes


def create_empty_labels_zip(
    mappings: Iterable[LabelMapping],
    *,
    collision_strategy: str = "skip_duplicates",
    include_report: bool = False,
) -> BytesIO:
    """Create an in-memory ZIP whose generated label entries are all zero bytes."""

    mapping_list = list(mappings)
    selected, outcomes = _select_for_generation(mapping_list, collision_strategy)
    seen: set[str] = set()
    buffer = BytesIO()

    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        for mapping in selected:
            archive_path = (PurePosixPath("labels") / mapping.label_path).as_posix()
            collision_key = archive_path.casefold()
            if collision_key in seen:
                raise ValueError(f"Unsafe duplicate ZIP entry blocked: {archive_path}")
            seen.add(collision_key)
            archive.writestr(archive_path, b"")

        if include_report:
            report_path = "labels/label_generation_report.csv"
            if report_path.casefold() in seen:
                raise ValueError(
                    "A generated label conflicts with label_generation_report.csv. "
                    "Disable the report or choose another label extension."
                )
            report = StringIO(newline="")
            writer = csv.writer(report, lineterminator="\n")
            writer.writerow(
                ["image_name", "image_extension", "relative_path", "label_name", "status"]
            )
            for mapping in mapping_list:
                writer.writerow(
                    [
                        mapping.image_name,
                        mapping.image_extension,
                        mapping.source_path.as_posix(),
                        mapping.label_path.as_posix() if mapping.label_name else "",
                        outcomes.get(mapping.source_path, mapping.status),
                    ]
                )
            archive.writestr(report_path, report.getvalue().encode("utf-8-sig"))

    buffer.seek(0)
    return buffer


def summarize_mappings(mappings: Iterable[LabelMapping]) -> dict[str, int]:
    """Compute dashboard statistics from a mapping collection."""

    items = list(mappings)
    supported = [item for item in items if item.image_extension and is_supported_image(item.image_name)]
    collision_groups = detect_collisions(
        item for item in items if item.status in {"Ready", "Collision"}
    )
    return {
        "total_files": len(items),
        "images_found": len(supported),
        "supported_images": len(supported),
        "unsupported_files": sum(item.status == "Unsupported" for item in items),
        "labels_to_create": sum(item.status == "Ready" for item in items),
        "duplicate_base_names": len(collision_groups),
        "filename_collisions": sum(len(group) for group in collision_groups.values()),
        "invalid_filenames": sum(item.status == "Invalid" for item in items),
        "subfolders_detected": len(
            {item.relative_folder.as_posix() for item in items if item.relative_folder != PurePosixPath(".")}
        ),
    }
