#!/usr/bin/env python3
"""
Windows系统健康检查器

作为🔧 DevOps Engineer，我负责执行全面的Windows系统健康检查，
包括系统文件完整性、注册表健康、磁盘错误和安全更新状态。
"""

import subprocess
import json
import re
import psutil
from datetime import datetime
from pathlib import Path

class WindowsSystemHealthChecker:
    """Windows系统健康检查器"""
    
    def __init__(self):
        self.health_report = {
            "system_files": {},
            "registry_health": {},
            "disk_health": {},
            "security_updates": {},
            "performance_metrics": {},
            "recommendations": []
        }
        
    def check_system_file_integrity(self):
        """检查系统文件完整性"""
        print("🔍 检查系统文件完整性...")
        
        try:
            # 运行SFC扫描
            print("   运行系统文件检查器 (SFC)...")
            sfc_result = subprocess.run(
                ["sfc", "/scannow"],
                capture_output=True,
                text=True,
                shell=True,
                encoding='utf-8',
                errors='ignore'
            )
            
            sfc_status = "未知"
            if "Windows 资源保护未发现任何完整性冲突" in sfc_result.stdout:
                sfc_status = "健康"
            elif "Windows 资源保护发现了损坏文件" in sfc_result.stdout:
                sfc_status = "发现损坏文件"
            elif "Windows 资源保护无法执行请求的操作" in sfc_result.stdout:
                sfc_status = "需要管理员权限"
            
            # 运行DISM检查
            print("   运行部署映像服务和管理工具 (DISM)...")
            dism_result = subprocess.run(
                ["dism", "/online", "/cleanup-image", "/checkhealth"],
                capture_output=True,
                text=True,
                shell=True,
                encoding='utf-8',
                errors='ignore'
            )
            
            dism_status = "健康" if "未检测到组件存储损坏" in dism_result.stdout else "需要进一步检查"
            
            self.health_report["system_files"] = {
                "sfc_status": sfc_status,
                "dism_status": dism_status,
                "last_check": datetime.now().isoformat(),
                "details": {
                    "sfc_output": sfc_result.stdout[:500] if sfc_result.stdout else "无输出",
                    "dism_output": dism_result.stdout[:500] if dism_result.stdout else "无输出"
                }
            }
            
            print(f"   ✅ SFC状态: {sfc_status}")
            print(f"   ✅ DISM状态: {dism_status}")
            
        except Exception as e:
            print(f"   ❌ 系统文件检查失败: {e}")
            self.health_report["system_files"] = {
                "status": "检查失败",
                "error": str(e),
                "recommendation": "请以管理员身份运行"
            }
    
    def check_registry_health(self):
        """检查注册表健康状态"""
        print("🔍 检查注册表健康状态...")
        
        try:
            # 检查注册表大小
            registry_info = {}
            
            # 获取注册表基本信息
            reg_query_result = subprocess.run(
                ["reg", "query", "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion"],
                capture_output=True,
                text=True,
                shell=True
            )
            
            if reg_query_result.returncode == 0:
                registry_info["accessibility"] = "正常"
            else:
                registry_info["accessibility"] = "异常"
            
            # 检查常见的注册表问题
            common_issues = []
            
            # 检查启动项
            startup_result = subprocess.run(
                ["reg", "query", "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run"],
                capture_output=True,
                text=True,
                shell=True
            )
            
            if startup_result.returncode == 0:
                startup_entries = len(startup_result.stdout.split('\n')) - 3
                registry_info["startup_entries"] = startup_entries
                if startup_entries > 20:
                    common_issues.append("启动项过多，可能影响启动速度")
            
            self.health_report["registry_health"] = {
                "status": "健康" if not common_issues else "需要优化",
                "accessibility": registry_info.get("accessibility", "未知"),
                "startup_entries": registry_info.get("startup_entries", 0),
                "issues": common_issues,
                "last_check": datetime.now().isoformat()
            }
            
            print(f"   ✅ 注册表访问: {registry_info.get('accessibility', '未知')}")
            print(f"   ✅ 启动项数量: {registry_info.get('startup_entries', 0)}")
            
        except Exception as e:
            print(f"   ❌ 注册表检查失败: {e}")
            self.health_report["registry_health"] = {
                "status": "检查失败",
                "error": str(e)
            }
    
    def check_disk_health(self):
        """检查磁盘错误"""
        print("🔍 检查磁盘健康状态...")
        
        try:
            disk_info = {}
            
            # 获取磁盘使用情况
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disk_info[partition.device] = {
                        "total": usage.total,
                        "used": usage.used,
                        "free": usage.free,
                        "percent": round((usage.used / usage.total) * 100, 2),
                        "filesystem": partition.fstype
                    }
                except PermissionError:
                    continue
            
            # 检查磁盘健康状态 (SMART)
            smart_status = {}
            try:
                wmic_result = subprocess.run(
                    ["wmic", "diskdrive", "get", "status"],
                    capture_output=True,
                    text=True,
                    shell=True
                )
                
                if "OK" in wmic_result.stdout:
                    smart_status["overall"] = "健康"
                else:
                    smart_status["overall"] = "需要检查"
                    
            except Exception:
                smart_status["overall"] = "无法检测"
            
            # 分析磁盘使用情况
            issues = []
            for device, info in disk_info.items():
                if info["percent"] > 90:
                    issues.append(f"磁盘 {device} 使用率过高 ({info['percent']}%)")
                elif info["percent"] > 80:
                    issues.append(f"磁盘 {device} 使用率较高 ({info['percent']}%)")
            
            self.health_report["disk_health"] = {
                "status": "健康" if not issues else "需要关注",
                "smart_status": smart_status["overall"],
                "disk_usage": disk_info,
                "issues": issues,
                "last_check": datetime.now().isoformat()
            }
            
            print(f"   ✅ SMART状态: {smart_status['overall']}")
            for device, info in disk_info.items():
                print(f"   ✅ {device} 使用率: {info['percent']}%")
                
        except Exception as e:
            print(f"   ❌ 磁盘检查失败: {e}")
            self.health_report["disk_health"] = {
                "status": "检查失败",
                "error": str(e)
            }
    
    def check_security_updates(self):
        """检查安全更新状态"""
        print("🔍 检查安全更新状态...")
        
        try:
            # 检查Windows Update状态
            update_info = {}
            
            # 使用PowerShell检查更新
            ps_command = """
            Get-WUList -MicrosoftUpdate | Select-Object Title, Size, @{Name="Category";Expression={$_.Categories | Select-Object -First 1 | Select-Object -ExpandProperty Name}} | ConvertTo-Json
            """
            
            try:
                ps_result = subprocess.run(
                    ["powershell", "-Command", ps_command],
                    capture_output=True,
                    text=True,
                    shell=True,
                    timeout=30
                )
                
                if ps_result.returncode == 0 and ps_result.stdout.strip():
                    update_info["powershell_check"] = "成功"
                else:
                    update_info["powershell_check"] = "需要PSWindowsUpdate模块"
            except subprocess.TimeoutExpired:
                update_info["powershell_check"] = "超时"
            except Exception:
                update_info["powershell_check"] = "失败"
            
            # 检查Windows Defender状态
            try:
                defender_result = subprocess.run(
                    ["powershell", "-Command", "Get-MpComputerStatus | Select-Object AntivirusEnabled, RealTimeProtectionEnabled | ConvertTo-Json"],
                    capture_output=True,
                    text=True,
                    shell=True,
                    timeout=10
                )
                
                if defender_result.returncode == 0:
                    defender_info = json.loads(defender_result.stdout)
                    update_info["defender_status"] = {
                        "antivirus_enabled": defender_info.get("AntivirusEnabled", False),
                        "realtime_protection": defender_info.get("RealTimeProtectionEnabled", False)
                    }
                else:
                    update_info["defender_status"] = "无法检测"
                    
            except Exception:
                update_info["defender_status"] = "检查失败"
            
            # 检查系统版本和构建号
            try:
                version_result = subprocess.run(
                    ["systeminfo"],
                    capture_output=True,
                    text=True,
                    shell=True,
                    timeout=15
                )
                
                if version_result.returncode == 0:
                    version_info = version_result.stdout
                    # 提取Windows版本信息
                    os_name_match = re.search(r"OS 名称:\s*(.+)", version_info)
                    os_version_match = re.search(r"OS 版本:\s*(.+)", version_info)
                    
                    update_info["system_info"] = {
                        "os_name": os_name_match.group(1).strip() if os_name_match else "未知",
                        "os_version": os_version_match.group(1).strip() if os_version_match else "未知"
                    }
                    
            except Exception:
                update_info["system_info"] = "无法获取"
            
            self.health_report["security_updates"] = {
                "status": "需要手动检查",
                "last_check": datetime.now().isoformat(),
                "update_check": update_info.get("powershell_check", "未检查"),
                "defender_status": update_info.get("defender_status", "未知"),
                "system_info": update_info.get("system_info", {}),
                "recommendation": "建议手动检查Windows Update和Windows Defender状态"
            }
            
            print(f"   ✅ 更新检查: {update_info.get('powershell_check', '未检查')}")
            print(f"   ✅ Defender状态: {update_info.get('defender_status', '未知')}")
            
        except Exception as e:
            print(f"   ❌ 安全更新检查失败: {e}")
            self.health_report["security_updates"] = {
                "status": "检查失败",
                "error": str(e)
            }
    
    def collect_performance_metrics(self):
        """收集性能指标"""
        print("📊 收集系统性能指标...")
        
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # 内存使用情况
            memory = psutil.virtual_memory()
            
            # 磁盘I/O
            disk_io = psutil.disk_io_counters()
            
            # 网络I/O
            network_io = psutil.net_io_counters()
            
            # 进程数量
            process_count = len(psutil.pids())
            
            self.health_report["performance_metrics"] = {
                "cpu": {
                    "usage_percent": cpu_percent,
                    "core_count": cpu_count,
                    "status": "正常" if cpu_percent < 80 else "高负载"
                },
                "memory": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "usage_percent": memory.percent,
                    "status": "正常" if memory.percent < 80 else "内存不足"
                },
                "disk_io": {
                    "read_bytes": disk_io.read_bytes if disk_io else 0,
                    "write_bytes": disk_io.write_bytes if disk_io else 0
                },
                "network_io": {
                    "bytes_sent": network_io.bytes_sent if network_io else 0,
                    "bytes_recv": network_io.bytes_recv if network_io else 0
                },
                "processes": {
                    "count": process_count,
                    "status": "正常" if process_count < 200 else "进程较多"
                },
                "timestamp": datetime.now().isoformat()
            }
            
            print(f"   ✅ CPU使用率: {cpu_percent}%")
            print(f"   ✅ 内存使用率: {memory.percent}%")
            print(f"   ✅ 进程数量: {process_count}")
            
        except Exception as e:
            print(f"   ❌ 性能指标收集失败: {e}")
            self.health_report["performance_metrics"] = {
                "status": "收集失败",
                "error": str(e)
            }
    
    def generate_recommendations(self):
        """生成优化建议"""
        print("💡 生成系统优化建议...")
        
        recommendations = []
        
        # 基于检查结果生成建议
        if self.health_report.get("system_files", {}).get("sfc_status") == "发现损坏文件":
            recommendations.append("运行 'sfc /scannow' 修复系统文件")
        
        if self.health_report.get("registry_health", {}).get("startup_entries", 0) > 15:
            recommendations.append("清理不必要的启动项以提高启动速度")
        
        disk_issues = self.health_report.get("disk_health", {}).get("issues", [])
        if disk_issues:
            recommendations.extend(disk_issues)
            recommendations.append("考虑清理磁盘空间或扩展存储")
        
        memory_status = self.health_report.get("performance_metrics", {}).get("memory", {}).get("status")
        if memory_status == "内存不足":
            recommendations.append("考虑关闭不必要的程序或增加内存")
        
        cpu_status = self.health_report.get("performance_metrics", {}).get("cpu", {}).get("status")
        if cpu_status == "高负载":
            recommendations.append("检查高CPU使用率的进程")
        
        # 通用建议
        recommendations.extend([
            "定期运行Windows Update检查安全更新",
            "保持Windows Defender实时保护开启",
            "定期清理临时文件和回收站",
            "考虑使用磁盘清理工具释放空间",
            "定期重启系统以清理内存和临时文件"
        ])
        
        self.health_report["recommendations"] = recommendations
        
        print("   💡 生成了以下优化建议:")
        for i, rec in enumerate(recommendations[:5], 1):
            print(f"   {i}. {rec}")
        if len(recommendations) > 5:
            print(f"   ... 还有 {len(recommendations) - 5} 条建议")
    
    def generate_health_report(self):
        """生成健康检查报告"""
        print("📊 生成系统健康报告...")
        
        # 计算总体健康评分
        health_score = 100
        issues_count = 0
        
        # 系统文件检查
        if self.health_report.get("system_files", {}).get("sfc_status") != "健康":
            health_score -= 20
            issues_count += 1
        
        # 注册表健康
        if self.health_report.get("registry_health", {}).get("status") != "健康":
            health_score -= 10
            issues_count += 1
        
        # 磁盘健康
        if self.health_report.get("disk_health", {}).get("issues"):
            health_score -= 15
            issues_count += 1
        
        # 性能指标
        memory_status = self.health_report.get("performance_metrics", {}).get("memory", {}).get("status")
        cpu_status = self.health_report.get("performance_metrics", {}).get("cpu", {}).get("status")
        
        if memory_status != "正常":
            health_score -= 15
            issues_count += 1
        
        if cpu_status != "正常":
            health_score -= 10
            issues_count += 1
        
        health_score = max(0, health_score)  # 确保不低于0
        
        report = {
            "metadata": {
                "check_date": datetime.now().isoformat(),
                "checker": "🔧 DevOps Engineer",
                "system_platform": "Windows"
            },
            "overall_health": {
                "score": health_score,
                "status": "优秀" if health_score >= 90 else "良好" if health_score >= 70 else "需要关注" if health_score >= 50 else "需要立即处理",
                "issues_count": issues_count
            },
            "detailed_results": self.health_report,
            "summary": {
                "system_files": self.health_report.get("system_files", {}).get("sfc_status", "未检查"),
                "registry": self.health_report.get("registry_health", {}).get("status", "未检查"),
                "disk_health": self.health_report.get("disk_health", {}).get("status", "未检查"),
                "security": self.health_report.get("security_updates", {}).get("status", "未检查"),
                "performance": "正常" if health_score >= 70 else "需要优化"
            }
        }
        
        # 保存报告
        report_path = Path(".kiro/reports/windows_system_health_report.json")
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 健康报告已保存到: {report_path}")
        return report
    
    def execute_health_check(self):
        """执行完整的健康检查"""
        print("🔧 开始Windows系统健康检查...")
        print("=" * 60)
        
        try:
            # 1. 系统文件完整性检查
            self.check_system_file_integrity()
            
            # 2. 注册表健康检查
            self.check_registry_health()
            
            # 3. 磁盘错误检查
            self.check_disk_health()
            
            # 4. 安全更新状态检查
            self.check_security_updates()
            
            # 5. 收集性能指标
            self.collect_performance_metrics()
            
            # 6. 生成优化建议
            self.generate_recommendations()
            
            # 7. 生成健康报告
            report = self.generate_health_report()
            
            print("=" * 60)
            print("🎉 Windows系统健康检查完成!")
            print(f"📊 总体健康评分: {report['overall_health']['score']}/100")
            print(f"✅ 系统状态: {report['overall_health']['status']}")
            print(f"⚠️ 发现问题: {report['overall_health']['issues_count']} 个")
            
            return True
            
        except Exception as e:
            print(f"❌ 健康检查过程中出现错误: {str(e)}")
            return False

def main():
    """主函数"""
    print("🔧 Windows系统健康检查器")
    print("作为DevOps Engineer，我将执行全面的系统健康检查")
    print()
    
    checker = WindowsSystemHealthChecker()
    success = checker.execute_health_check()
    
    if success:
        print("\n🎯 系统健康检查完成!")
        print("💡 请查看生成的报告了解详细信息和优化建议")
    else:
        print("\n⚠️ 健康检查过程中遇到问题")

if __name__ == "__main__":
    main()