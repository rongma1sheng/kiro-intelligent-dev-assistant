"""
技能识别引擎

从代码、文档、代码审查等活动中自动识别和提取技能。
"""

import re
import uuid
from typing import List, Dict, Any
from datetime import datetime

from .models import Skill, SkillCategory, SkillLevel, SkillEvidence


class SkillRecognitionEngine:
    """技能识别引擎"""
    
    def __init__(self):
        # 技能识别规则
        self.code_skill_patterns = {
            "python_programming": [
                r"def\s+\w+", r"class\s+\w+", r"import\s+\w+", r"from\s+\w+\s+import",
                r"@\w+", r"lambda\s+", r"yield\s+", r"async\s+def", r"await\s+"
            ],
            "javascript_programming": [
                r"function\s+\w+", r"const\s+\w+", r"let\s+\w+", r"var\s+\w+",
                r"=>\s*", r"async\s+function", r"await\s+", r"Promise\."
            ],
            "sql_database": [
                r"SELECT\s+", r"INSERT\s+INTO", r"UPDATE\s+", r"DELETE\s+FROM",
                r"CREATE\s+TABLE", r"ALTER\s+TABLE", r"JOIN\s+", r"WHERE\s+"
            ],
            "docker_containerization": [
                r"FROM\s+", r"RUN\s+", r"COPY\s+", r"WORKDIR\s+",
                r"EXPOSE\s+", r"CMD\s+", r"ENTRYPOINT\s+"
            ],
            "git_version_control": [
                r"git\s+add", r"git\s+commit", r"git\s+push", r"git\s+pull",
                r"git\s+merge", r"git\s+branch", r"git\s+checkout"
            ]
        }
        
        self.doc_skill_patterns = {
            "technical_writing": [
                r"##\s+", r"###\s+", r"```", r"\*\*\w+\*\*", r"_\w+_",
                r"1\.\s+", r"-\s+", r"\[.*\]\(.*\)"
            ],
            "api_documentation": [
                r"@param", r"@return", r"@throws", r"@example",
                r"GET\s+/", r"POST\s+/", r"PUT\s+/", r"DELETE\s+/"
            ],
            "system_design": [
                r"architecture", r"component", r"service", r"interface",
                r"scalability", r"performance", r"reliability"
            ]
        }
        
        self.review_skill_patterns = {
            "code_review": [
                r"LGTM", r"looks good", r"approve", r"suggestion",
                r"consider", r"refactor", r"optimize", r"security"
            ],
            "quality_assurance": [
                r"test", r"coverage", r"edge case", r"validation",
                r"error handling", r"exception", r"logging"
            ],
            "mentoring": [
                r"explain", r"teach", r"guide", r"help",
                r"best practice", r"pattern", r"principle"
            ]
        }
    
    def extract_skills_from_code(self, code_content: str, file_path: str) -> List[Skill]:
        """从代码中提取技能"""
        identified_skills = []
        
        # 基于文件扩展名初步判断
        file_ext = file_path.split('.')[-1].lower() if '.' in file_path else ''
        
        for skill_name, patterns in self.code_skill_patterns.items():
            skill_score = 0
            matched_patterns = []
            
            for pattern in patterns:
                matches = re.findall(pattern, code_content, re.IGNORECASE)
                if matches:
                    skill_score += len(matches)
                    matched_patterns.append(pattern)
            
            # 如果找到匹配的模式，创建技能
            if skill_score > 0:
                # 根据匹配程度确定熟练度
                proficiency = min(1.0, skill_score / 10.0)
                
                # 创建技能证据
                evidence = SkillEvidence(
                    evidence_id=str(uuid.uuid4()),
                    evidence_type="code_analysis",
                    source_path=file_path,
                    description=f"在代码中发现{len(matched_patterns)}种{skill_name}模式",
                    quality_score=min(1.0, skill_score / 5.0),
                    timestamp=datetime.now(),
                    metadata={
                        "matched_patterns": matched_patterns,
                        "match_count": skill_score,
                        "file_extension": file_ext
                    }
                )
                
                skill = Skill(
                    id=f"{skill_name}_{uuid.uuid4().hex[:8]}",
                    name=skill_name.replace('_', ' ').title(),
                    category=SkillCategory.TECHNICAL,
                    level=self._determine_skill_level(proficiency),
                    proficiency=proficiency,
                    evidence=[evidence],
                    tags=[skill_name, "code_analysis", file_ext]
                )
                
                identified_skills.append(skill)
        
        return identified_skills
    
    def extract_skills_from_docs(self, document_content: str, doc_type: str) -> List[Skill]:
        """从文档中提取技能"""
        identified_skills = []
        
        for skill_name, patterns in self.doc_skill_patterns.items():
            skill_score = 0
            matched_patterns = []
            
            for pattern in patterns:
                matches = re.findall(pattern, document_content, re.IGNORECASE)
                if matches:
                    skill_score += len(matches)
                    matched_patterns.append(pattern)
            
            if skill_score > 0:
                proficiency = min(1.0, skill_score / 8.0)
                
                evidence = SkillEvidence(
                    evidence_id=str(uuid.uuid4()),
                    evidence_type="document_analysis",
                    source_path=f"{doc_type}_document",
                    description=f"在{doc_type}文档中发现{len(matched_patterns)}种{skill_name}模式",
                    quality_score=min(1.0, skill_score / 4.0),
                    timestamp=datetime.now(),
                    metadata={
                        "matched_patterns": matched_patterns,
                        "match_count": skill_score,
                        "document_type": doc_type
                    }
                )
                
                skill = Skill(
                    id=f"{skill_name}_{uuid.uuid4().hex[:8]}",
                    name=skill_name.replace('_', ' ').title(),
                    category=SkillCategory.SOFT_SKILL,
                    level=self._determine_skill_level(proficiency),
                    proficiency=proficiency,
                    evidence=[evidence],
                    tags=[skill_name, "document_analysis", doc_type]
                )
                
                identified_skills.append(skill)
        
        return identified_skills
    
    def extract_skills_from_reviews(self, review_content: str, review_context: Dict[str, Any]) -> List[Skill]:
        """从代码审查中提取技能"""
        identified_skills = []
        
        for skill_name, patterns in self.review_skill_patterns.items():
            skill_score = 0
            matched_patterns = []
            
            for pattern in patterns:
                matches = re.findall(pattern, review_content, re.IGNORECASE)
                if matches:
                    skill_score += len(matches)
                    matched_patterns.append(pattern)
            
            if skill_score > 0:
                proficiency = min(1.0, skill_score / 6.0)
                
                evidence = SkillEvidence(
                    evidence_id=str(uuid.uuid4()),
                    evidence_type="code_review",
                    source_path=review_context.get("file_path", "unknown"),
                    description=f"在代码审查中发现{len(matched_patterns)}种{skill_name}行为",
                    quality_score=min(1.0, skill_score / 3.0),
                    timestamp=datetime.now(),
                    metadata={
                        "matched_patterns": matched_patterns,
                        "match_count": skill_score,
                        "review_context": review_context
                    }
                )
                
                skill = Skill(
                    id=f"{skill_name}_{uuid.uuid4().hex[:8]}",
                    name=skill_name.replace('_', ' ').title(),
                    category=SkillCategory.SOFT_SKILL,
                    level=self._determine_skill_level(proficiency),
                    proficiency=proficiency,
                    evidence=[evidence],
                    tags=[skill_name, "code_review", "collaboration"]
                )
                
                identified_skills.append(skill)
        
        return identified_skills
    
    def _determine_skill_level(self, proficiency: float) -> SkillLevel:
        """根据熟练度确定技能等级"""
        if proficiency >= 0.9:
            return SkillLevel.EXPERT
        elif proficiency >= 0.7:
            return SkillLevel.ADVANCED
        elif proficiency >= 0.5:
            return SkillLevel.INTERMEDIATE
        elif proficiency >= 0.3:
            return SkillLevel.BEGINNER
        else:
            return SkillLevel.NOVICE
    
    def classify_skill_types(self, skills: List[Skill]) -> Dict[SkillCategory, List[Skill]]:
        """对技能进行分类"""
        classified = {}
        
        for skill in skills:
            category = skill.category
            if category not in classified:
                classified[category] = []
            classified[category].append(skill)
        
        return classified