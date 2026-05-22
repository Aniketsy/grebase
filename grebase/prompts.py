from prompt_toolkit import prompt

PROMPT_TEXT = (
    "Select resolution:\n"
    "1. Keep yours (this file)\n"
    "2. Keep theirs (this file)\n"
    "3. Keep yours (all remaining)\n"
    "4. Keep theirs (all remaining)\n"
    "5. Show diff\n"
    "6. Skip\n"
    "7. Abort\n"
    "> "
)


def prompt_conflict_action() -> str:
    return prompt(PROMPT_TEXT).strip()
