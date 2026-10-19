"""Logo drawing and the bar's alpha conversion (pure image code)."""

import numpy as np
import pytest
from PIL import Image

from chit.icon import app_icon


@pytest.mark.parametrize("size", [16, 32, 256])
@pytest.mark.parametrize("theme", ["light", "dark"])
def test_app_icon_sizes_and_transparent_corners(size, theme):
    img = app_icon(size, theme)
    assert img.size == (size, size) and img.mode == "RGBA"
    assert img.getpixel((0, 0))[3] == 0  # rounded-tile corner is transparent
    assert img.getpixel((size // 2, size // 2))[3] == 255


def test_listening_icon_differs():
    assert app_icon(64, "dark").tobytes() != app_icon(64, "dark", listening=True).tobytes()


def test_premultiplied_bgra():
    overlay = pytest.importorskip("chit.overlay")
    img = Image.new("RGBA", (2, 1))
    img.putpixel((0, 0), (200, 100, 50, 255))
    img.putpixel((1, 0), (200, 100, 50, 128))
    out = overlay.premultiplied_bgra(img)
    assert out.shape == (1, 2, 4) and out.dtype == np.uint8
    assert tuple(out[0, 0]) == (50, 100, 200, 255)  # BGRA order
    assert tuple(out[0, 1]) == (25, 50, 100, 128)  # colour scaled by alpha
