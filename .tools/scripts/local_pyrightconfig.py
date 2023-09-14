"""Generate a local `pyrightconfig.json` variation for development."""

from json import dumps
from pathlib import Path
from tomllib import loads


def main():
    pyright = loads(Path("pyproject.toml").read_text("utf-8"))["tool"]["pyright"]
    pyright["include"] += [
        f"../boiler{suffix}/{path}"
        for suffix in ["cv", "data", "daq"]
        for path in pyright["include"]
    ]
    Path("pyrightconfig.json").write_text(
        encoding="utf-8",
        data=f"{dumps(indent=2, obj=pyright)}\n",
    )


if __name__ == "__main__":
    main()
