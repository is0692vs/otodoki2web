# `backend/app/services/search_strategies/` ディレクトリのAGENTルール

このディレクトリには、iTunes API から楽曲を検索するための様々な戦略を定義するモジュール群が含まれます。

## 構造と役割

- `__init__.py`: Pythonパッケージとして認識させるためのファイル。`get_strategy` 関数を提供し、戦略名を元に適切な戦略クラスをロードします。
- `base.py`: すべての検索戦略が継承すべき基底クラス `BaseSearchStrategy` を定義します。
- `artist_search.py`: アーティスト名で楽曲を検索する戦略を実装します。
- `genre_search.py`: ジャンル名で楽曲を検索する戦略を実装します。
- `random_keyword.py`: 定義済みキーワードからランダムに選択して楽曲を検索する戦略を実装します。
- `release_year_search.py`: リリース年で楽曲を検索する戦略を実装します。
- `user_preference_search.py`: ユーザーの like/dislike 評価に基づいて、好みのジャンルやアーティストを検索する戦略を実装します。

## 主要なコンポーネント

- `BaseSearchStrategy`: 検索戦略のインターフェースを定義します。
- 各戦略クラス (`ArtistSearchStrategy`, `GenreSearchStrategy`, `RandomKeywordSearchStrategy`, `ReleaseYearSearchStrategy`, `UserPreferenceSearchStrategy`): `generate_params` メソッドを実装し、iTunes API に渡す検索パラメータを生成します。
- `UserPreferenceSearchStrategy`: ユーザーIDとデータベースセッションを受け取り、ユーザーの評価履歴から好みに基づいた検索パラメータを生成します。

## AIエージェントへの指示

- 新しい検索戦略を追加する場合は、`base.py` を継承した新しいモジュールをこのディレクトリに作成してください。
- 既存の検索戦略のロジックを変更する場合は、該当する戦略ファイル (`artist_search.py`, `genre_search.py`, `random_keyword.py`, `release_year_search.py`, `user_preference_search.py`) を修正してください。
- `get_strategy` 関数に新しい戦略を登録する必要がある場合は、`__init__.py` を更新してください。
- ユーザー固有のコンテキストを必要とする戦略を追加する場合は、`user_preference_search.py` を参考にしてください。