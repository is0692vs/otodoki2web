"""Service for personalizing track recommendations based on user preferences."""
from __future__ import annotations

import logging
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.models.track import Track
from app.services.preference_analyzer import PreferenceAnalyzer, UserPreferences

logger = logging.getLogger(__name__)


class PersonalizationService:
    """楽曲のパーソナライゼーションサービス
    
    ユーザーの好みに基づいて楽曲をランク付けし、より関連性の高い楽曲を優先します。
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.analyzer = PreferenceAnalyzer(session)
    
    async def personalize_tracks(
        self,
        tracks: List[Track],
        user: User,
        min_likes: int = 3,
    ) -> List[Track]:
        """ユーザーの好みに基づいて楽曲を並び替え
        
        Args:
            tracks: 楽曲のリスト
            user: ユーザー
            min_likes: 分析に必要な最小like数
            
        Returns:
            List[Track]: 好みに基づいて並び替えられた楽曲リスト
        """
        if not tracks:
            return tracks
        
        try:
            # ユーザーの好みを分析
            preferences = await self.analyzer.analyze_preferences(
                user_id=str(user.id),
                min_likes=min_likes,
            )
            
            # 好みデータがない場合は元の順序を返す
            if not preferences:
                logger.info(
                    f"User {user.id} has insufficient preference data, "
                    "skipping personalization"
                )
                return tracks
            
            # 楽曲をスコアリング
            scored_tracks = [
                (track, self._score_track(track, preferences))
                for track in tracks
            ]
            
            # スコアで並び替え（高い順）
            scored_tracks.sort(key=lambda x: x[1], reverse=True)
            personalized = [track for track, _ in scored_tracks]
            
            logger.info(
                f"Personalized {len(personalized)} tracks for user {user.id} "
                f"based on {preferences.total_likes} likes"
            )
            
            return personalized
            
        except Exception as e:
            logger.error(f"Failed to personalize tracks for user {user.id}: {e}")
            # エラー時は元の順序を返す
            return tracks
    
    def _score_track(
        self,
        track: Track,
        preferences: UserPreferences,
    ) -> float:
        """楽曲にスコアを付ける
        
        Args:
            track: 楽曲
            preferences: ユーザーの好み
            
        Returns:
            float: スコア（高いほど好みに合っている）
        """
        score = 0.0
        
        # ジャンルマッチング
        if track.genre:
            genre_dict = dict(preferences.liked_genres)
            if track.genre in genre_dict:
                # 好きなジャンル: +10点 + カウント数
                score += 10.0 + genre_dict[track.genre]
            
            disliked_genre_dict = dict(preferences.disliked_genres)
            if track.genre in disliked_genre_dict:
                # 嫌いなジャンル: -5点
                score -= 5.0
        
        # アーティストマッチング
        if track.artist:
            artist_dict = dict(preferences.liked_artists)
            if track.artist in artist_dict:
                # 好きなアーティスト: +15点 + カウント数 * 2
                score += 15.0 + artist_dict[track.artist] * 2.0
            
            disliked_artist_dict = dict(preferences.disliked_artists)
            if track.artist in disliked_artist_dict:
                # 嫌いなアーティスト: -10点
                score -= 10.0
        
        return score
