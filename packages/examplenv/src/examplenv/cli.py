"""Generate example.env.* files from .env.* files recursively.

Extracts variable names and infers their value types.
"""

import os
import re
import sys
from glob import glob
from typing import Literal, Iterable, Annotated, TypedDict
from pathlib import Path

import typer


app = typer.Typer(no_args_is_help=True)


class EnvFileLine(TypedDict):
    key: str | None
    value: str | None
    comment: str | None


TOKEN_KV_SEP = "="
TOKEN_START_COMMENT = "#"


def parse_env_file(file_path: Path) -> Iterable[EnvFileLine]:
    with open(file_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            res: EnvFileLine = {"key": None, "value": None, "comment": None}

            part_type: Literal["key", "value", "comment"] = "key"
            part_val_start = 0
            part_val_end = 0
            # Parse key
            for part_val_end, char in enumerate(line):
                if char == TOKEN_KV_SEP:
                    if part_val_start != part_val_end:
                        res[part_type] = line[part_val_start:part_val_end]
                    else:
                        res[part_type] = None
                    part_type = "value"
                    part_val_start = part_val_end + 1
                elif char == TOKEN_START_COMMENT:
                    res[part_type] = line[part_val_start:part_val_end]
                    part_type = "comment"
                    part_val_start = part_val_end + 1
                    break

            res[part_type] = line[part_val_start:].strip()
            yield res


def construct_env_line(env_line: EnvFileLine) -> str:
    res = ""
    if env_line["key"]:
        res += env_line["key"]
    if env_line["value"]:
        res += "="
        res += env_line["value"]
    if env_line["comment"]:
        if res:
            res += " # "
        else:
            res += "# "
        res += env_line["comment"]
    return res


SPECIAL_COMMENT_MASK_ON = "!MASK-ON"
SPECIAL_COMMENT_MASK_OFF = "!MASK-OFF"
SPECIAL_COMMENT_SECRET = "!SECRET"


def generate_example_env_file(original_file: Path, mask_all: bool) -> str:
    env_vars = parse_env_file(original_file)
    lines = [f"# Example environment variables for {original_file.name}"]
    in_mask_block = False

    for line in env_vars:
        if line["comment"]:
            if SPECIAL_COMMENT_MASK_ON in line["comment"]:
                in_mask_block = True
            if SPECIAL_COMMENT_MASK_OFF in line["comment"]:
                in_mask_block = False

        if (
            mask_all
            or in_mask_block
            or (line["comment"] and SPECIAL_COMMENT_SECRET in line["comment"])
        ) and line["value"]:
            line["value"] = f"<YOUR_{line['key'] or ''}>"
        lines.append(construct_env_line(line))

    lines.append("")
    return "\n".join(lines)


def find_env_files(
    root_dir: Path,
) -> list[Path]:
    return [
        Path(path)
        for path in glob(
            "**/.env*", recursive=True, root_dir=root_dir, include_hidden=True
        )
    ]


def find_and_gen_example_env_files(root_dir: Path, mask_all: bool) -> None:
    """Recursively find .env.* files and generate corresponding example files.

    Args:
        root_dir: Root directory to start the search
    """
    for env_file in find_env_files(root_dir):
        # Parse the env file
        # Generate example file
        example_content = generate_example_env_file(env_file, mask_all)

        # Determine output filename
        if env_file.name == ".env":
            example_file = env_file.parent / "example.env"
        else:
            # .env.something -> example.env.something
            example_file = env_file.parent / f"example{env_file.name}"

        # Write example file
        try:
            with open(example_file, "w", encoding="utf-8") as f:
                f.write(example_content)
            print(f"{env_file} -> {example_file}")
        except OSError as e:
            print(f"Error writing {example_file}: {e}", file=sys.stderr)


def to_dict(iterable: Iterable[str | tuple[str, str]]):
    res: dict[str, str | None] = {}
    for it in iterable:
        if isinstance(it, tuple):
            res[it[0]] = it[1]
        else:
            res[it] = None

    return res


# def find_and_migrate_env_files(root_dir: Path):
#     for example_env_file in find_env_files(
#         root_dir, re.compile(r"^example\.env(\..+)?$")
#     ):
#         print(f"Processing: {example_env_file}")
#         env_file = example_env_file.parent / example_env_file.name.removeprefix(
#             "example"
#         )
#         if env_file.exists() and env_file.is_file():
#             example_env_vars = to_dict(parse_env_file(example_env_file))
#             env_vars = to_dict(parse_env_file(env_file))
#             lines: list[str] = []

#             for key, val in example_env_vars.items():
#                 if val:
#                     if should_ignore(key, val):
#                         lines.append(f"{key}={val}")
#                 else:
#                     lines.append(key)

#             example_content = "\n".join(lines)
#         else:
#             with open(example_env_file) as f:
#                 example_content = f.read()

#         # Write example file
#         try:
#             with open(env_file, "w", encoding="utf-8") as f:
#                 f.write(example_content)
#             print(f"  ✓ Generated: {env_file.relative_to(root_dir)}\n")
#         except OSError as e:
#             print(f"  ✗ Error writing {env_file}: {e}\n", file=sys.stderr)


def checkPath(path: Path):
    if not path.exists():
        print(f"Error: Directory {path} does not exist.", file=sys.stderr)
        sys.exit(1)

    if not path.is_dir():
        print(f"Error: {path} is not a directory.", file=sys.stderr)
        sys.exit(1)


@app.command("gen")
def gen_example_env(
    dir_to_find: Annotated[
        Path | None,
        typer.Argument(help="Path to search for env file"),
    ] = None,
    mask_all: Annotated[
        bool,
        typer.Option(help="Mask all values, only keep keys"),
    ] = False,
):
    """Find and generate all examples for all .env files."""
    root_dir = dir_to_find if dir_to_find else Path.cwd()
    checkPath(root_dir)

    print(f"Searching for .env files in: {root_dir}\n")
    find_and_gen_example_env_files(root_dir, mask_all)


@app.command()
def migrate(
    dir_to_find: Annotated[
        Path | None, typer.Argument(help="Path to search for env file")
    ],
):
    """Migrate the env file for you."""

    raise NotImplementedError()
    root_dir = dir_to_find if dir_to_find else Path.cwd()
    checkPath(root_dir)

    print(f"Searching for .env files in: {root_dir}\n")
    # find_and_migrate_env_files(root_dir)
    print("Done!")


def main():
    app()


if __name__ == "__main__":
    main()
