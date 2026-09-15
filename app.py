"""Streamlit UI for Dataset Empty Label Generator."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from label_generator import (
    build_label_mappings,
    create_empty_labels_zip,
    normalize_extension,
    summarize_mappings,
)
LABEL_EXTENSIONS = [".txt", ".csv", ".json", ".jsonl", ".xml", ".yaml", ".yml", ".label", "Custom"] 
COLLISION_OPTIONS = { 
    "Skip duplicates": "skip_duplicates",
    "Keep first file": "keep_first",
    "Preserve directory structure": "preserve_structure",
    "Cancel generation": "cancel",
}

st.set_page_config(
    page_title="Dataset Empty Label Generator",
    page_icon=":material/note_add:",
    layout="wide",
)
st.session_state.setdefault("labels_zip", None)
st.session_state.setdefault("generated_signature", None)

st.title("Dataset Empty Label Generator", icon=":material/note_add:")
st.caption("Create safe, zero-byte annotation files from an image dataset — entirely in your browser session.")

with st.container(border=True):
    uploaded_files = st.file_uploader(
        "Select or drop an image folder",
        accept_multiple_files="directory",
        help="The browser supplies filenames and relative paths. Image contents are never decoded or copied into the ZIP.",
        key="dataset_folder",
    )
    st.caption("Your source files are treated as read-only. Only an in-memory labels ZIP is created.")

generator_tab, preview_tab, issues_tab, help_tab = st.tabs(
    [
        ":material/tune: Generator",
        ":material/table_view: Preview",
        ":material/warning: Issues",
        ":material/help: Help",
    ]
)

with generator_tab:
    st.subheader("Configuration")
    config_left, config_middle, config_right = st.columns(3, vertical_alignment="bottom")
    with config_left:
        selected_extension = st.selectbox("Label extension", LABEL_EXTENSIONS, key="label_extension")
        custom_extension = (
            st.text_input("Custom extension", placeholder=".ann or bbox", key="custom_extension")
            if selected_extension == "Custom"
            else ""
        )
    with config_middle:
        include_subfolders = st.toggle("Include subfolders", value=True, key="include_subfolders")
        preserve_structure = st.toggle(
            "Preserve folder structure",
            value=True,
            disabled=not include_subfolders,
            key="preserve_structure",
        )
    with config_right:
        include_report = st.toggle("Include generation report", key="include_report")
        collision_choice = st.selectbox(
            "Collision handling",
            list(COLLISION_OPTIONS),
            help="Skip duplicates is safest and creates no label for a colliding group.",
            key="collision_handling",
        )

extension_input = custom_extension if selected_extension == "Custom" else selected_extension
extension_error = ""
try:
    normalized_extension = normalize_extension(extension_input)
except ValueError as exc:
    normalized_extension = ""
    extension_error = str(exc)

effective_preserve = preserve_structure or collision_choice == "Preserve directory structure"
paths = [uploaded.name for uploaded in uploaded_files]
if uploaded_files and normalized_extension:
    with generator_tab:
        with st.spinner("Scanning dataset...", show_time=True):
            mappings = build_label_mappings(
                paths,
                normalized_extension,
                include_subfolders=include_subfolders,
                preserve_structure=effective_preserve,
            )
else:
    mappings = []
stats = summarize_mappings(mappings)

rows = [
    {
        "No.": number,
        "Image Name": mapping.image_name,
        "Image Extension": mapping.image_extension,
        "Relative Folder": "Root" if mapping.relative_folder.as_posix() == "." else mapping.relative_folder.as_posix(),
        "Generated Label": mapping.label_path.as_posix() if mapping.label_name else "—",
        "Status": mapping.status,
    }
    for number, mapping in enumerate(mappings, start=1)
]
preview_df = pd.DataFrame(
    rows,
    columns=["No.", "Image Name", "Image Extension", "Relative Folder", "Generated Label", "Status"],
)

with generator_tab:
    if extension_error:
        st.error(extension_error, icon=":material/error:")

    st.subheader("Dataset summary")
    metric_labels = [
        ("Total files scanned", "total_files"),
        ("Images found", "images_found"),
        ("Supported images", "supported_images"),
        ("Unsupported files", "unsupported_files"),
        ("Labels to create", "labels_to_create"),
        ("Duplicate base names", "duplicate_base_names"),
        ("Filename collisions", "filename_collisions"),
        ("Invalid filenames", "invalid_filenames"),
        ("Subfolders detected", "subfolders_detected"),
    ]
    for start in range(0, len(metric_labels), 3):
        for column, (label, key) in zip(st.columns(3), metric_labels[start : start + 3]):
            column.metric(label, f"{stats[key]:,}", border=True)

    collision_strategy = COLLISION_OPTIONS[collision_choice]
    if collision_strategy == "preserve_structure":
        collision_strategy = "skip_duplicates"

    if not uploaded_files:
        st.info("Select a folder to scan its files and build the preview.", icon=":material/folder_open:")
    elif not mappings:
        st.warning("No files remain after applying the subfolder setting.", icon=":material/warning:")
    elif stats["supported_images"] == 0:
        st.warning("No supported images were found in this folder.", icon=":material/image_not_supported:")
    elif stats["filename_collisions"]:
        st.warning(
            f"{stats['filename_collisions']} images are involved in filename collisions. "
            f"Current handling: {collision_choice}.",
            icon=":material/warning:",
        )

    signature = (
        tuple(paths),
        normalized_extension,
        include_subfolders,
        effective_preserve,
        include_report,
        collision_strategy,
    )
    can_generate = bool(mappings and stats["supported_images"] and normalized_extension)
    if st.button(
        "Generate empty labels",
        type="primary",
        icon=":material/archive:",
        disabled=not can_generate,
        key="generate_labels",
    ):
        progress = st.progress(10, text="Validating mappings...")
        try:
            progress.progress(45, text="Generating zero-byte labels...")
            labels_zip = create_empty_labels_zip(
                mappings,
                collision_strategy=collision_strategy,
                include_report=include_report,
            )
            progress.progress(90, text="Creating labels.zip...")
            st.session_state.labels_zip = labels_zip.getvalue()
            st.session_state.generated_signature = signature
            progress.progress(100, text="labels.zip is ready.")
            st.success("Generation complete. Your source files were not changed.", icon=":material/check_circle:")
        except (OSError, ValueError) as exc:
            st.session_state.labels_zip = None
            st.session_state.generated_signature = None
            progress.empty()
            st.error(f"ZIP generation failed: {exc}", icon=":material/error:")

    if st.session_state.labels_zip and st.session_state.generated_signature == signature:
        st.download_button(
            "Download labels.zip",
            data=st.session_state.labels_zip,
            file_name="labels.zip",
            mime="application/zip",
            icon=":material/download:",
            type="primary",
            key="download_labels",
        )
    elif st.session_state.labels_zip:
        st.caption("Configuration changed. Generate again to refresh the ZIP.")

with preview_tab:
    st.subheader("Image to label mapping")
    search_col, filter_col = st.columns([2, 1], vertical_alignment="bottom")
    search = search_col.text_input(
        "Search",
        placeholder="Filename, extension, folder, label, or status",
        key="preview_search",
    )
    status_filter = filter_col.segmented_control(
        "Status",
        ["All", "Ready", "Collision", "Invalid", "Unsupported"],
        default="All",
        key="preview_status",
    )
    filtered_df = preview_df
    if status_filter and status_filter != "All":
        filtered_df = filtered_df[filtered_df["Status"] == status_filter]
    if search.strip() and not filtered_df.empty:
        mask = filtered_df.astype(str).apply(
            lambda column: column.str.contains(search.strip(), case=False, regex=False)
        ).any(axis=1)
        filtered_df = filtered_df[mask]
    if preview_df.empty:
        st.info("Upload a folder to see the complete mapping preview.", icon=":material/table_view:")
    else:
        st.caption(f"Showing {len(filtered_df):,} of {len(preview_df):,} scanned files.")
        st.dataframe(filtered_df, hide_index=True, height=520, key="mapping_preview")

with issues_tab:
    st.subheader("Dataset issues")
    issues = [mapping for mapping in mappings if mapping.status != "Ready"]
    if not uploaded_files:
        st.info("Upload a folder to inspect collisions and unsupported files.", icon=":material/folder_open:")
    elif not issues:
        st.success("No collisions, invalid filenames, or unsupported files detected.", icon=":material/check_circle:")
    else:
        collisions = [mapping for mapping in issues if mapping.status == "Collision"]
        unsupported = [mapping for mapping in issues if mapping.status == "Unsupported"]
        invalid = [mapping for mapping in issues if mapping.status == "Invalid"]
        if collisions:
            st.error("Filename collision detected", icon=":material/error:")
            collision_df = pd.DataFrame(
                {
                    "Image": [item.source_path.as_posix() for item in collisions],
                    "Maps to": [item.label_path.as_posix() for item in collisions],
                }
            )
            st.dataframe(collision_df, hide_index=True)
        if unsupported:
            with st.expander(f"Unsupported files ({len(unsupported):,})", icon=":material/block:"):
                st.dataframe(
                    pd.DataFrame({"File": [item.source_path.as_posix() for item in unsupported]}),
                    hide_index=True,
                )
        if invalid:
            with st.expander(f"Invalid filenames ({len(invalid):,})", icon=":material/error:"):
                st.dataframe(
                    pd.DataFrame(
                        {"File": [item.source_path.as_posix() for item in invalid], "Reason": [item.detail for item in invalid]}
                    ),
                    hide_index=True,
                )

with help_tab:
    st.subheader("How it works")
    st.markdown(
        """
This app reads only the uploaded filenames and relative paths, replaces each supported image's final extension,
and packages empty label files under `labels/`. Image bytes are not decoded, copied, edited, moved, or deleted.

- **Why empty?** Empty annotation files are useful placeholders for images that currently have no objects or annotations.
- **Supported images:** `.jpg`, `.jpeg`, `.png`, `.webp`, `.bmp`, `.tif`, `.tiff`, and `.gif` (case-insensitive).
- **Label formats:** The selected extension changes only the filename. Even `.csv`, `.json`, and `.xml` labels contain exactly 0 bytes.
- **Collisions:** Names are compared case-insensitively for Windows safety. Skip duplicates is the default; keeping the first is deterministic; preserving folders can resolve same-name images in different folders.
- **Large datasets:** Browsers and Streamlit enforce upload limits per file. The app avoids reading image content, but the browser still performs the directory upload.
"""
    )
    st.code("my.image.001.jpg  →  labels/my.image.001.txt", language="text")
    st.caption("No source-folder write access is used by this application.")
