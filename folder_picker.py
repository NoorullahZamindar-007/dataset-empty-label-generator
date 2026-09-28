"""Browser-side folder picker that sends paths, never file contents, to Python."""

from __future__ import annotations

from collections.abc import Sequence

import streamlit as st


_FOLDER_PICKER = st.components.v2.component(
    "metadata_folder_picker",
    html="""
<div class="picker">
  <input id="folder-input" type="file" webkitdirectory directory multiple />
  <button id="choose" type="button">Choose image folder</button>
  <button id="clear" type="button" class="secondary">Clear</button>
  <span id="status" role="status" aria-live="polite">No folder selected</span>
</div>
""",
    css="""
.picker {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
  min-height: 2.8rem;
}
#folder-input { display: none; }
button {
  background: var(--st-primary-color);
  border: 1px solid var(--st-primary-color);
  border-radius: var(--st-button-border-radius, 0.5rem);
  color: white;
  cursor: pointer;
  font: inherit;
  font-weight: 600;
  padding: 0.55rem 0.9rem;
}
button.secondary {
  background: transparent;
  border-color: var(--st-border-color);
  color: var(--st-text-color);
}
button:focus-visible { outline: 2px solid var(--st-primary-color); outline-offset: 2px; }
#status { color: var(--st-text-color); font-size: 0.9rem; }
""",
    js="""
export default function(component) {
  const { data, parentElement, setStateValue } = component
  const input = parentElement.querySelector("#folder-input")
  const choose = parentElement.querySelector("#choose")
  const clear = parentElement.querySelector("#clear")
  const status = parentElement.querySelector("#status")
  if (!input || !choose || !clear || !status) return

  const count = Number(data?.count ?? 0)
  status.textContent = count
    ? `${count.toLocaleString()} file paths selected — image bytes were not uploaded`
    : "No folder selected"

  choose.onclick = () => {
    input.value = ""
    input.click()
  }
  clear.onclick = () => {
    input.value = ""
    setStateValue("paths", [])
  }
  input.onchange = () => {
    const paths = Array.from(input.files ?? [], file => file.webkitRelativePath || file.name)
    status.textContent = `${paths.length.toLocaleString()} paths found — preparing preview...`
    setStateValue("paths", paths)
  }
}
""",
)


def metadata_folder_picker(*, key: str) -> list[str]:
    """Return browser-selected relative paths without uploading file bytes."""

    state = st.session_state.get(key, {})
    current: Sequence[str] = state.get("paths", []) if hasattr(state, "get") else []
    result = _FOLDER_PICKER(
        key=key,
        data={"count": len(current)},
        on_paths_change=lambda: None,
        height=54,
    )
    paths = getattr(result, "paths", None)
    return list(paths if paths is not None else current)
