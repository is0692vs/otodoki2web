import importlib
import pkgutil
import inspect

from .base import BaseSearchStrategy


def get_strategy(strategy_name: str, **kwargs) -> BaseSearchStrategy:
    """指定された戦略名に基づいて戦略インスタンスを取得する。
    
    Args:
        strategy_name: 戦略名
        **kwargs: 戦略クラスに渡す追加のキーワード引数（例: session, user_id）
    """

    try:
        if strategy_name == "chart_keyword":
            from .chart_keyword import ChartKeywordSearchStrategy

            return ChartKeywordSearchStrategy()
        
        if strategy_name == "user_preference_search":
            from .user_preference_search import UserPreferenceSearchStrategy
            
            return UserPreferenceSearchStrategy(**kwargs)

        module_path = f"app.services.search_strategies.{strategy_name}"
        strategy_module = importlib.import_module(module_path)

        for obj in vars(strategy_module).values():
            if (
                inspect.isclass(obj)
                and issubclass(obj, BaseSearchStrategy)
                and obj is not BaseSearchStrategy
            ):
                return obj()

        raise ImportError(
            "No BaseSearchStrategy subclass found in module "
            f"'{strategy_name}'."
        )

    except (ImportError, AttributeError) as exc:
        raise ImportError(
            "Could not load search strategy "
            f"'{strategy_name}'. Ensure the module exists and "
            "defines a valid strategy class."
        ) from exc


def list_strategies() -> list[str]:
    """
    利用可能なすべての戦略名（モジュール名）のリストを返す

    Returns:
        list[str]: 利用可能な戦略名のリスト
    """
    package_path = "app.services.search_strategies"
    package = importlib.import_module(package_path)

    available_strategies = []
    for _, name, is_pkg in pkgutil.iter_modules(package.__path__):
        if not is_pkg and name != 'base':
            available_strategies.append(name)

    return available_strategies
