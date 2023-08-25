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
    (Path(".vscode") / "pinned-files.json").write_text(
        encoding="utf-8",
        data='{"version":"2","pinnedList":["C:/Users/Blake/Code/mine/boilercore/src/boilercore","C:/Users/Blake/Code/mine/boilercv/src/boilercv","C:/Users/Blake/Code/mine/boilerdaq/src/boilerdaq","C:/Users/Blake/Code/mine/boilerdata/src/boilerdata"],"aliasMap":{}}',
    )


if __name__ == "__main__":
    main()
