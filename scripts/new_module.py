import os

import typer
import inquirer
from mako.template import Template


template_dir = os.path.join("templates", "new_module")
mako_suffix = ".mako"
test_file_template: Template | None = None


def main(app_name: str, overwrite: bool = False):
    os.makedirs(f"src/{app_name}", exist_ok=True)
    paths: dict[str, str] = {}
    for root, dirs, files in os.walk(template_dir):
        for file in files:
            if file == "_test.py.mako":
                global test_file_template
                test_file_template = Template(os.path.join(root, file))
                continue
            paths[file.split(".")[0]] = os.path.join(root, file)
    questions = [
        inquirer.Checkbox(
            "files",
            "Files to create",
            choices=list(paths.keys()),
            default=[
                "__init__",
                "consts",
                "dtos",
                "entities",
                "initialize",
                "repositories",
                "routers",
                "services",
            ],
        )
    ]
    answer = inquirer.prompt(questions)
    assert answer and "files" in answer
    file_to_create: list[str] = answer["files"]
    has_router = "routers" in file_to_create
    for file in file_to_create:
        path = paths[file]
        template = Template(filename=path)
        create_file_path = os.path.join("src", app_name, file + ".py")
        create_test_file_path = os.path.join("src", app_name, file + "_test.py")
        if os.path.exists(create_file_path) and not overwrite:
            continue
        with open(
            create_file_path,
            "w",
        ) as f:
            content = template.render(app_name=app_name, has_router=has_router)
            assert isinstance(content, str)
            f.write(content)
        if file == "__init__":
            continue
        with open(
            create_test_file_path,
            "w",
        ) as f:
            content = test_file_template.render(file=file)
            assert isinstance(content, str)
            f.write(content)


if __name__ == "__main__":
    typer.run(main)
