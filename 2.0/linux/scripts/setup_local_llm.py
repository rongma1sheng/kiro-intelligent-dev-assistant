# -*- coding: utf-8 -*-
"""
Local LLM Configuration for AMD Ryzen AI MAX+ 395 (128GB Unified Memory)

Hardware:
- CPU: AMD Ryzen AI MAX+ 395 (16 cores, 32 threads, Zen 5)
- GPU: Radeon 8060S (40 CUs, RDNA 3.5)
- Memory: 128GB LPDDR5X-8000 unified memory (up to 96GB for GPU via VGM)
- Bandwidth: 256 GB/s

Recommended Models for MIA Tri-Brain System:
1. Soldier: Qwen3-30B-A3B (MoE, 3B active) - Real-time trading, <20ms latency
2. Commander: DeepSeek-R1-Distill-Llama-70B - Strategy analysis, multi-step reasoning
3. Scholar: Qwen3-235B-A22B (MoE, 22B active) - Deep research, complex analysis

Usage:
    python scripts/setup_local_llm.py
"""

import sys
import subprocess
import platform
from pathlib import Path
from dataclasses import dataclass
from typing import List


@dataclass
class ModelConfig:
    """Model configuration"""
    name: str
    file: str
    size_gb: float
    repo: str
    quant: str
    active_params: str
    use_case: str
    recommended: bool
    note: str


# Recommended models for MIA quantitative trading system
RECOMMENDED_MODELS: List[ModelConfig] = [
    # Soldier - Fast System (Real-time trading)
    ModelConfig(
        name="Qwen3-30B-A3B-Instruct",
        file="Qwen3-30B-A3B-Instruct-Q5_K_M.gguf",
        size_gb=19,
        repo="Qwen/Qwen3-30B-A3B-Instruct-GGUF",
        quant="Q5_K_M",
        active_params="3B (MoE)",
        use_case="Soldier - Real-time trading, low latency (<20ms P99)",
        recommended=True,
        note="TOP PICK for Soldier! Only 3B active params, ultra-fast, GPT-4o level quality"
    ),
    # Commander - Strategy Analysis
    ModelConfig(
        name="DeepSeek-R1-Distill-Llama-70B",
        file="DeepSeek-R1-Distill-Llama-70B-Q4_K_M.gguf",
        size_gb=43,
        repo="unsloth/DeepSeek-R1-Distill-Llama-70B-GGUF",
        quant="Q4_K_M",
        active_params="70B (Dense)",
        use_case="Commander - Strategy analysis, multi-step reasoning, risk assessment",
        recommended=True,
        note="DeepSeek-R1 distilled, o1-level reasoning capability"
    ),
    # Scholar - Deep Research
    ModelConfig(
        name="Qwen3-235B-A22B-Instruct",
        file="Qwen3-235B-A22B-Instruct-Q4_K_M.gguf",
        size_gb=112,
        repo="Qwen/Qwen3-235B-A22B-Instruct-GGUF",
        quant="Q4_K_M",
        active_params="22B (MoE)",
        use_case="Scholar - Factor research, theory analysis, complex reasoning",
        recommended=True,
        note="TOP PICK! 128GB perfect match, GPT-4o/o1 level reasoning"
    ),
    # Alternative models
    ModelConfig(
        name="DeepSeek-R1-Distill-Qwen-32B",
        file="DeepSeek-R1-Distill-Qwen-32B-Q5_K_M.gguf",
        size_gb=24,
        repo="unsloth/DeepSeek-R1-Distill-Qwen-32B-GGUF",
        quant="Q5_K_M",
        active_params="32B (Dense)",
        use_case="Commander (Alt) - Balanced reasoning and speed",
        recommended=False,
        note="Alternative: faster but slightly weaker reasoning"
    ),
    ModelConfig(
        name="Qwen2.5-72B-Instruct",
        file="qwen2.5-72b-instruct-q5_k_m.gguf",
        size_gb=55,
        repo="Qwen/Qwen2.5-72B-Instruct-GGUF",
        quant="Q5_K_M",
        active_params="72B (Dense)",
        use_case="General - High quality Chinese understanding, financial text analysis",
        recommended=False,
        note="Alternative: Qwen2.5 series best, excellent Chinese capability"
    ),
]


