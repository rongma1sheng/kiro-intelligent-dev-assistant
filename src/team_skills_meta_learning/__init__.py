"""
12人团队Skills元学习系统

基于元学习理论，为硅谷12人团队提供智能技能识别、学习模式分析和配置优化功能。
"""

from .models import (
    Skill, SkillCategory, SkillLevel, RoleSkillProfile, 
    LearningEvent, LearningEventType, LearningOutcome
)
from .skill_recognition import SkillRecognitionEngine
from .pattern_analyzer import LearningPatternAnalyzer
from .config_optimizer import SkillConfigurationOptimizer
from .meta_coordinator import MetaLearningCoordinator
from .core import TeamSkillsMetaLearningSystem

__version__ = "1.0.0"
__author__ = "Kiro Team"

__all__ = [
    # 核心系统
    "TeamSkillsMetaLearningSystem",
    
    # 数据模型
    "Skill", "SkillCategory", "SkillLevel", "RoleSkillProfile",
    "LearningEvent", "LearningEventType", "LearningOutcome",
    
    # 核心引擎
    "SkillRecognitionEngine", "LearningPatternAnalyzer",
    "SkillConfigurationOptimizer", "MetaLearningCoordinator"
]