"""Service for analyzing user preferences from evaluations."""
from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Evaluation, EvaluationStatus, TrackCache

logger = logging.getLogger(__name__)


@dataclass
class UserPreferences:
    """ユーザーの好みの統計情報"""
    
    liked_genres: List[tuple[str, int]]  # (genre, count) のリスト
    liked_artists: List[tuple[str, int]]  # (artist, count) のリスト
    disliked_genres: List[tuple[str, int]]
    disliked_artists: List[tuple[str, int]]
    total_likes: int
    total_dislikes: int
    
    def get_top_genres(self, limit: int = 5) -> List[str]:
        """上位のジャンルを取得"""
        return [genre for genre, _ in self.liked_genres[:limit]]
    
    def get_top_artists(self, limit: int = 5) -> List[str]:
        """上位のアーティストを取得"""
        return [artist for artist, _ in self.liked_artists[:limit]]


class PreferenceAnalyzer:
    """ユーザーの評価履歴から好みを分析するサービス"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def analyze_preferences(
        self,
        user_id: str,
        min_likes: int = 3,
    ) -> Optional[UserPreferences]:
        """ユーザーの好みを分析
        
        Args:
            user_id: ユーザーID
            min_likes: 分析に必要な最小like数
            
        Returns:
            UserPreferences: 好みの統計情報、データ不足の場合はNone
        """
        try:
            # Liked tracks の取得
            liked_query = (
                select(TrackCache)
                .join(Evaluation, Evaluation.track_id == TrackCache.id)
                .where(Evaluation.user_id == user_id)
                .where(Evaluation.status == EvaluationStatus.LIKE)
            )
            liked_result = await self.session.execute(liked_query)
            liked_tracks = list(liked_result.scalars().all())
            
            # Disliked tracks の取得
            disliked_query = (
                select(TrackCache)
                .join(Evaluation, Evaluation.track_id == TrackCache.id)
                .where(Evaluation.user_id == user_id)
                .where(Evaluation.status == EvaluationStatus.DISLIKE)
            )
            disliked_result = await self.session.execute(disliked_query)
            disliked_tracks = list(disliked_result.scalars().all())
            
            # データが不足している場合は None を返す
            if len(liked_tracks) < min_likes:
                logger.info(
                    f"User {user_id} has insufficient likes ({len(liked_tracks)} < {min_likes})"
                )
                return None
            
            # ジャンルとアーティストの集計
            liked_genres = self._count_genres(liked_tracks)
            liked_artists = self._count_artists(liked_tracks)
            disliked_genres = self._count_genres(disliked_tracks)
            disliked_artists = self._count_artists(disliked_tracks)
            
            preferences = UserPreferences(
                liked_genres=liked_genres,
                liked_artists=liked_artists,
                disliked_genres=disliked_genres,
                disliked_artists=disliked_artists,
                total_likes=len(liked_tracks),
                total_dislikes=len(disliked_tracks),
            )
            
            logger.info(
                f"Analyzed preferences for user {user_id}: "
                f"{len(liked_genres)} genres, {len(liked_artists)} artists from {len(liked_tracks)} likes"
            )
            
            return preferences
            
        except Exception as e:
            logger.error(f"Failed to analyze preferences for user {user_id}: {e}")
            return None
    
    def _count_genres(self, tracks: List[TrackCache]) -> List[tuple[str, int]]:
        """ジャンルをカウント"""
        genres = [
            track.primary_genre
            for track in tracks
            if track.primary_genre
        ]
        counter = Counter(genres)
        return counter.most_common()
    
    def _count_artists(self, tracks: List[TrackCache]) -> List[tuple[str, int]]:
        """アーティストをカウント"""
        artists = [
            track.artist
            for track in tracks
            if track.artist
        ]
        counter = Counter(artists)
        return counter.most_common()