def check_system():
    """Check system environment"""
    print("=" * 70)
    print("System Check - AMD Ryzen AI MAX+ 395")
    print("=" * 70)
    
    print(f"OS: {platform.system()} {platform.release()}")
    print(f"Python: {sys.version.split()[0]}")
    print(f"Architecture: {platform.machine()}")
    
    # Get CPU info
    try:
        result = subprocess.run(
            ["powershell", "-Command", 
             "Get-CimInstance Win32_Processor | Select-Object -ExpandProperty Name"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            cpu_name = result.stdout.strip()
            print(f"CPU: {cpu_name}")
            if "RYZEN AI MAX" in cpu_name.upper():
                print("  [OK] AMD Ryzen AI MAX+ processor detected")
    except Exception as e:
        print(f"  [WARN] CPU detection failed: {e}")
    
    # Get memory info
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "(Get-CimInstance Win32_PhysicalMemory | Measure-Object -Property Capacity -Sum).Sum / 1GB"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            memory_gb = float(result.stdout.strip())
            print(f"Memory: {memory_gb:.0f} GB unified")
            if memory_gb >= 128:
                print("  [OK] 128GB - Can run 235B parameter models")
            elif memory_gb >= 64:
                print("  [OK] 64GB - Can run 70B parameter models")
    except Exception as e:
        print(f"  [WARN] Memory detection failed: {e}")
    
    # Get GPU info
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            gpu_name = result.stdout.strip()
            print(f"GPU: {gpu_name}")
            if "8060S" in gpu_name or "RADEON" in gpu_name.upper():
                print("  [OK] AMD Radeon integrated GPU detected")
    except Exception as e:
        print(f"  [WARN] GPU detection failed: {e}")
    
    # Check Vulkan
    print()
    try:
        result = subprocess.run(
            ["vulkaninfo", "--summary"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            print("Vulkan: [OK] Installed")
            for line in result.stdout.split('\n'):
                if 'deviceName' in line:
                    print(f"  {line.strip()}")
        else:
            print("Vulkan: [WARN] Not configured properly")
            print("  Please install AMD Adrenalin Edition 25.8.1 WHQL driver")
    except FileNotFoundError:
        print("Vulkan: [X] Not found")
        print("  Please install AMD Adrenalin Edition 25.8.1 WHQL driver")
        print("  Download: https://www.amd.com/en/support")
    except Exception as e:
        print(f"Vulkan: [WARN] Check failed: {e}")
    
    print()


def verify_installation():
    """Verify llama-cpp-python installation"""
    print("=" * 70)
    print("Verify llama-cpp-python Installation")
    print("=" * 70)
    
    try:
        from llama_cpp import Llama
        import llama_cpp
        version = getattr(llama_cpp, '__version__', 'unknown')
        print(f"llama_cpp: [OK] Installed (version: {version})")
        return True
    except ImportError as e:
        print(f"llama_cpp: [X] Not installed")
        print()
        print("Install command:")
        print("  set CMAKE_ARGS=-DGGML_VULKAN=on")
        print("  pip install llama-cpp-python --force-reinstall --no-cache-dir")
        return False
    
    print()


def show_model_recommendations():
    """Show model recommendations"""
    print("=" * 70)
    print("MIA Tri-Brain System - Model Recommendations (128GB Unified Memory)")
    print("=" * 70)
    
    model_dir = Path("D:/MIA_Data/models")
    
    # Show architecture diagram
    print("""
+======================================================================+
|                    MIA Tri-Brain Architecture                        |
+======================================================================+
|                                                                      |
|  +------------------+                                                |
|  |     Scholar      |  Qwen3-235B-A22B (22B active, MoE)             |
|  |  Deep Research   |  - Factor research, theory analysis           |
|  |                  |  - Complex reasoning, long context            |
|  +--------+---------+  - Latency: No strict requirement             |
|           |                                                          |
|  +--------v---------+                                                |
|  |    Commander     |  DeepSeek-R1-70B or Qwen3-235B                 |
|  | Strategy Analysis|  - Strategy analysis, risk assessment         |
|  |                  |  - Multi-step reasoning, decision validation  |
|  +--------+---------+  - Latency: < 5s                              |
|           |                                                          |
|  +--------v---------+                                                |
|  |     Soldier      |  Qwen3-30B-A3B (3B active, MoE) [BEST]         |
|  |  Fast Decision   |  - Real-time trading decisions                |
|  |                  |  - Ultra-low latency (<20ms P99)              |
|  +------------------+  - Hot standby support                        |
|                                                                      |
+======================================================================+

Memory Allocation (128GB):
- Soldier (Qwen3-30B-A3B Q5): ~19GB (always loaded)
- Commander (on-demand): ~43-112GB
- Scholar (on-demand): ~112GB
- System/Context cache: ~16GB

Expected Performance (256GB/s bandwidth):
- Qwen3-30B-A3B: ~20-25 tokens/s
- Qwen3-235B-A22B: ~5-8 tokens/s
- DeepSeek-R1-70B: ~8-12 tokens/s
""")
    
    # Show recommended models
    print("=" * 70)
    print("Recommended Models")
    print("=" * 70)
    
    for model in RECOMMENDED_MODELS:
        if not model.recommended:
            continue
        
        status = "[Downloaded]" if (model_dir / model.file).exists() else "[To Download]"
        
        print(f"\n*** {model.name} ***")
        print(f"    File: {model.file}")
        print(f"    Size: {model.size_gb:.0f} GB ({model.quant})")
        print(f"    Active Params: {model.active_params}")
        print(f"    Use Case: {model.use_case}")
        print(f"    Note: {model.note}")
        print(f"    Status: {status}")
    
    # Show alternative models
    print("\n" + "-" * 70)
    print("Alternative Models")
    print("-" * 70)
    
    for model in RECOMMENDED_MODELS:
        if model.recommended:
            continue
        
        status = "[Downloaded]" if (model_dir / model.file).exists() else "[To Download]"
        
        print(f"\n    {model.name}")
        print(f"    File: {model.file}")
        print(f"    Size: {model.size_gb:.0f} GB | {model.active_params}")
        print(f"    Note: {model.note}")
        print(f"    Status: {status}")


def show_download_commands():
    """Show download commands"""
    print("\n" + "=" * 70)
    print("Download Commands")
    print("=" * 70)
    
    model_dir = Path("D:/MIA_Data/models")
    model_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\nModel directory: {model_dir}")
    print("\n# Install huggingface_hub first")
    print("pip install huggingface_hub")
    
    print("\n# 1. Soldier Model (19GB) - Download first!")
    print("huggingface-cli download Qwen/Qwen3-30B-A3B-Instruct-GGUF \\")
    print("  Qwen3-30B-A3B-Instruct-Q5_K_M.gguf \\")
    print("  --local-dir D:/MIA_Data/models")
    
    print("\n# 2. Commander Model (43GB)")
    print("huggingface-cli download unsloth/DeepSeek-R1-Distill-Llama-70B-GGUF \\")
    print("  DeepSeek-R1-Distill-Llama-70B-Q4_K_M.gguf \\")
    print("  --local-dir D:/MIA_Data/models")
    
    print("\n# 3. Scholar Model (112GB)")
    print("huggingface-cli download Qwen/Qwen3-235B-A22B-Instruct-GGUF \\")
    print("  Qwen3-235B-A22B-Instruct-Q4_K_M.gguf \\")
    print("  --local-dir D:/MIA_Data/models")
    
    print("\n# Or download directly from HuggingFace:")
    print("  https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-GGUF")
    print("  https://huggingface.co/unsloth/DeepSeek-R1-Distill-Llama-70B-GGUF")
    print("  https://huggingface.co/Qwen/Qwen3-235B-A22B-Instruct-GGUF")


def show_next_steps():
    """Show next steps"""
    print("\n" + "=" * 70)
    print("Next Steps - LM Studio (AMD Recommended)")
    print("=" * 70)
    print("""
1. Download and install LM Studio:
   https://lmstudio.ai/

2. In LM Studio, download model:
   - Search: Qwen3-30B-A3B-Instruct-GGUF
   - Select: Q5_K_M quantization (~19GB)

3. Start local server in LM Studio:
   - Load the model
   - Go to "Local Server" tab
   - Click "Start Server" (default port: 1234)

4. Update .env file:
   LM_STUDIO_API_URL=http://localhost:1234/v1
   LM_STUDIO_MODEL=qwen3-30b-a3b-instruct

5. Test the connection:
   curl http://localhost:1234/v1/models

Optional: Install AMD Adrenalin Edition 25.8.1 WHQL driver for 96GB VGM
   https://www.amd.com/en/support
""")


def main():
    """Main function"""
    print()
    print("=" * 70)
    print("MIA Local LLM Configuration")
    print("AMD Ryzen AI MAX+ 395 (128GB Unified Memory)")
    print("llama-cpp-python + Vulkan")
    print("=" * 70)
    print()
    
    # 1. Check system
    check_system()
    
    # 2. Verify installation
    verify_installation()
    
    # 3. Show model recommendations
    show_model_recommendations()
    
    # 4. Show download commands
    show_download_commands()
    
    # 5. Show next steps
    show_next_steps()
    
    print("=" * 70)
    print("Configuration Complete!")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()
