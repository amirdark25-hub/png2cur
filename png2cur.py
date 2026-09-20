import argparse
import struct
from PIL import Image



def load_and_prepare(png_path, size, crop=None):
    """PNG ro mikune RGBA, crop mikune, va too canvas size x size mizarad."""
    img = Image.open(png_path).convert("RGBA")
    if crop:
        img = img.crop(crop)   # (left, top, right, bottom)
    img.thumbnail((size, size), Image.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.paste(img, (0, 0))
    return canvas


def build_cur_bytes(img, hotspot_x, hotspot_y):
    w, h = img.size
    pixels = list(img.getdata())                # list az (r, g, b, a)

    # 1) Header (6 bytes): reserved, type=2 (cur), count=1
    header = struct.pack("<HHH", 0, 2, 1)

    # 2) Andaze and-mask (1 bit per pixel)
    mask_row_bytes = ((w + 31) // 32) * 4
    xor_size = w * h * 4
    mask_size = mask_row_bytes * h
    image_data_size = 40 + xor_size + mask_size

    # 3) Directory entry (16 bytes) — hotspot X va Y inja zakhire mishan
    entry = struct.pack(
        "<BBBBHHII",
        w % 256, h % 256,   # width/height (256 mishe 0)
        0, 0,               # reserved colors, reserved
        hotspot_x, hotspot_y,  # HHHOTSPOT!
        image_data_size, 22,
    )

    # 4) BITMAPINFOHEADER (40 bytes) — ghoble in, h=2x
    bmp_header = struct.pack("<IiiHHIIiiII",
                             40, w, h * 2, 1, 32,
                             0, xor_size, 0, 0, 0, 0)

    # 5) XOR data — BGRA, az payin be bala (bottom-up)
    xor_data = bytearray()
    for y in range(h - 1, -1, -1):
        for x in range(w):
            r, g, b, a = pixels[y * w + x]
            xor_data += struct.pack("<BBBB", b, g, r, a)

    # 6) AND mask — bit=1 yani transparent
    mask = bytearray()
    for y in range(h - 1, -1, -1):
        row = bytearray(mask_row_bytes)
        for x in range(w):
            a = pixels[y * w + x][3]
            if a == 0:
                row[x // 8] |= 1 << (7 - x % 8)
        mask += row

    return header + entry + bmp_header + bytes(xor_data) + bytes(mask)


def main():
    parser = argparse.ArgumentParser(description="PNG → CUR converter")
    parser.add_argument("input")
    parser.add_argument("output")
    parser.add_argument("--size", type=int, default=32, help="cursor size (default 32)")
    parser.add_argument("--hotspot", type=int, nargs=2, default=[0, 0],
                        metavar=("X", "Y"), help="hotspot (default 0 0)")
    parser.add_argument("--crop", type=int, nargs=4, metavar=("L", "T", "R", "B"),
                        default=None, help="crop box: left top right bottom")
    args = parser.parse_args()

    hx, hy = args.hotspot
    if not (0 <= hx < args.size and 0 <= hy < args.size):
        parser.error("hotspot must be inside cursor size")

    img = load_and_prepare(args.input, args.size, args.crop)
    cur_bytes = build_cur_bytes(img, hx, hy)

    with open(args.output, "wb") as f:
        f.write(cur_bytes)

    print(f"OK: {args.output} ({args.size}x{args.size}, hotspot {hx},{hy})")


if __name__ == "__main__":
    main()
