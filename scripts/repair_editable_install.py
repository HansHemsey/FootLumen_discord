from __future__ import annotations

import site
import subprocess
import sys
from pathlib import Path


def main() -> None:
    root_dir = Path(__file__).resolve().parents[1]
    src_dir = root_dir / "src"
    if not src_dir.exists():
        raise SystemExit(f"Missing src directory: {src_dir}")

    written = 0
    for site_dir_raw in site.getsitepackages():
        site_dir = Path(site_dir_raw)
        if not site_dir.exists():
            continue
        marker = site_dir / "football_predictor_local.pth"
        marker.write_text(f"{src_dir}\n", encoding="utf-8")
        if sys.platform == "darwin":
            subprocess.run(
                ["chflags", "nohidden", str(marker)],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        written += 1

    if written == 0:
        raise SystemExit("No writable site-packages directory found")

    entrypoint = Path(sys.prefix) / "bin" / "football-predictor"
    if entrypoint.exists():
        entrypoint.write_text(
            "\n".join(
                [
                    f"#!{sys.executable}",
                    "from __future__ import annotations",
                    "import sys",
                    f"sys.path.insert(0, {str(src_dir)!r})",
                    "from football_predictor.cli import app",
                    "",
                    "if __name__ == '__main__':",
                    "    sys.exit(app())",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        entrypoint.chmod(entrypoint.stat().st_mode | 0o111)
        if sys.platform == "darwin":
            subprocess.run(
                ["chflags", "nohidden", str(entrypoint)],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )


if __name__ == "__main__":
    main()
