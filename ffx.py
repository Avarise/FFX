#!/usr/bin/env python3
import sys
import yaml
import subprocess
import shlex
from pathlib import Path

###############################################################################
#  Utility
###############################################################################

def load_config(config_path: Path):
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")
    with config_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def add_filter(filters, frag):
    if not frag:
        return
    frag = frag.strip().rstrip(",")
    if frag:
        filters.append(frag)

###############################################################################
#  Filter Builders
###############################################################################

def build_eq(cfg):
    c = cfg.get("eq", {})
    if not c.get("enabled", False):
        return None

    return (
        "eq="
        f"brightness={c.get('brightness', 0.0)}:"
        f"contrast={c.get('contrast', 1.0)}:"
        f"gamma={c.get('gamma', 1.0)}:"
        f"saturation={c.get('saturation', 1.0)}"
    )


def build_unsharp(cfg):
    c = cfg.get("sharpen", {})
    if not c.get("enabled", False):
        return None

    m = c.get("main", {})
    return (
        "unsharp="
        f"{m.get('msize_x', 5)}:{m.get('msize_y', 5)}:{m.get('amount', 0.6)}:"
        f"{m.get('msize_x_chroma', 5)}:{m.get('msize_y_chroma', 5)}:{m.get('amount_chroma', 0.1)}"
    )


def build_extra_sharpen(cfg):
    c = cfg.get("sharpen", {})
    if not c.get("extra_enabled", False):
        return None

    e = c.get("extra", {})
    return (
        "unsharp="
        f"{e.get('msize', 3)}:{e.get('msize', 3)}:{e.get('amount', 0.4)}"
    )


def build_deblur(cfg):
    c = cfg.get("deblur", {})
    if not c.get("enabled", False):
        return None

    method = c.get("method", "convolution")

    if method == "convolution":
        # Typical deblurring kernel
        k = c.get("kernel", "-1 -1 -1 -1 9 -1 -1 -1 -1")
        return f"convolution='{k}'"

    if method == "unsharp_multi":
        # multi-pass unsharp
        passes = c.get("passes", 2)
        amount = c.get("amount", 1.0)
        msize = c.get("msize", 5)
        chain = []
        for _ in range(passes):
            chain.append(f"unsharp={msize}:{msize}:{amount}")
        return ",".join(chain)

    return None


def build_denoise(cfg):
    c = cfg.get("denoise", {})
    if not c.get("enabled", False):
        return None

    return (
        "hqdn3d="
        f"{c.get('luma', 2.0)}:"
        f"{c.get('chroma', 1.5)}:"
        f"{c.get('time', 3.0)}:"
        f"{c.get('chroma_time', 0.0)}"
    )


def build_blur(cfg):
    c = cfg.get("blur", {})
    if not c.get("enabled", False):
        return None

    r = c.get("radius", 2)
    return f"boxblur={r}"


def build_grain(cfg):
    c = cfg.get("grain", {})
    if not c.get("enabled", False):
        return None
    return f"noise=alls={c.get('strength', 4)}:allf={c.get('frequency', 'p')}"


def build_color_channel(cfg):
    cc = cfg.get("color_channels", {})
    r = cc.get("red", 1.0)
    g = cc.get("green", 1.0)
    b = cc.get("blue", 1.0)

    if (r, g, b) == (1.0, 1.0, 1.0):
        return None

    return f"eq=red_mul={r}:green_mul={g}:blue_mul={b}"


def build_custom(cfg):
    c = cfg.get("custom_filters", [])
    if not c:
        return None
    return ",".join(c)


###############################################################################
#  Main
###############################################################################

def main():
    if len(sys.argv) != 3:
        print("Usage: ffx.py <input> <output>")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    config_path = Path(__file__).with_name("ffx.yaml")
    cfg = load_config(config_path)

    filters = []

    add_filter(filters, build_eq(cfg))
    add_filter(filters, build_color_channel(cfg))
    add_filter(filters, build_unsharp(cfg))
    add_filter(filters, build_extra_sharpen(cfg))
    add_filter(filters, build_deblur(cfg))
    add_filter(filters, build_denoise(cfg))
    add_filter(filters, build_blur(cfg))
    add_filter(filters, build_grain(cfg))
    add_filter(filters, build_custom(cfg))

    filter_chain = ",".join(filters)

    print("Using filter chain:")
    print(filter_chain)
    print()

    cmd = [
        "ffmpeg",
        "-i", str(input_path),
        "-vf", filter_chain,
        "-c:a", "copy",
        str(output_path)
    ]

    print("Executing FFmpeg…")
    print(" ".join(shlex.quote(x) for x in cmd))
    print()

    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
