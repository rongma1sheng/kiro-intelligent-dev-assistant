"""藏经阁仪表盘 (Library Dashboard)

白皮书依据: 附录A 全息指挥台 - 9. 藏经阁 (Library)
优先级: P2 - 高级功能

核心功能:
- 研报管理与阅读
- 论文库浏览
- 知识图谱展示
- Scholar引擎集成
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger

try:
    import streamlit as st

    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False


class DocumentType(Enum):
    """文档类型枚举"""

    RESEARCH_REPORT = "研报"
    ACADEMIC_PAPER = "论文"
    NEWS_ARTICLE = "新闻"
    STRATEGY_DOC = "策略文档"
    FACTOR_DOC = "因子文档"


class DocumentSource(Enum):
    """文档来源枚举"""

    BROKER = "券商研报"
    ARXIV = "arXiv"
    SSRN = "SSRN"
    NEWS = "财经新闻"
    INTERNAL = "内部文档"


@dataclass
class Document:
    """文档数据模型

    Attributes:
        doc_id: 文档ID
        title: 标题
        doc_type: 文档类型
        source: 来源
        author: 作者
        publish_date: 发布日期
        summary: 摘要
        keywords: 关键词
        relevance_score: 相关性评分
        read_count: 阅读次数
        extracted_factors: 提取的因子数
    """

    doc_id: str
    title: str
    doc_type: DocumentType
    source: DocumentSource
    author: str
    publish_date: datetime
    summary: str
    keywords: List[str]
    relevance_score: float
    read_count: int = 0
    extracted_factors: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "doc_type": self.doc_type.value,
            "source": self.source.value,
            "author": self.author,
            "publish_date": self.publish_date.isoformat(),
            "summary": self.summary,
            "keywords": self.keywords,
            "relevance_score": self.relevance_score,
            "read_count": self.read_count,
            "extracted_factors": self.extracted_factors,
        }


@dataclass
class KnowledgeNode:
    """知识图谱节点

    Attributes:
        node_id: 节点ID
        name: 名称
        node_type: 节点类型
        connections: 连接数
        importance: 重要性评分
    """

    node_id: str
    name: str
    node_type: str
    connections: int
    importance: float


class LibraryDashboard:
    """藏经阁仪表盘

    白皮书依据: 附录A 全息指挥台 - 9. 藏经阁 (Library)

    提供研报和论文的管理与阅读功能:
    - 研报库浏览
    - 论文库浏览
    - 知识图谱
    - Scholar引擎集成
    """

    COLOR_SCHEME = {
        "rise": "#FF4D4F",
        "fall": "#52C41A",
        "neutral": "#8C8C8C",
        "primary": "#1890FF",
        "warning": "#FA8C16",
    }

    def __init__(self, redis_client: Optional[Any] = None):
        """初始化藏经阁仪表盘

        Args:
            redis_client: Redis客户端
        """
        self.redis_client = redis_client
        logger.info("LibraryDashboard initialized")

    def get_documents(
        self,
        doc_type: Optional[DocumentType] = None,
        source: Optional[DocumentSource] = None,
        keyword: Optional[str] = None,
        limit: int = 20,
    ) -> List[Document]:
        """获取文档列表

        Args:
            doc_type: 文档类型筛选
            source: 来源筛选
            keyword: 关键词搜索
            limit: 返回数量限制

        Returns:
            文档列表
        """
        if self.redis_client is None:
            return self._get_mock_documents(limit)

        try:
            doc_ids = self.redis_client.lrange("mia:library:documents", 0, limit * 2)
            documents = []

            for doc_id in doc_ids:
                data = self.redis_client.hgetall(f"mia:library:doc:{doc_id}")
                if not data:
                    continue

                doc = Document(
                    doc_id=doc_id,
                    title=data.get("title", ""),
                    doc_type=DocumentType[data.get("doc_type", "RESEARCH_REPORT")],
                    source=DocumentSource[data.get("source", "BROKER")],
                    author=data.get("author", ""),
                    publish_date=datetime.fromisoformat(data.get("publish_date", datetime.now().isoformat())),
                    summary=data.get("summary", ""),
                    keywords=data.get("keywords", "").split(","),
                    relevance_score=float(data.get("relevance_score", 0)),
                    read_count=int(data.get("read_count", 0)),
                    extracted_factors=int(data.get("extracted_factors", 0)),
                )

                # 应用筛选
                if doc_type and doc.doc_type != doc_type:
                    continue
                if source and doc.source != source:
                    continue
                if keyword and keyword.lower() not in doc.title.lower():
                    continue

                documents.append(doc)

                if len(documents) >= limit:
                    break

            return documents if documents else self._get_mock_documents(limit)

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Failed to get documents: {e}")
            return self._get_mock_documents(limit)

    def get_knowledge_graph(self) -> List[KnowledgeNode]:
        """获取知识图谱节点

        Returns:
            知识图谱节点列表
        """
        if self.redis_client is None:
            return self._get_mock_knowledge_graph()

        try:
            nodes = []
            node_ids = self.redis_client.smembers("mia:library:knowledge:nodes")

            for node_id in node_ids:
                data = self.redis_client.hgetall(f"mia:library:knowledge:{node_id}")
                if data:
                    nodes.append(
                        KnowledgeNode(
                            node_id=node_id,
                            name=data.get("name", ""),
                            node_type=data.get("type", ""),
                            connections=int(data.get("connections", 0)),
                            importance=float(data.get("importance", 0)),
                        )
                    )

            return nodes if nodes else self._get_mock_knowledge_graph()

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Failed to get knowledge graph: {e}")
            return self._get_mock_knowledge_graph()

    def trigger_scholar_scan(self, sources: List[str]) -> Dict[str, Any]:
        """触发Scholar引擎扫描

        Args:
            sources: 要扫描的来源列表

        Returns:
            扫描任务信息
        """
        task_id = f"scan_{datetime.now().strftime('%Y%m%d%H%M%S')}"  # pylint: disable=implicit-str-concat

        if self.redis_client:
            self.redis_client.hset(
                f"mia:library:scan:{task_id}",
                mapping={"status": "running", "sources": ",".join(sources), "start_time": datetime.now().isoformat()},
            )

        logger.info(f"Scholar scan triggered: {task_id}, sources: {sources}")

        return {"task_id": task_id, "status": "running", "sources": sources}

    def render_streamlit(self) -> None:
        """渲染Streamlit界面"""
        if not HAS_STREAMLIT:
            logger.warning("Streamlit not available")
            return

        st.title("📚 藏经阁 (Library)")
        st.caption("研报管理 · 论文库 · 知识图谱 · Scholar引擎")

        tab1, tab2, tab3, tab4 = st.tabs(["📄 研报库", "📑 论文库", "🕸️ 知识图谱", "🔍 Scholar扫描"])

        with tab1:
            self._render_research_reports()

        with tab2:
            self._render_academic_papers()

        with tab3:
            self._render_knowledge_graph()

        with tab4:
            self._render_scholar_scan()

    def _render_research_reports(self) -> None:
        """渲染研报库"""
        st.subheader("📄 券商研报库")

        # 搜索和筛选
        col1, col2 = st.columns([3, 1])
        with col1:
            keyword = st.text_input("搜索研报", placeholder="输入关键词...")
        with col2:
            source_filter = st.selectbox("来源", ["全部", "券商研报", "财经新闻"])

        source = None
        if source_filter == "券商研报":
            source = DocumentSource.BROKER
        elif source_filter == "财经新闻":
            source = DocumentSource.NEWS

        documents = self.get_documents(
            doc_type=DocumentType.RESEARCH_REPORT, source=source, keyword=keyword if keyword else None
        )

        st.caption(f"共 {len(documents)} 篇研报")
        st.divider()

        for doc in documents:
            with st.expander(f"📄 {doc.title}"):
                col1, col2, col3 = st.columns([2, 1, 1])

                with col1:
                    st.markdown(f"**作者**: {doc.author}")
                    st.markdown(f"**来源**: {doc.source.value}")
                    st.caption(f"发布日期: {doc.publish_date.strftime('%Y-%m-%d')}")

                with col2:
                    st.metric("相关性", f"{doc.relevance_score:.0%}")

                with col3:
                    st.metric("提取因子", doc.extracted_factors)

                st.markdown("**摘要**")
                st.info(doc.summary)

                st.markdown(f"**关键词**: {', '.join(doc.keywords)}")

                if st.button("📖 阅读全文", key=f"read_{doc.doc_id}"):
                    st.success("正在加载全文...")

    def _render_academic_papers(self) -> None:
        """渲染论文库"""
        st.subheader("📑 学术论文库")

        # 来源筛选
        source_filter = st.selectbox("论文来源", ["全部", "arXiv", "SSRN"])

        source = None
        if source_filter == "arXiv":
            source = DocumentSource.ARXIV
        elif source_filter == "SSRN":
            source = DocumentSource.SSRN

        documents = self.get_documents(doc_type=DocumentType.ACADEMIC_PAPER, source=source)

        st.caption(f"共 {len(documents)} 篇论文")
        st.divider()

        for doc in documents:
            with st.container():
                st.markdown(f"### {doc.title}")
                st.caption(f"{doc.author} | {doc.source.value} | {doc.publish_date.strftime('%Y-%m-%d')}")
                st.markdown(doc.summary[:200] + "..." if len(doc.summary) > 200 else doc.summary)

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("相关性", f"{doc.relevance_score:.0%}")
                with col2:
                    st.metric("阅读次数", doc.read_count)
                with col3:
                    st.metric("提取因子", doc.extracted_factors)

                st.divider()

    def _render_knowledge_graph(self) -> None:
        """渲染知识图谱"""
        st.subheader("🕸️ 知识图谱")
        st.info("展示因子、策略、市场概念之间的关联关系")

        nodes = self.get_knowledge_graph()

        # 按类型分组
        node_types = {}
        for node in nodes:
            if node.node_type not in node_types:
                node_types[node.node_type] = []
            node_types[node.node_type].append(node)

        for node_type, type_nodes in node_types.items():
            st.markdown(f"### {node_type}")

            cols = st.columns(4)
            for i, node in enumerate(type_nodes[:8]):
                with cols[i % 4]:
                    st.markdown(f"**{node.name}**")
                    st.caption(f"连接: {node.connections} | 重要性: {node.importance:.2f}")

            st.divider()

    def _render_scholar_scan(self) -> None:
        """渲染Scholar扫描"""
        st.subheader("🔍 Scholar引擎扫描")
        st.info("触发Scholar引擎扫描最新研报和论文")

        with st.form("scholar_scan_form"):
            st.markdown("**选择扫描来源**")

            col1, col2 = st.columns(2)
            with col1:
                scan_arxiv = st.checkbox("arXiv (q-fin)", value=True)
                scan_ssrn = st.checkbox("SSRN", value=True)
            with col2:
                scan_broker = st.checkbox("券商研报", value=True)
                scan_news = st.checkbox("财经新闻", value=False)

            submitted = st.form_submit_button("🚀 开始扫描", use_container_width=True)

        if submitted:
            sources = []
            if scan_arxiv:
                sources.append("arxiv")
            if scan_ssrn:
                sources.append("ssrn")
            if scan_broker:
                sources.append("broker")
            if scan_news:
                sources.append("news")

            if sources:
                result = self.trigger_scholar_scan(sources)
                st.success(f"扫描任务已启动: {result['task_id']}")
                st.info(f"扫描来源: {', '.join(sources)}")
            else:
                st.warning("请至少选择一个扫描来源")

    def _get_mock_documents(self, limit: int) -> List[Document]:
        """获取模拟文档数据"""
        mock_docs = [
            Document(
                "DOC001",
                "2026年A股市场展望：结构性机会凸显",
                DocumentType.RESEARCH_REPORT,
                DocumentSource.BROKER,
                "中信证券研究部",
                datetime(2026, 1, 15),
                "本报告分析了2026年A股市场的主要投资机会，重点关注科技、消费、新能源三大板块...",
                ["A股", "投资策略", "2026展望"],
                0.92,
                156,
                3,
            ),
            Document(
                "DOC002",
                "量化因子有效性研究：动量因子的衰减与重生",
                DocumentType.ACADEMIC_PAPER,
                DocumentSource.ARXIV,
                "Zhang et al.",
                datetime(2026, 1, 10),
                "本文研究了动量因子在A股市场的有效性变化，发现传统动量因子存在显著衰减...",
                ["动量因子", "因子衰减", "量化投资"],
                0.88,
                89,
                5,
            ),
            Document(
                "DOC003",
                "机器学习在因子挖掘中的应用",
                DocumentType.ACADEMIC_PAPER,
                DocumentSource.SSRN,
                "Li & Wang",
                datetime(2026, 1, 8),
                "本文提出了一种基于深度学习的因子挖掘框架，能够自动发现有效的Alpha因子...",
                ["机器学习", "因子挖掘", "深度学习"],
                0.85,
                67,
                8,
            ),
            Document(
                "DOC004",
                "新能源汽车产业链深度报告",
                DocumentType.RESEARCH_REPORT,
                DocumentSource.BROKER,
                "国泰君安",
                datetime(2026, 1, 5),
                "新能源汽车渗透率持续提升，产业链上下游迎来新一轮增长机遇...",
                ["新能源", "汽车", "产业链"],
                0.78,
                234,
                2,
            ),
            Document(
                "DOC005",
                "ESG投资策略研究：中国市场的实证分析",
                DocumentType.ACADEMIC_PAPER,
                DocumentSource.ARXIV,
                "Chen et al.",
                datetime(2026, 1, 3),
                "本文首次系统性地研究了ESG因子在中国A股市场的有效性...",
                ["ESG", "可持续投资", "因子研究"],
                0.82,
                45,
                4,
            ),
        ]
        return mock_docs[:limit]

    def _get_mock_knowledge_graph(self) -> List[KnowledgeNode]:
        """获取模拟知识图谱"""
        return [
            KnowledgeNode("N001", "动量因子", "因子", 15, 0.92),
            KnowledgeNode("N002", "价值因子", "因子", 12, 0.88),
            KnowledgeNode("N003", "质量因子", "因子", 10, 0.85),
            KnowledgeNode("N004", "趋势跟踪", "策略", 8, 0.78),
            KnowledgeNode("N005", "均值回归", "策略", 7, 0.75),
            KnowledgeNode("N006", "科技板块", "市场", 20, 0.95),
            KnowledgeNode("N007", "消费板块", "市场", 18, 0.90),
            KnowledgeNode("N008", "新能源", "市场", 16, 0.88),
        ]
