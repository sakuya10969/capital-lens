import logging
from typing import Any, Dict, List

from openai import AsyncAzureOpenAI

from src.core.config import settings

logger = logging.getLogger(__name__)


def _make_client() -> AsyncAzureOpenAI:
    return AsyncAzureOpenAI(
        azure_endpoint=settings.AZ_OPENAI_ENDPOINT,
        api_key=settings.AZ_OPENAI_API_KEY,
        api_version=settings.AZ_OPENAI_API_VERSION,
    )


def _az_configured() -> bool:
    return bool(settings.AZ_OPENAI_ENDPOINT and settings.AZ_OPENAI_API_KEY)


async def summarize_ipo_with_llm(code: str, text: str) -> str:
    """Azure OpenAI を使って会社概要を日本語約200文字の短文要約として返す。"""
    if not _az_configured():
        logger.warning(
            "Azure OpenAI not configured. Set AZ_OPENAI_ENDPOINT and "
            "AZ_OPENAI_API_KEY to enable summaries."
        )
        return (
            f"銘柄コード {code} の要約を生成するには Azure OpenAI の設定が必要です。"
            "（AZ_OPENAI_ENDPOINT / AZ_OPENAI_API_KEY を設定してください）"
        )

    system_prompt = (
        "あなたはIPO企業の事業概要を投資家向けに紹介するアナリストです。"
        "提供された会社概要テキストをもとに、日本語で約200～300文字程度で要約を作成してください。"
        "箇条書きは禁止です。"
        "冗長な前置きや「〜を行う企業です。」で終わるだけの単調な文章は避けてください。"
        "企業の事業内容・特徴・市場での立ち位置が簡潔かつ自然に伝わる文章にしてください。"
        "テキストが不十分な場合は取得できた情報の範囲でまとめ、推測で補完しないでください。"
    )
    user_content = (
        text.strip()
        if text.strip()
        else (
            f"銘柄コード {code} の会社概要テキストを取得できませんでした。"
            "入手可能な情報の範囲で要約してください。"
        )
    )

    response = await _make_client().chat.completions.create(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content[:8000]},
        ],
        max_completion_tokens=512,
        model=settings.AZ_OPENAI_DEPLOYMENT,
    )

    return (response.choices[0].message.content or "").strip()


async def summarize_market_with_llm(
    categorised: Dict[str, List[Dict[str, Any]]],
) -> str:
    """市場データから日本語約200文字の地合い解説文を生成して返す。

    Azure OpenAI が未設定の場合は空文字列を返す。
    LLM 呼び出しに失敗した場合もエラーを握りつぶして空文字列を返す。
    """
    if not _az_configured():
        logger.warning(
            "Azure OpenAI not configured. Skipping market summary generation."
        )
        return ""

    # 市場データをテキスト形式に変換
    lines: List[str] = []
    for items in categorised.values():
        for item in items:
            name = item.get("name", "")
            price = item.get("current_price")
            change = item.get("change")
            change_pct = item.get("change_percent")
            if isinstance(change, (int, float)) and isinstance(
                change_pct, (int, float)
            ):
                lines.append(
                    f"{name}: {price} (前日比 {change:+.2f} / {change_pct:+.2f}%)"
                )
            else:
                lines.append(f"{name}: {price}")

    user_content = "以下は直近の市場データです。\n\n" + "\n".join(lines)

    system_prompt = (
        "あなたは資本市場の状況を投資家向けに解説するアナリストです。"
        "提供された市場データをもとに、日本語で約200文字の地合い解説を1段落で作成してください。"
        "箇条書きは禁止です。数値を羅列するだけでなく、全体として何が起きているかが伝わる文章にしてください。"
        "主要指数（日経平均・TOPIX・東証グロース等）の動きから地合いの強弱、"
        "グロース優位か大型株優位かといったニュアンスも含めてください。"
        "冗長な前置きは不要です。"
    )

    try:
        response = await _make_client().chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            max_completion_tokens=512,
            model=settings.AZ_OPENAI_DEPLOYMENT,
        )
        return (response.choices[0].message.content or "").strip()
    except Exception as exc:
        logger.warning("Market summary generation failed: %s", exc)
        return ""
