"""WebcamEnumerator — probe local device indices and fingerprint by device name.

On Windows, uses WMI (via wmic.exe) to obtain the friendly device name.
Falls back to "Webcam {index}" on error or non-Windows platforms.
"""

from __future__ import annotations

import concurrent.futures
import logging
import subprocess
import sys
from dataclasses import dataclass

import cv2

logger = logging.getLogger(__name__)

# DSHOW is significantly faster on Windows for probing — CAP_ANY tries multiple
# backends sequentially and has ~1-2s timeout per missing index.
_WEBCAM_BACKEND = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY
_MAX_INDEX = 9


# ── Device name resolution ────────────────────────────────────────────────────

def _wmic_device_names() -> list[str]:
    """Return ordered list of video-capture device friendly names from WMI.

    Runs ``wmic path Win32_PnPEntity where "PNPClass='Camera'" get Name``
    and parses the output.  Returns an empty list on any error.
    """
    if sys.platform != "win32":
        return []
    try:
        result = subprocess.run(
            [
                "wmic",
                "path", "Win32_PnPEntity",
                "where", "PNPClass='Camera'",
                "get", "Name",
            ],
            capture_output=True, text=True, timeout=5,
        )
        lines = [
            ln.strip() for ln in result.stdout.splitlines()
            if ln.strip() and ln.strip().lower() != "name"
        ]
        return lines
    except Exception as exc:
        logger.debug("WMI query failed: %s", exc)
        return []


def _device_name_for_index(index: int, wmic_names: list[str]) -> str:
    """Map a cv2 device index to a WMI friendly name.

    WMI returns names in the same enumeration order as DirectShow, so
    index 0 → wmic_names[0], index 1 → wmic_names[1], etc.
    """
    if index < len(wmic_names):
        return wmic_names[index]
    return f"Webcam {index}"


# ── Public interface ──────────────────────────────────────────────────────────

@dataclass
class EnumeratedDevice:
    index: int
    label: str           # human-readable (same as device_name)
    device_name: str     # fingerprint key — matches WMI friendly name


def _probe_index(i: int) -> bool:
    """Open and immediately release a capture to test if index exists."""
    cap = cv2.VideoCapture(i, _WEBCAM_BACKEND)
    opened = cap.isOpened()
    cap.release()
    return opened


def enumerate_webcams(
    max_index: int = _MAX_INDEX,
    skip_indices: set[int] | None = None,
) -> list[EnumeratedDevice]:
    """Probe device indices 0‥max_index and return available webcams.

    Probes all indices in parallel (ThreadPoolExecutor) so total time is
    bounded by the slowest single probe rather than the sum.

    ``skip_indices`` — device indices to exclude from probing.  Pass the set
    of indices currently held by active CameraThreads so the probe never opens
    a DirectShow device that is already streaming (doing so can corrupt the
    active capture on Windows).

    Each returned device includes:
    - ``index``       — current cv2 device index
    - ``label``       — same as device_name (for UI display)
    - ``device_name`` — stable fingerprint from WMI / fallback string
    """
    wmic_names = _wmic_device_names()
    skip = skip_indices or set()
    indices = [i for i in range(max_index + 1) if i not in skip]

    if not indices:
        return []

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(indices)) as ex:
        opened_flags = list(ex.map(_probe_index, indices))

    found: list[EnumeratedDevice] = []
    for i, opened in zip(indices, opened_flags):
        if opened:
            name = _device_name_for_index(i, wmic_names)
            found.append(EnumeratedDevice(index=i, label=name, device_name=name))
            logger.debug("Webcam found: index=%d name=%r", i, name)

    return found


def find_index_by_name(device_name: str, max_index: int = _MAX_INDEX) -> int | None:
    """Scan indices and return the current index for a device with the given name.

    Returns ``None`` if the device is not found (disconnected or name changed).
    Used by WebcamWatcher to remap indices after a reconnect.
    """
    wmic_names = _wmic_device_names()
    indices = list(range(max_index + 1))

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(indices)) as ex:
        opened_flags = list(ex.map(_probe_index, indices))

    for i, opened in zip(indices, opened_flags):
        if opened and _device_name_for_index(i, wmic_names) == device_name:
            return i
    return None
