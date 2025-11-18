"""Generate example.env.* files from .env.* files recursively.

Extracts variable names and infers their value types.
"""

import os
import re
import sys
from pathlib import Path


def infer_type(value: str) -> str:
    """Infer the type of an environment variable value.

    Args:
        value: The environment variable value as a string

    Returns:
        A string representing the inferred type
    """
    value = value.strip()

    # Check for boolean
    if value.lower() in ("true", "false"):
        return "bool"

    # Check for integer
    if value.isdigit() or (value.startswith("-") and value[1:].isdigit()):
        return "int"

    # Check for float
    try:
        float(value)
        if "." in value:
            return "float"
        return "int"
    except ValueError:
        pass

    # Check for JSON-like structures
    if (value.startswith("[") and value.endswith("]")) or (
        value.startswith("{") and value.endswith("}")
    ):
        return "json"

    # Check for URL
    if value.startswith(
        ("http://", "https://", "ftp://", "postgres://", "mysql://")
    ):
        return "url"

    # Check for path-like (contains / or \)
    if "/" in value or "\\" in value:
        return "path"

    # Default to string
    return "str"


def parse_env_file(file_path: Path) -> dict[str, str]:
    """Parse a .env file and extract variable names and their inferred types.

    Args:
        file_path: Path to the .env file

    Returns:
        Dictionary mapping variable names to their inferred types
    """
    env_vars = {}

    try:
        with open(file_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()

                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue

                # Parse the line
                if "=" not in line:
                    continue

                # Handle key=value pairs
                key, value = line.split("=", 1)
                key = key.strip()

                # Skip if key is empty
                if not key:
                    continue

                # Remove quotes from value if present
                value = value.strip().strip("\"'")

                # Infer type
                inferred_type = infer_type(value)
                env_vars[key] = inferred_type

    except OSError as e:
        print(f"Error reading file {file_path}: {e}", file=sys.stderr)

    return env_vars


def generate_example_env(env_vars: dict[str, str], original_file: Path) -> str:
    """Generate content for an example.env file.

    Args:
        env_vars: Dictionary mapping variable names to their types
        original_file: Path to the original .env file

    Returns:
        String content for the example.env file
    """
    lines = [f"# Example environment variables from {original_file.name}\n"]

    for key in sorted(env_vars.keys()):
        var_type = env_vars[key]
        lines.append(f"{key}=<{var_type}>\n")

    return "".join(lines)


def find_and_process_env_files(root_dir: Path) -> None:
    """Recursively find .env.* files and generate corresponding example files.

    Args:
        root_dir: Root directory to start the search
    """
    env_pattern = re.compile(r"^\.env(\..+)?$")
    found_files = []

    # Walk through directory tree
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Skip common directories
        skip_dirs = {
            ".git",
            "__pycache__",
            ".venv",
            "venv",
            "node_modules",
            ".next",
        }
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]

        for filename in filenames:
            # Check if file matches .env or .env.* pattern
            if env_pattern.match(filename):
                file_path = Path(dirpath) / filename
                found_files.append(file_path)

    if not found_files:
        print("No .env files found.")
        return

    print(f"Found {len(found_files)} .env file(s):\n")

    # Process each file
    for env_file in found_files:
        print(f"Processing: {env_file}")

        # Parse the env file
        env_vars = parse_env_file(env_file)

        if not env_vars:
            print("  ⚠️  No variables found\n")
            continue

        # Generate example file
        example_content = generate_example_env(env_vars, env_file)

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
            print(
                f"  ✓ Generated: {example_file.relative_to(root_dir)} "
                f"({len(env_vars)} variables)\n"
            )
        except OSError as e:
            print(f"  ✗ Error writing {example_file}: {e}\n", file=sys.stderr)


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        root_dir = Path(sys.argv[1])
    else:
        root_dir = Path.cwd()

    if not root_dir.exists():
        print(f"Error: Directory {root_dir} does not exist.", file=sys.stderr)
        sys.exit(1)

    if not root_dir.is_dir():
        print(f"Error: {root_dir} is not a directory.", file=sys.stderr)
        sys.exit(1)

    print(f"Searching for .env files in: {root_dir}\n")
    find_and_process_env_files(root_dir)
    print("Done!")


if __name__ == "__main__":
    main()
