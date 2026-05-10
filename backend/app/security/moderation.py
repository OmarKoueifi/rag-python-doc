from __future__ import annotations

from dataclasses import dataclass

from openai import AsyncOpenAI

MODERATION_MODEL = "omni-moderation-latest"


@dataclass(frozen=True)
class ModerationResult:
    flagged: bool
    categories: list[str]

    @property
    def detail(self) -> str:
        return ", ".join(self.categories) if self.categories else ""


async def moderate(client: AsyncOpenAI, text: str) -> ModerationResult:
    resp = await client.moderations.create(model=MODERATION_MODEL, input=text)
    result = resp.results[0]
    flagged_cats = sorted(k for k, v in result.categories.model_dump().items() if v)
    return ModerationResult(flagged=bool(result.flagged), categories=flagged_cats)
