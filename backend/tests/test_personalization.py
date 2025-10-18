"""Tests for personalization and preference analysis services."""
import pytest
import pytest_asyncio
from uuid import uuid4

from app.db.models import Evaluation, EvaluationStatus, TrackCache, User
from app.services.personalization import PersonalizationService
from app.services.preference_analyzer import PreferenceAnalyzer
from app.models.track import Track


@pytest_asyncio.fixture
async def test_user(async_session):
    """Create a test user."""
    user = User(
        id=uuid4(),
        email="test@example.com",
        hashed_password="hashed_password",
        display_name="Test User",
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_tracks(async_session):
    """Create test tracks in the database."""
    tracks = [
        TrackCache(
            external_id="1001",
            source="itunes",
            title="Rock Song 1",
            artist="Rock Band",
            album="Rock Album",
            primary_genre="Rock",
            duration_ms=180000,
        ),
        TrackCache(
            external_id="1002",
            source="itunes",
            title="Pop Song 1",
            artist="Pop Artist",
            album="Pop Album",
            primary_genre="Pop",
            duration_ms=200000,
        ),
        TrackCache(
            external_id="1003",
            source="itunes",
            title="Rock Song 2",
            artist="Rock Band",
            album="Rock Album 2",
            primary_genre="Rock",
            duration_ms=190000,
        ),
        TrackCache(
            external_id="1004",
            source="itunes",
            title="Jazz Song",
            artist="Jazz Artist",
            album="Jazz Album",
            primary_genre="Jazz",
            duration_ms=240000,
        ),
    ]
    
    for track in tracks:
        async_session.add(track)
    await async_session.commit()
    
    for track in tracks:
        await async_session.refresh(track)
    
    return tracks


@pytest_asyncio.fixture
async def test_evaluations(async_session, test_user, test_tracks):
    """Create test evaluations."""
    # Like first 3 tracks (2 Rock, 1 Pop)
    evaluations = []
    for i in range(3):
        eval = Evaluation(
            id=uuid4(),
            user_id=test_user.id,
            track_id=test_tracks[i].id,
            external_track_id=test_tracks[i].external_id,
            status=EvaluationStatus.LIKE,
            source="swipe",
        )
        async_session.add(eval)
        evaluations.append(eval)
    
    # Dislike Jazz track
    eval = Evaluation(
        id=uuid4(),
        user_id=test_user.id,
        track_id=test_tracks[3].id,
        external_track_id=test_tracks[3].external_id,
        status=EvaluationStatus.DISLIKE,
        source="swipe",
    )
    async_session.add(eval)
    evaluations.append(eval)
    
    await async_session.commit()
    
    for eval in evaluations:
        await async_session.refresh(eval)
    
    return evaluations


class TestPreferenceAnalyzer:
    """Test PreferenceAnalyzer service."""
    
    @pytest.mark.asyncio
    async def test_analyze_preferences_with_sufficient_data(
        self, async_session, test_user, test_evaluations
    ):
        """Test preference analysis with sufficient data."""
        analyzer = PreferenceAnalyzer(async_session)
        preferences = await analyzer.analyze_preferences(
            user_id=str(test_user.id),
            min_likes=3,
        )
        
        assert preferences is not None
        assert preferences.total_likes == 3
        assert preferences.total_dislikes == 1
        
        # Check genres
        top_genres = preferences.get_top_genres(limit=2)
        assert "Rock" in top_genres
        assert len(top_genres) <= 2
        
        # Check artists
        top_artists = preferences.get_top_artists(limit=2)
        assert "Rock Band" in top_artists or "Pop Artist" in top_artists
    
    @pytest.mark.asyncio
    async def test_analyze_preferences_insufficient_data(
        self, async_session, test_user
    ):
        """Test preference analysis with insufficient data."""
        analyzer = PreferenceAnalyzer(async_session)
        preferences = await analyzer.analyze_preferences(
            user_id=str(test_user.id),
            min_likes=10,  # High threshold
        )
        
        # Should return None when insufficient data
        assert preferences is None
    
    @pytest.mark.asyncio
    async def test_genre_counting(self, async_session, test_user, test_evaluations):
        """Test genre counting accuracy."""
        analyzer = PreferenceAnalyzer(async_session)
        preferences = await analyzer.analyze_preferences(
            user_id=str(test_user.id),
            min_likes=3,
        )
        
        assert preferences is not None
        # Should have Rock (2) and Pop (1) in liked genres
        genre_dict = dict(preferences.liked_genres)
        assert genre_dict.get("Rock", 0) == 2
        assert genre_dict.get("Pop", 0) == 1
        
        # Should have Jazz in disliked genres
        disliked_genre_dict = dict(preferences.disliked_genres)
        assert "Jazz" in disliked_genre_dict


class TestPersonalizationService:
    """Test PersonalizationService."""
    
    @pytest.mark.asyncio
    async def test_personalize_tracks_with_preferences(
        self, async_session, test_user, test_evaluations
    ):
        """Test track personalization with user preferences."""
        service = PersonalizationService(async_session)
        
        # Create tracks to personalize
        tracks = [
            Track(
                id="2001",
                title="New Rock Song",
                artist="Rock Band",
                genre="Rock",
                album="New Album",
                artwork_url="",
                preview_url="",
            ),
            Track(
                id="2002",
                title="New Jazz Song",
                artist="Jazz Artist",
                genre="Jazz",
                album="New Jazz Album",
                artwork_url="",
                preview_url="",
            ),
            Track(
                id="2003",
                title="New Pop Song",
                artist="Pop Artist",
                genre="Pop",
                album="New Pop Album",
                artwork_url="",
                preview_url="",
            ),
        ]
        
        personalized = await service.personalize_tracks(tracks, test_user)
        
        # Rock should be first (liked genre)
        # Jazz should be last (disliked genre)
        assert personalized[0].genre == "Rock"
        assert personalized[-1].genre == "Jazz"
    
    @pytest.mark.asyncio
    async def test_personalize_empty_tracks(self, async_session, test_user):
        """Test personalization with empty track list."""
        service = PersonalizationService(async_session)
        personalized = await service.personalize_tracks([], test_user)
        assert personalized == []
    
    @pytest.mark.asyncio
    async def test_personalize_without_preferences(self, async_session, test_user):
        """Test personalization when user has no preferences."""
        service = PersonalizationService(async_session)
        
        tracks = [
            Track(
                id="3001",
                title="Song 1",
                artist="Artist 1",
                genre="Rock",
                album="Album 1",
                artwork_url="",
                preview_url="",
            ),
            Track(
                id="3002",
                title="Song 2",
                artist="Artist 2",
                genre="Pop",
                album="Album 2",
                artwork_url="",
                preview_url="",
            ),
        ]
        
        # User with no evaluations - should return original order
        personalized = await service.personalize_tracks(
            tracks, test_user, min_likes=100
        )
        assert personalized == tracks
    
    @pytest.mark.asyncio
    async def test_track_scoring(self, async_session, test_user, test_evaluations):
        """Test track scoring logic."""
        service = PersonalizationService(async_session)
        
        # Load preferences
        preferences = await service.analyzer.analyze_preferences(
            user_id=str(test_user.id),
            min_likes=3,
        )
        
        assert preferences is not None
        
        # Create test tracks
        rock_track = Track(
            id="4001",
            title="Rock Song",
            artist="Rock Band",
            genre="Rock",
            album="Album",
            artwork_url="",
            preview_url="",
        )
        
        jazz_track = Track(
            id="4002",
            title="Jazz Song",
            artist="Jazz Artist",
            genre="Jazz",
            album="Album",
            artwork_url="",
            preview_url="",
        )
        
        # Score tracks
        rock_score = service._score_track(rock_track, preferences)
        jazz_score = service._score_track(jazz_track, preferences)
        
        # Rock should have higher score (liked genre and artist)
        # Jazz should have lower or negative score (disliked genre)
        assert rock_score > jazz_score
