"""Atomic document writes for every ePy editor.

The three editors used to share an identical save line that wrote
directly into the document's final path. A process that died mid-write
-- or an autosave timer killed while the machine is under load -- left
the document truncated on disk, and the truncated file was the only
copy. This module stages a complete temporary sibling and then renames
it over the destination, so the destination is either the previous
complete document or the new complete document, never a partial one.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def write_text_atomic(
    path: Path, text: str, *, encoding: str = "utf-8"
) -> None:
    """Write *text* to *path* atomically.

    The text is first written to a unique temporary file in the same
    directory as *path*, then ``os.replace`` swaps it into place. A
    failure before the swap leaves the original file untouched and the
    temporary file removed.

    Args:
        path: Destination path of the document.
        text: Complete document text to write.
        encoding: Text encoding to use for the temporary file.

    Raises:
        OSError: If the parent directory does not exist, the temporary
            file cannot be created, or the final replacement fails.
    """
    temp_path: Path | None = None
    try:
        # delete=False keeps the temp name assigned by
        # NamedTemporaryFile; dir=path.parent puts it on the same
        # filesystem so os.replace is atomic.
        with tempfile.NamedTemporaryFile(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
            mode="w",
            encoding=encoding,
            newline="",
        ) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(text)
        os.replace(temp_path, path)
    except BaseException:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise
