from prompt_toolkit import prompt

PROMPT_TEXT = (
    "Select resolution:\n"
    "1. Keep mine (this file)\n"
    "2. Keep theirs (this file)\n"
    "3. Keep mine (all remaining)\n"
    "4. Keep theirs (all remaining)\n"
    "5. Show diff\n"
    "6. Skip\n"
    "7. Abort\n"
    "> "
)


def prompt_conflict_action() -> str:
    return prompt(PROMPT_TEXT).strip()


def prompt_lockfile_regen(file_name: str, command: list[str]) -> bool:
    command_text = " ".join(command)
    message = (
        f"Regenerate {file_name} using '{command_text}'? " "Package versions may change. [y/N] "
    )
    response = prompt(message).strip().lower()
    return response in {"y", "yes"}
