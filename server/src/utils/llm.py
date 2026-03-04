import logging
from typing import List

from openai import AsyncAzureOpenAI

from src.core.config import settings

logger = logging.getLogger(__name__)


async def summarize_ipo_with_llm(code: str, text: str) -> List[str]:
    """Azure OpenAI を使って会社概要を 4〜8 箇条書きに要約する"""
    if not settings.AZ_OPENAI_ENDPOINT or not settings.AZ_OPENAI_API_KEY:
        logger.warning(
            "Azure OpenAI not configured. Set AZ_OPENAI_ENDPOINT and "
            "AZ_OPENAI_API_KEY to enable summaries."
        )
        return [
            f"銘柄コード {code} の要約を生成するには Azure OpenAI の設定が必要です。"
            "（AZ_OPENAI_ENDPOINT / AZ_OPENAI_API_KEY を設定してください）"
        ]

    client = AsyncAzureOpenAI(
        azure_endpoint=settings.AZ_OPENAI_ENDPOINT,
        api_key=settings.AZ_OPENAI_API_KEY,
        api_version=settings.AZ_OPENAI_API_VERSION,
    )

    system_prompt = (
        "あなたはIPO企業の事業概要をまとめる専門家です。"
        "提供された会社概要テキストを日本語で4〜8項目の箇条書きにまとめてください。"
        "各項目は「・」で始め、1行で完結させてください。"
        "テキストが不十分な場合は入手できた情報の範囲でまとめてください。"
    )
    user_content = (
        text.strip()
        if text.strip()
        else f"銘柄コード {code} の会社概要テキストを取得できませんでした。"
        "入手可能な情報の範囲で概要をまとめてください。"
    )

    response = await client.chat.completions.create(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content[:8000]},
        ],
        max_completion_tokens=16384,
        model=settings.AZ_OPENAI_DEPLOYMENT,
    )

    content = response.choices[0].message.content or ""
    bullets = [
        line.lstrip("・•-").strip()
        for line in content.splitlines()
        if line.strip()
        and (
            line.strip().startswith("・")
            or line.strip().startswith("•")
            or line.strip().startswith("-")
        )
    ]
    return bullets if bullets else [content.strip()]
