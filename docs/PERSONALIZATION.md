# 楽曲パーソナライゼーション機能

## 概要

otodoki2 では、ユーザーの like/dislike 評価履歴を分析し、個々のユーザーの好みに基づいてパーソナライズされた楽曲推薦を提供します。

## 機能の仕組み

### 1. 好み分析 (PreferenceAnalyzer)

`PreferenceAnalyzer` サービスは、ユーザーの評価履歴から以下の統計情報を抽出します：

- **Liked genres**: ユーザーが like した楽曲のジャンル別カウント
- **Liked artists**: ユーザーが like した楽曲のアーティスト別カウント
- **Disliked genres**: ユーザーが dislike した楽曲のジャンル別カウント
- **Disliked artists**: ユーザーが dislike した楽曲のアーティスト別カウント

最低3つの like 評価があれば、パーソナライゼーションが有効になります。

### 2. パーソナライゼーション (PersonalizationService)

`PersonalizationService` は、楽曲リストをユーザーの好みに基づいてスコアリングし、並び替えます。

#### スコアリングルール

- **好きなジャンルの楽曲**: +10点 + そのジャンルの like 数
- **好きなアーティストの楽曲**: +15点 + そのアーティストの like 数 × 2
- **嫌いなジャンルの楽曲**: -5点
- **嫌いなアーティストの楽曲**: -10点

スコアが高い楽曲ほど、ユーザーの好みに合っていると判断されます。

### 3. API 統合

`/api/v1/tracks/suggestions` エンドポイントは、オプショナルな認証をサポートしています：

- **認証あり**: パーソナライズされた楽曲リストを返す
- **認証なし**: 通常の楽曲リストを返す（既存動作）

## 使用例

### フロントエンドから利用する

```typescript
import { api } from '@/services';

// 認証済みの場合、自動的にパーソナライズされた楽曲が返される
const response = await api.tracks.suggestions({ 
  limit: 20,
  excludeIds: '1001,1002,1003' 
});

if (response.data) {
  // パーソナライズされた楽曲リスト
  const tracks = response.data.data;
}
```

### プログラマティックに分析する

```python
from app.services.preference_analyzer import PreferenceAnalyzer
from app.services.personalization import PersonalizationService

# ユーザーの好みを分析
analyzer = PreferenceAnalyzer(session)
preferences = await analyzer.analyze_preferences(
    user_id=user.id,
    min_likes=3,
)

if preferences:
    print(f"Top genres: {preferences.get_top_genres(5)}")
    print(f"Top artists: {preferences.get_top_artists(5)}")
    
    # 楽曲をパーソナライズ
    personalization = PersonalizationService(session)
    personalized_tracks = await personalization.personalize_tracks(
        tracks=candidate_tracks,
        user=user,
    )
```

## 検索戦略への拡張

`UserPreferenceSearchStrategy` は、Worker のキュー補充時にユーザーの好みを活用できる検索戦略です（将来的な拡張）：

```python
from app.services.search_strategies import get_strategy

# ユーザー固有の検索戦略を取得
strategy = get_strategy(
    "user_preference_search",
    session=db_session,
    user_id=user.id,
)

# 好みに基づいた検索パラメータを生成
params = await strategy.generate_params()
# 例: {"term": "Rock", "entity": "song", "attribute": "genreIndex"}
```

## テスト

包括的なテストスイートが `backend/tests/test_personalization.py` に含まれています：

```bash
# テストを実行
cd backend
pytest tests/test_personalization.py -v
```

テストカバレッジ：
- PreferenceAnalyzer の分析機能
- PersonalizationService のスコアリングとランク付け
- データ不足時のフォールバック動作
- 空リストのハンドリング

## パフォーマンスに関する考慮事項

- **キャッシング**: ユーザーの好み情報は、セッション内でキャッシュすることを推奨
- **非同期処理**: すべての分析とパーソナライゼーションは非同期で実行
- **フォールバック**: データ不足や分析失敗時は、通常の楽曲リストにフォールバック

## 今後の拡張案

1. **機械学習統合**: より高度な推薦アルゴリズムの導入
2. **コラボレーティブフィルタリング**: 類似ユーザーの好みを活用
3. **時系列分析**: ユーザーの好みの変化を追跡
4. **A/Bテスト**: パーソナライゼーションの効果測定
