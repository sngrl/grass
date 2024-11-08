from typing import Optional


def file_to_list(
        filename: str
):
    with open(filename, 'r+') as f:
        return list(filter(bool, f.read().splitlines()))


def str_to_file(file_name: str, msg: str, mode: Optional[str] = "a"):
    with open(
            file_name,
            mode
    ) as text_file:
        text_file.write(f"{msg}\n")
