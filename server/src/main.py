import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.core.exceptions import ExternalAPIError, DataParsingError
from src.routers import market, ipo

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)

# アプリケーション
app = FastAPI(
    title="Capital Lens API",
    description="資本市場の概況と新規上場銘柄(IPO)に関するAPI",
    version="1.0.0",
)

# ミドルウェア
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# グローバル例外ハンドラ
@app.exception_handler(ExternalAPIError)
async def external_api_error_handler(
    _request: Request, exc: ExternalAPIError
) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={
            "error": "external_api_error",
            "source": exc.source,
            "detail": exc.detail,
        },
    )


@app.exception_handler(DataParsingError)
async def data_parsing_error_handler(
    _request: Request, exc: DataParsingError
) -> JSONResponse:
    return JSONResponse(
        status_code=502,
        content={
            "error": "data_parsing_error",
            "source": exc.source,
            "detail": exc.detail,
        },
    )


# ルーター
app.include_router(market.router)
app.include_router(ipo.router)

# ヘルスチェック
@app.get("/health")
async def health_check():
    return {"status": "ok"}
