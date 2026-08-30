"""Load versioned prompt templates from the prompts/ directory.

Prompts are plain Markdown with ``$name`` placeholders (``string.Template``).
Rejected versions are kept on disk (plan_v1, plan_v2, ...) as part of the
project's evaluation record; code points at the current version explicitly.
"""

from __future__ import annotations

from string import Template

from triage.dataset import REPO_ROOT

PROMPTS_DIR = REPO_ROOT / "prompts"

PLAN_PROMPT = "plan_v1"
CONCLUDE_PROMPT = "conclude_v1"


def load_template(name: str) -> Template:
    path = PROMPTS_DIR / f"{name}.md"
    return Template(path.read_text())


def render(name: str, /, **fields: str) -> str:
    return load_template(name).substitute(**fields)
