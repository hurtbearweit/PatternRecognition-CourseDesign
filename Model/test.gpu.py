import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import torch


print("CUDA 可用：", torch.cuda.is_available())
print("GPU 型号：", torch.cuda.get_device_name(0))