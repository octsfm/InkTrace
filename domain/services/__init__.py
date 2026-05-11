# 文件：模块：__init__
"""
领域服务模块

作者：孔利群
"""

# 文件路径：domain/services/__init__.py


try:
    from domain.services.style_analyzer import StyleAnalyzer
except Exception:  # pragma: no cover - legacy optional import
    StyleAnalyzer = None

try:
    from domain.services.plot_analyzer import PlotAnalyzer
except Exception:  # pragma: no cover - legacy optional import
    PlotAnalyzer = None

try:
    from domain.services.consistency_checker import ConsistencyChecker, ConsistencyReport, Inconsistency
except Exception:  # pragma: no cover - legacy optional import
    ConsistencyChecker = None
    ConsistencyReport = None
    Inconsistency = None

try:
    from domain.services.writing_engine import WritingEngine, WritingContext
except Exception:  # pragma: no cover - legacy optional import
    WritingEngine = None
    WritingContext = None

__all__ = [
    'StyleAnalyzer',
    'PlotAnalyzer',
    'ConsistencyChecker',
    'ConsistencyReport',
    'Inconsistency',
    'WritingEngine',
    'WritingContext'
]
