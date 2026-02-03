#!/usr/bin/env python3
"""
Windows性能分析器

作为🔧 DevOps Engineer，我负责执行全面的Windows性能分析，
包括CPU和内存使用率、磁盘分析、启动项优化和开发环境优化建议。
"""

import subprocess
import json
import psutil
import time
from datetime import datetime
from pathlib import Path

class WindowsPerformanceAnalyzer:
    """Windows性能分析器"""
    
    def __init__(self):
        self.analysis_report = {
            "cpu_memory_analysis": {},
            "disk_analysis": {},
            "startup_optimization": {},
            "development_environment": {},
            "optimization_recommendations": []
        }
        
    def analyze_cpu_memory_usage(self):
        """分析CPU和内存使用率"""
        print("📊 分析CPU和内存使用情况...")
        
        try:
            # CPU分析
            cpu_percent = psutil.cpu_percent(interval=2)
            cpu_count_logical = psutil.cpu_count(logical=True)
            cpu_count_physical = psutil.cpu_count(logical=False)
            cpu_freq = psutil.cpu_freq()
            
            # 获取CPU使用率历史（多次采样）
            cpu_samples = []
            for i in range(5):
                cpu_samples.append(psutil.cpu_percent(interval=1))
                time.sleep(0.2)
            
            avg_cpu = sum(cpu_samples) / len(cpu_samples)
            max_cpu = max(cpu_samples)
            
            # 内存分析
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # 获取内存使用最多的进程
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'memory_percent', 'cpu_percent']):
                try:
                    processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            # 按内存使用排序
            top_memory_processes = sorted(processes, key=lambda x: x['memory_percent'] or 0, reverse=True)[:10]
            top_cpu_processes = sorted(processes, key=lambda x: x['cpu_percent'] or 0, reverse=True)[:10]
            
            self.analysis_report["cpu_memory_analysis"] = {
                "cpu": {
                    "current_usage": cpu_percent,
                    "average_usage": round(avg_cpu, 2),
                    "peak_usage": max_cpu,
                    "logical_cores": cpu_count_logical,
                    "physical_cores": cpu_count_physical,
                    "frequency_mhz": cpu_freq.current if cpu_freq else "未知",
                    "status": "正常" if avg_cpu < 70 else "高负载" if avg_cpu < 90 else "严重负载"
                },
                "memory": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "usage_percent": memory.percent,
                    "status": "正常" if memory.percent < 70 else "紧张" if memory.percent < 85 else "严重不足"
                },
                "swap": {
                    "total_gb": round(swap.total / (1024**3), 2),
                    "used_gb": round(swap.used / (1024**3), 2),
                    "usage_percent": swap.percent
                },
                "top_memory_processes": top_memory_processes[:5],
                "top_cpu_processes": top_cpu_processes[:5],
                "timestamp": datetime.now().isoformat()
            }
            
            print(f"   ✅ CPU平均使用率: {avg_cpu}% (峰值: {max_cpu}%)")
            print(f"   ✅ 内存使用率: {memory.percent}% ({memory.used / (1024**3):.1f}GB / {memory.total / (1024**3):.1f}GB)")
            print(f"   ✅ CPU状态: {self.analysis_report['cpu_memory_analysis']['cpu']['status']}")
            print(f"   ✅ 内存状态: {self.analysis_report['cpu_memory_analysis']['memory']['status']}")
            
        except Exception as e:
            print(f"   ❌ CPU和内存分析失败: {e}")
            self.analysis_report["cpu_memory_analysis"] = {
                "status": "分析失败",
                "error": str(e)
            }
    
    def analyze_disk_space_fragmentation(self):
        """分析磁盘空间和碎片"""
        print("💾 分析磁盘空间和碎片情况...")
        
        try:
            disk_info = {}
            
            # 获取所有磁盘分区信息
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    
                    # 磁盘I/O统计
                    disk_io = psutil.disk_io_counters(perdisk=True)
                    
                    disk_info[partition.device] = {
                        "mountpoint": partition.mountpoint,
                        "filesystem": partition.fstype,
                        "total_gb": round(usage.total / (1024**3), 2),
                        "used_gb": round(usage.used / (1024**3), 2),
                        "free_gb": round(usage.free / (1024**3), 2),
                        "usage_percent": round((usage.used / usage.total) * 100, 2),
                        "status": self._get_disk_status(usage.used / usage.total)
                    }
                    
                except PermissionError:
                    disk_info[partition.device] = {
                        "status": "无权限访问",
                        "mountpoint": partition.mountpoint
                    }
                    continue
            
            # 检查磁盘碎片（Windows特定）
            fragmentation_info = {}
            try:
                # 使用defrag命令检查碎片
                for drive in ['C:', 'D:', 'E:']:
                    try:
                        defrag_result = subprocess.run(
                            ["defrag", drive, "/A"],
                            capture_output=True,
                            text=True,
                            shell=True,
                            timeout=30
                        )
                        
                        if defrag_result.returncode == 0:
                            # 解析碎片信息
                            output = defrag_result.stdout
                            if "碎片" in output or "fragmented" in output.lower():
                                fragmentation_info[drive] = "需要整理"
                            else:
                                fragmentation_info[drive] = "良好"
                        else:
                            fragmentation_info[drive] = "无法检测"
                            
                    except (subprocess.TimeoutExpired, FileNotFoundError):
                        fragmentation_info[drive] = "检测超时或工具不可用"
                        
            except Exception:
                fragmentation_info = {"status": "碎片检测不可用"}
            
            # 磁盘I/O性能分析
            try:
                disk_io_start = psutil.disk_io_counters()
                time.sleep(2)
                disk_io_end = psutil.disk_io_counters()
                
                if disk_io_start and disk_io_end:
                    read_speed = (disk_io_end.read_bytes - disk_io_start.read_bytes) / 2  # bytes/sec
                    write_speed = (disk_io_end.write_bytes - disk_io_start.write_bytes) / 2
                    
                    io_performance = {
                        "read_speed_mbps": round(read_speed / (1024**2), 2),
                        "write_speed_mbps": round(write_speed / (1024**2), 2),
                        "status": "正常" if read_speed < 50 * 1024**2 else "高I/O负载"
                    }
                else:
                    io_performance = {"status": "无法测量"}
                    
            except Exception:
                io_performance = {"status": "测量失败"}
            
            self.analysis_report["disk_analysis"] = {
                "partitions": disk_info,
                "fragmentation": fragmentation_info,
                "io_performance": io_performance,
                "recommendations": self._generate_disk_recommendations(disk_info),
                "timestamp": datetime.now().isoformat()
            }
            
            print("   ✅ 磁盘使用情况:")
            for device, info in disk_info.items():
                if "usage_percent" in info:
                    print(f"      {device} {info['usage_percent']}% ({info['free_gb']}GB可用)")
            
            print(f"   ✅ 碎片状态: {len([k for k, v in fragmentation_info.items() if v == '需要整理'])} 个驱动器需要整理")
            
        except Exception as e:
            print(f"   ❌ 磁盘分析失败: {e}")
            self.analysis_report["disk_analysis"] = {
                "status": "分析失败",
                "error": str(e)
            }
    
    def analyze_startup_services_optimization(self):
        """分析启动项和服务优化"""
        print("🚀 分析启动项和服务优化...")
        
        try:
            startup_info = {}
            
            # 检查启动项（注册表）
            try:
                startup_result = subprocess.run(
                    ["reg", "query", "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run"],
                    capture_output=True,
                    text=True,
                    shell=True
                )
                
                if startup_result.returncode == 0:
                    startup_entries = []
                    lines = startup_result.stdout.split('\n')
                    for line in lines:
                        if line.strip() and not line.startswith('HKEY') and '    ' in line:
                            parts = line.strip().split('    ', 2)
                            if len(parts) >= 3:
                                startup_entries.append({
                                    "name": parts[0],
                                    "type": parts[1],
                                    "path": parts[2]
                                })
                    
                    startup_info["registry_startup"] = {
                        "count": len(startup_entries),
                        "entries": startup_entries[:10],  # 只显示前10个
                        "status": "正常" if len(startup_entries) < 15 else "过多"
                    }
                else:
                    startup_info["registry_startup"] = {"status": "无法读取"}
                    
            except Exception:
                startup_info["registry_startup"] = {"status": "检查失败"}
            
            # 检查用户启动项
            try:
                user_startup_result = subprocess.run(
                    ["reg", "query", "HKCU\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run"],
                    capture_output=True,
                    text=True,
                    shell=True
                )
                
                if user_startup_result.returncode == 0:
                    user_entries = len(user_startup_result.stdout.split('\n')) - 3
                    startup_info["user_startup"] = {
                        "count": max(0, user_entries),
                        "status": "正常" if user_entries < 10 else "过多"
                    }
                else:
                    startup_info["user_startup"] = {"count": 0, "status": "无启动项"}
                    
            except Exception:
                startup_info["user_startup"] = {"status": "检查失败"}
            
            # 检查Windows服务
            try:
                services_info = []
                
                # 使用PowerShell获取服务信息
                ps_command = """
                Get-Service | Where-Object {$_.StartType -eq 'Automatic' -and $_.Status -eq 'Running'} | 
                Select-Object Name, DisplayName, Status, StartType | 
                ConvertTo-Json
                """
                
                services_result = subprocess.run(
                    ["powershell", "-Command", ps_command],
                    capture_output=True,
                    text=True,
                    shell=True,
                    timeout=15
                )
                
                if services_result.returncode == 0 and services_result.stdout.strip():
                    try:
                        services_data = json.loads(services_result.stdout)
                        if isinstance(services_data, list):
                            services_info = services_data
                        elif isinstance(services_data, dict):
                            services_info = [services_data]
                    except json.JSONDecodeError:
                        services_info = []
                
                startup_info["services"] = {
                    "auto_start_running": len(services_info),
                    "status": "正常" if len(services_info) < 100 else "服务较多",
                    "sample_services": services_info[:5]  # 显示前5个服务
                }
                
            except Exception:
                startup_info["services"] = {"status": "检查失败"}
            
            # 生成启动优化建议
            optimization_suggestions = []
            
            registry_count = startup_info.get("registry_startup", {}).get("count", 0)
            user_count = startup_info.get("user_startup", {}).get("count", 0)
            
            if registry_count > 15:
                optimization_suggestions.append("系统启动项过多，建议禁用不必要的程序")
            if user_count > 10:
                optimization_suggestions.append("用户启动项过多，建议清理")
            if len(services_info) > 120:
                optimization_suggestions.append("自动启动服务过多，建议优化")
            
            self.analysis_report["startup_optimization"] = {
                "startup_programs": startup_info,
                "optimization_suggestions": optimization_suggestions,
                "boot_time_estimate": self._estimate_boot_time(registry_count + user_count),
                "timestamp": datetime.now().isoformat()
            }
            
            print(f"   ✅ 系统启动项: {registry_count} 个")
            print(f"   ✅ 用户启动项: {user_count} 个")
            print(f"   ✅ 自动启动服务: {len(services_info)} 个")
            print(f"   ✅ 优化建议: {len(optimization_suggestions)} 条")
            
        except Exception as e:
            print(f"   ❌ 启动项和服务分析失败: {e}")
            self.analysis_report["startup_optimization"] = {
                "status": "分析失败",
                "error": str(e)
            }
    
    def analyze_development_environment(self):
        """分析PowerShell和开发环境优化"""
        print("⚡ 分析PowerShell和开发环境...")
        
        try:
            dev_env_info = {}
            
            # PowerShell版本和配置
            try:
                ps_version_result = subprocess.run(
                    ["powershell", "-Command", "$PSVersionTable | ConvertTo-Json"],
                    capture_output=True,
                    text=True,
                    shell=True,
                    timeout=10
                )
                
                if ps_version_result.returncode == 0:
                    try:
                        ps_info = json.loads(ps_version_result.stdout)
                        dev_env_info["powershell"] = {
                            "version": ps_info.get("PSVersion", "未知"),
                            "edition": ps_info.get("PSEdition", "未知"),
                            "status": "已安装"
                        }
                    except json.JSONDecodeError:
                        dev_env_info["powershell"] = {"status": "版本信息解析失败"}
                else:
                    dev_env_info["powershell"] = {"status": "未安装或不可用"}
                    
            except Exception:
                dev_env_info["powershell"] = {"status": "检查失败"}
            
            # 检查PowerShell执行策略
            try:
                policy_result = subprocess.run(
                    ["powershell", "-Command", "Get-ExecutionPolicy"],
                    capture_output=True,
                    text=True,
                    shell=True,
                    timeout=5
                )
                
                if policy_result.returncode == 0:
                    policy = policy_result.stdout.strip()
                    dev_env_info["powershell"]["execution_policy"] = policy
                    dev_env_info["powershell"]["policy_status"] = "安全" if policy in ["Restricted", "AllSigned"] else "宽松"
                    
            except Exception:
                dev_env_info["powershell"]["execution_policy"] = "无法检测"
            
            # 检查常见开发工具
            dev_tools = {
                "git": ["git", "--version"],
                "python": ["python", "--version"],
                "node": ["node", "--version"],
                "npm": ["npm", "--version"],
                "docker": ["docker", "--version"],
                "code": ["code", "--version"]
            }
            
            installed_tools = {}
            for tool, command in dev_tools.items():
                try:
                    result = subprocess.run(
                        command,
                        capture_output=True,
                        text=True,
                        shell=True,
                        timeout=5
                    )
                    
                    if result.returncode == 0:
                        version = result.stdout.strip().split('\n')[0]
                        installed_tools[tool] = {
                            "installed": True,
                            "version": version,
                            "status": "可用"
                        }
                    else:
                        installed_tools[tool] = {
                            "installed": False,
                            "status": "未安装"
                        }
                        
                except Exception:
                    installed_tools[tool] = {
                        "installed": False,
                        "status": "检查失败"
                    }
            
            dev_env_info["development_tools"] = installed_tools
            
            # 检查环境变量
            important_env_vars = ["PATH", "PYTHONPATH", "NODE_PATH", "JAVA_HOME"]
            env_vars_info = {}
            
            for var in important_env_vars:
                try:
                    result = subprocess.run(
                        ["powershell", "-Command", f"$env:{var}"],
                        capture_output=True,
                        text=True,
                        shell=True,
                        timeout=5
                    )
                    
                    if result.returncode == 0 and result.stdout.strip():
                        env_vars_info[var] = {
                            "set": True,
                            "length": len(result.stdout.strip()),
                            "status": "已配置"
                        }
                    else:
                        env_vars_info[var] = {
                            "set": False,
                            "status": "未设置"
                        }
                        
                except Exception:
                    env_vars_info[var] = {
                        "set": False,
                        "status": "检查失败"
                    }
            
            dev_env_info["environment_variables"] = env_vars_info
            
            # 生成开发环境优化建议
            dev_optimization_suggestions = []
            
            # PowerShell优化建议
            if dev_env_info.get("powershell", {}).get("execution_policy") == "Restricted":
                dev_optimization_suggestions.append("考虑设置PowerShell执行策略为RemoteSigned以支持脚本执行")
            
            # 工具安装建议
            missing_tools = [tool for tool, info in installed_tools.items() if not info.get("installed", False)]
            if missing_tools:
                dev_optimization_suggestions.append(f"建议安装缺失的开发工具: {', '.join(missing_tools)}")
            
            # 环境变量建议
            unset_vars = [var for var, info in env_vars_info.items() if not info.get("set", False)]
            if unset_vars:
                dev_optimization_suggestions.append(f"建议配置环境变量: {', '.join(unset_vars)}")
            
            self.analysis_report["development_environment"] = {
                "powershell_info": dev_env_info.get("powershell", {}),
                "development_tools": installed_tools,
                "environment_variables": env_vars_info,
                "optimization_suggestions": dev_optimization_suggestions,
                "development_readiness": len(missing_tools) == 0,
                "timestamp": datetime.now().isoformat()
            }
            
            installed_count = len([t for t in installed_tools.values() if t.get("installed", False)])
            print(f"   ✅ PowerShell状态: {dev_env_info.get('powershell', {}).get('status', '未知')}")
            print(f"   ✅ 开发工具: {installed_count}/{len(dev_tools)} 已安装")
            print(f"   ✅ 环境变量: {len([v for v in env_vars_info.values() if v.get('set', False)])}/{len(important_env_vars)} 已配置")
            print(f"   ✅ 开发环境就绪: {'是' if len(missing_tools) == 0 else '否'}")
            
        except Exception as e:
            print(f"   ❌ 开发环境分析失败: {e}")
            self.analysis_report["development_environment"] = {
                "status": "分析失败",
                "error": str(e)
            }
    
    def generate_comprehensive_recommendations(self):
        """生成综合优化建议"""
        print("💡 生成综合优化建议...")
        
        recommendations = []
        
        # CPU和内存优化建议
        cpu_status = self.analysis_report.get("cpu_memory_analysis", {}).get("cpu", {}).get("status")
        memory_status = self.analysis_report.get("cpu_memory_analysis", {}).get("memory", {}).get("status")
        
        if cpu_status == "高负载":
            recommendations.append({
                "category": "性能优化",
                "priority": "高",
                "suggestion": "CPU使用率过高，建议检查高CPU使用率的进程并考虑升级硬件",
                "action": "使用任务管理器识别和关闭不必要的进程"
            })
        
        if memory_status in ["紧张", "严重不足"]:
            recommendations.append({
                "category": "内存优化",
                "priority": "高",
                "suggestion": "内存使用率过高，建议关闭不必要的程序或增加内存",
                "action": "清理内存占用大的程序，考虑增加物理内存"
            })
        
        # 磁盘优化建议
        disk_recs = self.analysis_report.get("disk_analysis", {}).get("recommendations", [])
        for rec in disk_recs:
            recommendations.append({
                "category": "磁盘优化",
                "priority": "中",
                "suggestion": rec,
                "action": "执行磁盘清理和碎片整理"
            })
        
        # 启动优化建议
        startup_suggestions = self.analysis_report.get("startup_optimization", {}).get("optimization_suggestions", [])
        for suggestion in startup_suggestions:
            recommendations.append({
                "category": "启动优化",
                "priority": "中",
                "suggestion": suggestion,
                "action": "使用msconfig或任务管理器禁用不必要的启动项"
            })
        
        # 开发环境优化建议
        dev_suggestions = self.analysis_report.get("development_environment", {}).get("optimization_suggestions", [])
        for suggestion in dev_suggestions:
            recommendations.append({
                "category": "开发环境",
                "priority": "低",
                "suggestion": suggestion,
                "action": "配置开发工具和环境变量"
            })
        
        # 通用系统优化建议
        recommendations.extend([
            {
                "category": "系统维护",
                "priority": "中",
                "suggestion": "定期运行Windows Update检查系统更新",
                "action": "设置自动更新或定期手动检查"
            },
            {
                "category": "安全优化",
                "priority": "高",
                "suggestion": "确保Windows Defender实时保护开启",
                "action": "检查Windows安全中心设置"
            },
            {
                "category": "性能调优",
                "priority": "低",
                "suggestion": "定期重启系统以清理内存和临时文件",
                "action": "建立定期重启计划"
            },
            {
                "category": "存储优化",
                "priority": "中",
                "suggestion": "使用磁盘清理工具清理临时文件和系统垃圾",
                "action": "运行磁盘清理工具或第三方清理软件"
            }
        ])
        
        # 按优先级排序
        priority_order = {"高": 1, "中": 2, "低": 3}
        recommendations.sort(key=lambda x: priority_order.get(x["priority"], 4))
        
        self.analysis_report["optimization_recommendations"] = recommendations
        
        print(f"   💡 生成了 {len(recommendations)} 条优化建议")
        print("   📊 建议分布:")
        high_priority = len([r for r in recommendations if r["priority"] == "高"])
        medium_priority = len([r for r in recommendations if r["priority"] == "中"])
        low_priority = len([r for r in recommendations if r["priority"] == "低"])
        print(f"      高优先级: {high_priority} 条")
        print(f"      中优先级: {medium_priority} 条")
        print(f"      低优先级: {low_priority} 条")
    
    def _get_disk_status(self, usage_ratio):
        """获取磁盘状态"""
        if usage_ratio < 0.7:
            return "正常"
        elif usage_ratio < 0.85:
            return "使用率较高"
        elif usage_ratio < 0.95:
            return "空间不足"
        else:
            return "严重不足"
    
    def _generate_disk_recommendations(self, disk_info):
        """生成磁盘优化建议"""
        recommendations = []
        
        for device, info in disk_info.items():
            if "usage_percent" in info:
                if info["usage_percent"] > 90:
                    recommendations.append(f"磁盘 {device} 空间严重不足，建议立即清理")
                elif info["usage_percent"] > 80:
                    recommendations.append(f"磁盘 {device} 空间不足，建议清理不必要的文件")
        
        return recommendations
    
    def _estimate_boot_time(self, startup_count):
        """估算启动时间"""
        base_time = 30  # 基础启动时间（秒）
        additional_time = startup_count * 2  # 每个启动项增加2秒
        
        total_time = base_time + additional_time
        
        if total_time < 60:
            return f"{total_time}秒 (快速)"
        elif total_time < 120:
            return f"{total_time}秒 (正常)"
        else:
            return f"{total_time}秒 (较慢)"
    
    def generate_performance_report(self):
        """生成性能分析报告"""
        print("📊 生成Windows性能分析报告...")
        
        # 计算总体性能评分
        performance_score = 100
        
        # CPU评分
        cpu_status = self.analysis_report.get("cpu_memory_analysis", {}).get("cpu", {}).get("status")
        if cpu_status == "高负载":
            performance_score -= 20
        elif cpu_status == "严重负载":
            performance_score -= 35
        
        # 内存评分
        memory_status = self.analysis_report.get("cpu_memory_analysis", {}).get("memory", {}).get("status")
        if memory_status == "紧张":
            performance_score -= 15
        elif memory_status == "严重不足":
            performance_score -= 30
        
        # 磁盘评分
        disk_recommendations = self.analysis_report.get("disk_analysis", {}).get("recommendations", [])
        performance_score -= len(disk_recommendations) * 5
        
        # 启动项评分
        startup_suggestions = self.analysis_report.get("startup_optimization", {}).get("optimization_suggestions", [])
        performance_score -= len(startup_suggestions) * 3
        
        performance_score = max(0, performance_score)
        
        report = {
            "metadata": {
                "analysis_date": datetime.now().isoformat(),
                "analyzer": "🔧 DevOps Engineer",
                "system_platform": "Windows",
                "analysis_type": "性能分析"
            },
            "overall_performance": {
                "score": performance_score,
                "status": "优秀" if performance_score >= 90 else "良好" if performance_score >= 70 else "需要优化" if performance_score >= 50 else "需要立即优化",
                "bottlenecks": self._identify_bottlenecks()
            },
            "detailed_analysis": self.analysis_report,
            "executive_summary": {
                "cpu_status": cpu_status or "未分析",
                "memory_status": memory_status or "未分析",
                "disk_status": "正常" if not disk_recommendations else "需要关注",
                "startup_status": "正常" if not startup_suggestions else "需要优化",
                "development_readiness": self.analysis_report.get("development_environment", {}).get("development_readiness", False)
            },
            "priority_actions": [r for r in self.analysis_report.get("optimization_recommendations", []) if r.get("priority") == "高"][:5]
        }
        
        # 保存报告
        report_path = Path(".kiro/reports/windows_performance_analysis_report.json")
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 性能分析报告已保存到: {report_path}")
        return report
    
    def _identify_bottlenecks(self):
        """识别性能瓶颈"""
        bottlenecks = []
        
        cpu_status = self.analysis_report.get("cpu_memory_analysis", {}).get("cpu", {}).get("status")
        memory_status = self.analysis_report.get("cpu_memory_analysis", {}).get("memory", {}).get("status")
        
        if cpu_status in ["高负载", "严重负载"]:
            bottlenecks.append("CPU性能瓶颈")
        
        if memory_status in ["紧张", "严重不足"]:
            bottlenecks.append("内存不足瓶颈")
        
        disk_recs = self.analysis_report.get("disk_analysis", {}).get("recommendations", [])
        if disk_recs:
            bottlenecks.append("磁盘空间瓶颈")
        
        startup_count = (
            self.analysis_report.get("startup_optimization", {})
            .get("startup_programs", {})
            .get("registry_startup", {})
            .get("count", 0)
        )
        if startup_count > 20:
            bottlenecks.append("启动项过多瓶颈")
        
        return bottlenecks if bottlenecks else ["无明显瓶颈"]
    
    def execute_performance_analysis(self):
        """执行完整的性能分析"""
        print("🔧 开始Windows性能分析...")
        print("=" * 60)
        
        try:
            # 1. CPU和内存使用率分析
            self.analyze_cpu_memory_usage()
            
            # 2. 磁盘空间和碎片分析
            self.analyze_disk_space_fragmentation()
            
            # 3. 启动项和服务优化分析
            self.analyze_startup_services_optimization()
            
            # 4. PowerShell和开发环境分析
            self.analyze_development_environment()
            
            # 5. 生成综合优化建议
            self.generate_comprehensive_recommendations()
            
            # 6. 生成性能报告
            report = self.generate_performance_report()
            
            print("=" * 60)
            print("🎉 Windows性能分析完成!")
            print(f"📊 总体性能评分: {report['overall_performance']['score']}/100")
            print(f"✅ 系统状态: {report['overall_performance']['status']}")
            print(f"🎯 主要瓶颈: {', '.join(report['overall_performance']['bottlenecks'])}")
            print(f"⚡ 高优先级建议: {len(report['priority_actions'])} 条")
            
            return True
            
        except Exception as e:
            print(f"❌ 性能分析过程中出现错误: {str(e)}")
            return False

def main():
    """主函数"""
    print("🔧 Windows性能分析器")
    print("作为DevOps Engineer，我将执行全面的Windows性能分析")
    print()
    
    analyzer = WindowsPerformanceAnalyzer()
    success = analyzer.execute_performance_analysis()
    
    if success:
        print("\n🎯 Windows性能分析完成!")
        print("💡 请查看生成的报告了解详细信息和优化建议")
    else:
        print("\n⚠️ 性能分析过程中遇到问题")

if __name__ == "__main__":
    main()