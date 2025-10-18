from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
import time
import logging
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional
import os

from sqlalchemy.ext.asyncio import AsyncSession

from .api.routes import (
    auth_router,
    evaluations_router,
    export_router,
    history_router,
    playback_router,
)
from .api.deps import get_optional_user
from .db.models import User
from .dependencies import (
    get_queue_manager,
    get_worker,
    get_db_session,
    initialize_dependencies,
    cleanup_dependencies,
    start_background_tasks,
    stop_background_tasks
)
from .core.queue import QueueManager
from .core.rate_limit import global_rate_limiter
from .services.suggestions import SuggestionsService, check_rate_limit
from .models.suggestions import SuggestionsResponse
from .db.session import dispose_engine

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションのライフサイクル管理"""
    # 起動時
    logger.info("Starting otodoki2 API application")
    initialize_dependencies()

    # レート制限器を初期化
    from .core.config import SuggestionsConfig
    config = SuggestionsConfig()
    global_rate_limiter.initialize(config.get_rate_limit_per_sec(), 1)

    await start_background_tasks()
    yield
    # 終了時
    logger.info("Shutting down otodoki2 API application")
    await stop_background_tasks()
    cleanup_dependencies()
    await dispose_engine()


app = FastAPI(
    title="otodoki2 API",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(auth_router)
app.include_router(evaluations_router)
app.include_router(export_router)
app.include_router(history_router)
app.include_router(playback_router)


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time

    if request.url.path == "/health" and response.status_code == 200:
        return response

    client = request.client
    client_host = client.host if client else "-"
    client_port = client.port if client else "-"
    logger.info(
        "%s:%s - \"%s %s\" %s [%.2fs]",
        client_host,
        client_port,
        request.method,
        request.url.path,
        response.status_code,
        process_time,
    )
    return response

# CORS設定（開発環境用）
origins_str = os.getenv("ORIGINS",
                        "http://localhost:3000,http://localhost:8081")
origins = [origin.strip() for origin in origins_str.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# アプリケーション開始時刻を記録
start_time = time.time()


@app.get("/")
def read_root():
    return {"message": "Hello from backend", "service": "otodoki2-api"}


@app.get("/health")
def read_health():
    current_time = time.time()
    uptime = current_time - start_time
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": round(uptime, 2),
        "service": "otodoki2-api"
    }


@app.get("/queue/stats")
def get_queue_stats(queue_manager: QueueManager = Depends(get_queue_manager)):
    """キューの統計情報を取得"""
    return queue_manager.stats()


@app.get("/queue/health")
def get_queue_health(queue_manager: QueueManager = Depends(get_queue_manager)):
    """キューの健全性チェック"""
    stats = queue_manager.stats()
    return {
        "status": "healthy" if stats["current_size"] > 0 else "low",
        "size": stats["current_size"],
        "capacity": stats["max_capacity"],
        "utilization_percent": stats["utilization"],
        "is_low_watermark": stats["is_low"]
    }


@app.get("/worker/stats")
def get_worker_stats():
    """ワーカーの統計情報を取得"""
    worker = get_worker()
    if worker is None:
        return {"error": "Worker not initialized"}
    return worker.stats


@app.post("/worker/trigger-refill")
async def trigger_refill():
    """ワンショットでキューの補充を実行"""
    worker = get_worker()
    if worker is None:
        return {"error": "Worker not initialized", "success": False}

    success = await worker.trigger_refill()
    message = (
        "Refill completed"
        if success
        else "Refill failed or already in progress"
    )
    return {"success": success, "message": message}


@app.get("/api/v1/tracks/suggestions", response_model=SuggestionsResponse)
async def get_track_suggestions(
    limit: Optional[int] = Query(
        None, ge=1, le=50, description="返却する楽曲数（1-50）"),
    excludeIds: Optional[str] = Query(None, description="除外する楽曲IDのカンマ区切り文字列"),
    queue_manager: QueueManager = Depends(get_queue_manager),
    user: Optional[User] = Depends(get_optional_user),
    session: AsyncSession = Depends(get_db_session),
) -> SuggestionsResponse:
    """楽曲提供APIエンドポイント

    キューから指定された数の楽曲を取得し、excludeIdsで指定された楽曲を除外して返す。
    認証済みユーザーの場合、好みに基づいてパーソナライズされた楽曲を返す。
    必要に応じて補充ワーカーをトリガーする。
    """
    # レート制限チェック
    is_allowed, retry_after = check_rate_limit()
    if not is_allowed:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(int(retry_after) + 1)}
        )

    try:
        # パラメータバリデーション
        from .core.config import SuggestionsConfig
        config = SuggestionsConfig()

        validated_limit = (
            limit if limit is not None else config.get_default_limit()
        )
        validated_limit = max(
            1,
            min(validated_limit, config.get_max_limit()),
        )

        # excludeIdsをリストに変換
        exclude_ids = []
        if excludeIds:
            try:
                exclude_ids = [
                    id_str.strip()
                    for id_str in excludeIds.split(",")
                    if id_str.strip()
                ]
            except Exception:
                exclude_ids = []

        # SuggestionsServiceでリクエスト処理
        worker = get_worker()
        suggestions_service = SuggestionsService(queue_manager, worker)
        response = await suggestions_service.get_suggestions(
            validated_limit,
            exclude_ids,
        )

        # 認証済みユーザーの場合、パーソナライズを適用
        if user and session:
            try:
                from .services.personalization import PersonalizationService
                personalization_service = PersonalizationService(session)
                
                # 楽曲をパーソナライズ（より多く取得してからランク付け）
                # 元のlimitより多く取得していれば、それをパーソナライズして返す
                personalized_tracks = await personalization_service.personalize_tracks(
                    response.data,
                    user,
                )
                response.data = personalized_tracks
                
                logger.info(
                    f"Applied personalization for user {user.id}, "
                    f"delivered {len(response.data)} tracks"
                )
            except Exception as e:
                logger.warning(f"Personalization failed for user {user.id}: {e}")
                # パーソナライズ失敗時は元のレスポンスを返す

        return response

    except Exception as e:
        logger.error(f"Error in get_track_suggestions: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@app.get("/api/v1/tracks/suggestions/stats")
async def get_suggestions_stats():
    """楽曲提供APIの統計情報"""
    rate_limit_stats = global_rate_limiter.get_stats()
    return {
        "rate_limit": rate_limit_stats
    }
