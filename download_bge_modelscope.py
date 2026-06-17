import os
import shutil
from pathlib import Path
from modelscope import snapshot_download

PROJECT_ROOT = Path("/root/autodl-tmp/医疗健康agent")
TARGET_DIR = PROJECT_ROOT / "models" / "bge-small-zh-v1.5"
CACHE_DIR = PROJECT_ROOT / "modelscope_cache"

TARGET_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

print("正在从 ModelScope 下载 BGE 模型...")

model_dir = snapshot_download(
    "BAAI/bge-small-zh-v1.5",
    cache_dir=str(CACHE_DIR)
)

print("ModelScope 原始下载目录：", model_dir)
print("正在复制到项目模型目录：", TARGET_DIR)

for item in Path(model_dir).iterdir():
    target = TARGET_DIR / item.name
    if item.is_dir():
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(item, target)
    else:
        shutil.copy2(item, target)

print("✅ BGE 模型已复制完成：", TARGET_DIR)
print("目录内容：")
for p in TARGET_DIR.iterdir():
    print(" -", p.name)
