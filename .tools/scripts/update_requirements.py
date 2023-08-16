"""Update requirements versions which are coupled to others."""

from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from re import MULTILINE, VERBOSE, Pattern, compile

from dulwich.porcelain import submodule_list
from dulwich.repo import Repo


def main():
    requirements_files = [
        Path("pyproject.toml"),
        *sorted(Path(".tools/requirements").glob("requirements*.txt")),
    ]
    with closing(repo := Repo(str(Path.cwd()))):
        submodules = [Submodule(*item) for item in list(submodule_list(repo))]
    dependency_relation = r"(?P<relation>[=~>]=)"  # ==, ~=, or >=
    for file in requirements_files:
        original_content = content = file.read_text("utf-8")
        if pandas_match := compile_specific(
            rf"""
            pandas                  # pandas
            (\[[\w,]+\])?           # e.g. [hdf5,performance] (optional)
            {dependency_relation}   # e.g. ==
            (?P<version>[\w\d\.]*)  # e.g. 2.0.2
            """
        ).search(content):
            content = compile_specific(
                rf"""
                (?P<dep>pandas-stubs)   # pandas-stubs
                {dependency_relation}   # e.g. ~=
                (?P<version>[\w\d\.]*)  # e.g. 2.0.2
                """
            ).sub(
                repl=rf"\g<prefix>\g<dep>\g<relation>{pandas_match['version']}\g<suffix>",
                string=content,
            )
        for sub in submodules:
            content = compile_specific(
                rf"""
                {sub.name}@                            # name@
                (?P<domain>git\+https://github\.com/)  # git+https://github.com/
                (?P<org>\w+/)                          # org/
                {sub.name}@                            # name@
                (?P<commit>\w+)                        # <commit-hash>
                $"""
            ).sub(
                repl=rf"\g<prefix>{sub.name}@\g<domain>\g<org>{sub.name}@{sub.commit}\g<suffix>",
                string=content,
            )
        if content != original_content:
            file.write_text(encoding="utf-8", data=content)


@dataclass
class Submodule:
    """Represents a git submodule."""

    name: str
    """The submodule name."""
    commit: str
    """The commit hash currently tracked by the submodule."""

    def __post_init__(self):
        """Handle byte strings reported by some submodule sources, like dulwich."""
        # dulwich.porcelain.submodule_list returns bytes
        if isinstance(self.name, bytes):
            self.name = self.name.decode("utf-8")


def compile_specific(pattern: str) -> Pattern[str]:
    """Compile verbose, multi-line regex pattern with a specific prefix and suffix."""
    return compile(
        flags=VERBOSE | MULTILINE,
        pattern=rf"""^
            (?P<prefix>\s*['"])?  # Optional `"` as in pyproject.toml
            {pattern}
            (?P<suffix>['"],)?  # Optional `",` as in pyproject.toml
            $""",
    )


if __name__ == "__main__":
    main()
