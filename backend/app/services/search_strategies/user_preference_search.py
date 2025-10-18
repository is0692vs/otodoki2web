"""User preference-based search strategy."""
import logging
import random
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseSearchStrategy
from ..preference_analyzer import PreferenceAnalyzer

logger = logging.getLogger(__name__)


class UserPreferenceSearchStrategy(BaseSearchStrategy):
    """ユーザーの好みに基づいて検索パラメータを生成する戦略
    
    ユーザーの like 評価履歴からジャンルやアーティストを分析し、
    好みに合った楽曲を検索するパラメータを生成します。
    """
    
    def __init__(
        self,
        session: Optional[AsyncSession] = None,
        user_id: Optional[str] = None,
    ):
        """初期化
        
        Args:
            session: データベースセッション
            user_id: ユーザーID
        """
        self.session = session
        self.user_id = user_id
        self._preferences = None
        self._preferences_loaded = False
    
    async def generate_params(self) -> Dict[str, Any]:
        """ユーザーの好みに基づいた検索パラメータを生成
        
        Returns:
            Dict[str, Any]: iTunes API 検索パラメータ
        """
        # セッションまたはユーザーIDがない場合はフォールバック
        if not self.session or not self.user_id:
            logger.warning(
                "UserPreferenceSearchStrategy: No session or user_id, falling back to default"
            )
            return self._fallback_params()
        
        # 好みをロード（初回のみ）
        if not self._preferences_loaded:
            await self._load_preferences()
            self._preferences_loaded = True
        
        # 好みデータがない場合はフォールバック
        if not self._preferences:
            logger.info(
                f"User {self.user_id} has insufficient preference data, using fallback"
            )
            return self._fallback_params()
        
        # 好みに基づいてパラメータを生成
        return await self._generate_preference_based_params()
    
    async def _load_preferences(self) -> None:
        """ユーザーの好みをロード"""
        try:
            analyzer = PreferenceAnalyzer(self.session)
            self._preferences = await analyzer.analyze_preferences(
                user_id=self.user_id,
                min_likes=3,  # 最低3つのlikeが必要
            )
        except Exception as e:
            logger.error(f"Failed to load preferences for user {self.user_id}: {e}")
            self._preferences = None
    
    async def _generate_preference_based_params(self) -> Dict[str, Any]:
        """好みに基づいてパラメータを生成"""
        if not self._preferences:
            return self._fallback_params()
        
        # 70%の確率で好きなジャンル、30%の確率で好きなアーティストを検索
        use_genre = random.random() < 0.7
        
        if use_genre:
            top_genres = self._preferences.get_top_genres(limit=3)
            if top_genres:
                genre = random.choice(top_genres)
                logger.info(f"Searching by preferred genre: {genre}")
                return {
                    "term": genre,
                    "entity": "song",
                    "attribute": "genreIndex",
                }
        
        # アーティストで検索
        top_artists = self._preferences.get_top_artists(limit=3)
        if top_artists:
            artist = random.choice(top_artists)
            logger.info(f"Searching by preferred artist: {artist}")
            return {
                "term": artist,
                "entity": "song",
                "attribute": "artistTerm",
            }
        
        # どちらもない場合はフォールバック
        return self._fallback_params()
    
    def _fallback_params(self) -> Dict[str, Any]:
        """フォールバック用のデフォルトパラメータ"""
        # 基本的なキーワード検索にフォールバック
        default_terms = ["pop", "rock", "jazz", "electronic", "indie"]
        term = random.choice(default_terms)
        return {
            "term": term,
            "entity": "song",
        }
