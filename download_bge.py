import os
from huggingface_hub import snapshot_download

PROJECT_ROOT = "/root/autodl-tmp/医疗健康agent"

os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
os.environ["HF_HOME"] = f"{PROJECT_ROOT}/hf_cache"
os.environ["TRANSFORMERS_CACHE"] = f"{PROJECT_ROOT}/hf_cache"

save_path = f"{PROJECT_ROOT}/models/bge-small-zh-v1.5"
os.makedirs(save_path, exist_ok=True)

snapshot_download(
    repo_id="BAAI/bge-small-zh-v1.5",
    local_dir=save_path,
    local_dir_use_symlinks=False,
    resume_download=True
)

print("BGE 模型下载完成：", save_path)
