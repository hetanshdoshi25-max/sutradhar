"""
SUTRADHAR - Visual identity matching (perceptual hashing)
------------------------------------------------------------
An avatar / profile image is another reusable identifier. Operators often
carry the SAME picture (or a lightly cropped / recolored / resized version
of it) across different aliases and sites. This module fingerprints an
image with a perceptual hash (pHash-style) and matches images that are
perceptually the same even when they are not byte-identical - so a resized
or re-compressed avatar still matches its original.

Legal / ethical scope: this operates on images the operator themselves
published (persona avatars, posted pictures). It is NOT facial recognition
against live camera feeds or any external face database - it only compares
images already inside the investigation set against one another.

No heavy models, no third-party CV libs beyond Pillow. The hash is a 64-bit
signature; two images match when their Hamming distance is small.
"""

import hashlib
from PIL import Image


HASH_SIZE = 8  # 8x8 = 64-bit signature


def phash(path_or_img):
    """Perceptual hash: shrink to 8x8 greyscale, threshold on the mean.
    Returns a 64-bit integer signature that survives resize/recompress."""
    img = path_or_img if isinstance(path_or_img, Image.Image) else Image.open(path_or_img)
    img = img.convert("L").resize((HASH_SIZE, HASH_SIZE), Image.LANCZOS)
    pixels = list(img.getdata())
    avg = sum(pixels) / len(pixels)
    bits = 0
    for i, p in enumerate(pixels):
        if p >= avg:
            bits |= (1 << i)
    return bits


def phash_bytes(data):
    """pHash from raw image bytes (e.g. an upload)."""
    from io import BytesIO
    return phash(Image.open(BytesIO(data)))


def hamming(a, b):
    """Number of differing bits between two 64-bit hashes (0 = identical)."""
    return bin(a ^ b).count("1")


def similarity(a, b):
    """0..1 perceptual similarity from two hashes (1.0 = identical)."""
    return 1.0 - hamming(a, b) / 64.0


def image_link(hash_a, hash_b, threshold=0.88):
    """Decide if two image hashes are the same picture. Returns (score, matched)."""
    if hash_a is None or hash_b is None:
        return 0.0, False
    s = similarity(hash_a, hash_b)
    return round(s, 3), s >= threshold


if __name__ == "__main__":
    # self-test: same image resized should still match; different image should not
    base = Image.new("L", (200, 200))
    for x in range(200):
        for y in range(200):
            base.putpixel((x, y), (x * 3 + y) % 256)
    resized = base.resize((90, 90)).resize((150, 150))
    other = Image.new("L", (200, 200), 128)

    h1, h2, h3 = phash(base), phash(resized), phash(other)
    print("same image, resized :", similarity(h1, h2), "->", image_link(h1, h2))
    print("different image      :", similarity(h1, h3), "->", image_link(h1, h3))
