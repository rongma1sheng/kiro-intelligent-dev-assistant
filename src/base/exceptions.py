"""
MIA系统异常定义

版本: v1.6.0
作者: MIA Team
日期: 2026-01-18
"""


class MIABaseException(Exception):
    """MIA系统基础异常"""


class ValidationError(MIABaseException):
    """验证错误"""


class ArenaTestError(MIABaseException):
    """Arena测试错误"""


class CertificationError(MIABaseException):
    """认证错误"""


class DataError(MIABaseException):
    """数据错误"""


class ResourceError(MIABaseException):
    """资源错误"""


class DataDownloadError(MIABaseException):
    """数据下载错误"""
