"""Existing IF-YOLO modules required by the week18 model YAML files."""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class IPFA(nn.Module):
    """Information-Preserving Feature Aggregation downsampling."""

    def __init__(self, c1: int, c2: int):
        super().__init__()
        self.conv_3x3_dw = nn.Conv2d(c1, c1, 3, 1, 1, bias=False)
        self.conv_1x1_pw = nn.Conv2d(c1 * 4, c2, 1, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.conv_3x3_dw(x)
        parts = (
            x[:, :, 0::2, 0::2],
            x[:, :, 1::2, 0::2],
            x[:, :, 0::2, 1::2],
            x[:, :, 1::2, 1::2],
        )
        return self.conv_1x1_pw(torch.cat(parts, dim=1))


class _CRC(nn.Module):
    def __init__(self, channels: int):
        super().__init__()
        self.conv1 = nn.Conv2d(channels, channels, 3, 1, 1)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = nn.Conv2d(channels, channels, 3, 1, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.conv2(self.relu(self.conv1(x)))


class _CCSM(nn.Module):
    def __init__(self, channels: int):
        super().__init__()
        self.crc_a = _CRC(channels)
        self.crc_m = _CRC(channels)
        self.avg_pool = nn.AdaptiveAvgPool2d(1)
        self.max_pool = nn.AdaptiveMaxPool2d(1)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        w = self.sigmoid(self.crc_a(self.avg_pool(x)) + self.crc_m(self.max_pool(x)))
        return x * w


class _SCSM(nn.Module):
    def __init__(self, channels: int, levels: int = 3):
        super().__init__()
        self.conv3_list = nn.ModuleList(nn.Conv2d(channels, 8, 3, 1, 1) for _ in range(levels))
        self.conv1 = nn.Conv2d(8 * levels, levels, 1, 1)
        self.softmax = nn.Softmax(dim=1)

    def forward(self, features: list[torch.Tensor]) -> torch.Tensor:
        attn = self.softmax(self.conv1(torch.cat([conv(x) for conv, x in zip(self.conv3_list, features)], dim=1)))
        return torch.cat([x * attn[:, i : i + 1] for i, x in enumerate(features)], dim=1)


class CSFM(nn.Module):
    """Original CSFM used by the basic IF-YOLO structure."""

    def __init__(self, channels: list[int]):
        super().__init__()
        shallow, middle, deep = channels
        self.conv_downsample = nn.Conv2d(shallow, shallow, 3, 2, 1)
        self.conv_align_shallow = nn.Conv2d(shallow, middle, 1, 1)
        self.conv_align_deep = nn.Conv2d(deep, middle, 1, 1)
        fused = middle * 3
        self.ccsm = _CCSM(fused)
        self.scsm = _SCSM(middle)
        self.out_conv = nn.Conv2d(fused, middle, 1, 1)

    def forward(self, x: list[torch.Tensor]) -> torch.Tensor:
        shallow, middle, deep = x
        shallow = self.conv_align_shallow(self.conv_downsample(shallow))
        deep = F.interpolate(deep, size=middle.shape[-2:], mode="bilinear", align_corners=False)
        deep = self.conv_align_deep(deep)
        features = [shallow, middle, deep]
        return self.out_conv(self.ccsm(torch.cat(features, 1)) + self.scsm(features))


class _ECABlock(nn.Module):
    def __init__(self, channels: int, k_size: int = 3):
        super().__init__()
        self.conv = nn.Conv1d(1, 1, kernel_size=k_size, padding=(k_size - 1) // 2, bias=False)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        y = self.conv(x.squeeze(-1).transpose(-1, -2)).transpose(-1, -2).unsqueeze(-1)
        return self.sigmoid(y)


class CSFMLite(nn.Module):
    """Lightweight CSFM used by the final candidate models."""

    def __init__(self, channels: list[int]):
        super().__init__()
        shallow, middle, deep = channels
        self.conv_downsample = nn.Conv2d(shallow, shallow, 3, 2, 1, groups=shallow, bias=False)
        self.conv_align_shallow = nn.Conv2d(shallow, middle, 1, 1)
        self.conv_align_deep = nn.Conv2d(deep, middle, 1, 1)
        fused = middle * 3
        self.avg_pool = nn.AdaptiveAvgPool2d(1)
        self.max_pool = nn.AdaptiveMaxPool2d(1)
        self.eca = _ECABlock(fused)
        self.spatial_dw = nn.ModuleList(nn.Conv2d(middle, middle, 3, 1, 1, groups=middle, bias=False) for _ in range(3))
        self.spatial_pw = nn.Conv2d(middle * 3, 3, 1, 1)
        self.softmax = nn.Softmax(dim=1)
        self.out_conv = nn.Conv2d(fused, middle, 1, 1)

    def forward(self, x: list[torch.Tensor]) -> torch.Tensor:
        shallow, middle, deep = x
        shallow = self.conv_align_shallow(self.conv_downsample(shallow))
        deep = F.interpolate(deep, size=middle.shape[-2:], mode="bilinear", align_corners=False)
        deep = self.conv_align_deep(deep)
        features = [shallow, middle, deep]
        fused = torch.cat(features, 1)
        channel_weight = self.eca(self.avg_pool(fused) + self.max_pool(fused))
        spatial_logits = self.spatial_pw(torch.cat([conv(f) for conv, f in zip(self.spatial_dw, features)], 1))
        spatial_weight = self.softmax(spatial_logits)
        spatial = torch.cat([f * spatial_weight[:, i : i + 1] for i, f in enumerate(features)], 1)
        return self.out_conv(fused * channel_weight + spatial)

