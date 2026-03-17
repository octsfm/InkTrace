# 文件：模块：__init__
"""
领域服务模块

作者：孔利群
"""

# 文件路径：domain/services/__init__.py


from domain.services.style_analyzer import StyleAnalyzer
from domain.services.plot_analyzer import PlotAnalyzer
from domain.services.consistency_checker import ConsistencyChecker, ConsistencyReport, Inconsistency
from domain.services.writing_engine import WritingEngine, WritingContext

__all__ = [
    'StyleAnalyzer',
    'PlotAnalyzer',
    'ConsistencyChecker',
    'ConsistencyReport',
    'Inconsistency',
    'WritingEngine',
    'WritingContext'
]
