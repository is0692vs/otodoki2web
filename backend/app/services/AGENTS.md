# `backend/app/services/` ディレクトリの AGENT ルール

このディレクトリには、ビジネスロジックや外部サービスとの連携を行うサービス層のコードが含まれます。

## 構造と役割

- `__init__.py`: Python パッケージとして認識させるためのファイル。
- `itunes_api.py`: iTunes Search API との連携を担当します。楽曲の検索、取得、整形機能を提供します。
- `suggestions.py`: 楽曲提供 API のロジックが含まれます。
- `worker.py`: バックグラウンドで動作し、iTunes API から楽曲データを取得し、キューを補充するワーカーロジックが含まれます。
- `play_history.py`: スワイプ/再生で取得したトラックメタデータをキャッシュしつつ、ユーザーの再生履歴を永続化します。
- `preference_analyzer.py`: ユーザーの評価履歴（like/dislike）を分析し、好みの統計情報を生成します。
- `personalization.py`: ユーザーの好みに基づいて楽曲をランク付けし、パーソナライズされた推薦を行います。
- `search_strategies/`: 楽曲検索戦略を定義するモジュール群が含まれます。

## 主要なコンポーネント

- `iTunesApiClient`: iTunes Search API との通信を管理し、楽曲データを取得します。
- `SuggestionsService`: 楽曲提供 API のビジネスロジックを実装します。
- `QueueReplenishmentWorker`: 楽曲キューの補充プロセスを管理します。
- `PlayHistoryService`: `/api/v1/history/played` から渡された再生イベントを `PlayHistory` テーブルに保存し、トラック情報のキャッシュを整備します。
- `PreferenceAnalyzer`: ユーザーの like/dislike 評価から、好きなジャンル・アーティストを分析します。
- `PersonalizationService`: ユーザーの好みに基づいて楽曲のスコアリングと並び替えを行います。

## AI エージェントへの指示

- 新しい外部サービスとの連携が必要な場合は、ここに新しいサービスモジュールを作成してください。
- 既存のサービスロジックを変更する場合は、該当するサービスファイル (`itunes_api.py`, `suggestions.py`, `worker.py`) を修正してください。
- 楽曲検索の戦略を追加または変更する場合は、`search_strategies/` ディレクトリを参照してください。
- ユーザーのパーソナライゼーション機能を拡張する場合は、`preference_analyzer.py` と `personalization.py` を参照してください。
