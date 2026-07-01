"""Custom modules for week-17 IF-YOLO experiments.

The modules are pure PyTorch and are designed to be registered into
Ultralytics' YAML parser by install_week17_modules.py.
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F

__all__ = (
    "IPFA",
    "CSFM",
    "CSFMLite",
    "DySampleYOLO",
    "LocalDetailRefine",
    "WeightedFeatureFusion",
)


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


class _ECABlock(nn.Module):
    def __init__(self, channels: int, k_size: int = 3):
        super().__init__()
        self.conv = nn.Conv1d(1, 1, kernel_size=k_size, padding=(k_size - 1) // 2, bias=False)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        y = self.conv(x.squeeze(-1).transpose(-1, -2)).transpose(-1, -2).unsqueeze(-1)
        return self.sigmoid(y)


class CSFMLite(nn.Module):
    """Lightweight cross-scale feature fusion module."""

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


CSFM = CSFMLite


class DySampleYOLO(nn.Module):
    """DySample-style dynamic upsampling for YOLO necks.

    The module keeps the channel count unchanged and upsamples spatial size by
    `scale`. It follows the official DySample idea: a 1x1 convolution predicts
    offsets and F.grid_sample performs dynamic point sampling.
    """

    def __init__(
        self,
        in_channels: int,
        scale: int = 2,
        style: str = "lp",
        groups: int = 4,
        dyscope: bool = False,
    ):
        super().__init__()
        if style not in {"lp", "pl"}:
            raise ValueError(f"Unsupported DySample style: {style}")
        if in_channels % groups != 0:
            raise ValueError(f"in_channels={in_channels} must be divisible by groups={groups}")
        if style == "pl" and in_channels % (scale * scale) != 0:
            raise ValueError("style='pl' requires in_channels divisible by scale^2")

        self.in_channels = in_channels
        self.scale = scale
        self.style = style
        self.groups = groups
        self.dyscope = dyscope

        offset_in = in_channels if style == "lp" else in_channels // (scale * scale)
        offset_out = 2 * groups * scale * scale if style == "lp" else 2 * groups
        self.offset = nn.Conv2d(offset_in, offset_out, 1)
        nn.init.normal_(self.offset.weight, std=0.001)
        nn.init.constant_(self.offset.bias, 0.0)

        if dyscope:
            self.scope = nn.Conv2d(offset_in, offset_out, 1, bias=False)
            nn.init.constant_(self.scope.weight, 0.0)
        else:
            self.scope = None

        self.register_buffer("init_pos", self._init_pos(), persistent=False)

    def _init_pos(self) -> torch.Tensor:
        h = torch.arange((-self.scale + 1) / 2, (self.scale - 1) / 2 + 1) / self.scale
        yy, xx = torch.meshgrid(h, h, indexing="ij")
        pos = torch.stack((xx, yy), dim=0)
        return pos.transpose(1, 2).repeat(1, self.groups, 1).reshape(1, -1, 1, 1)

    def _sample(self, x: torch.Tensor, offset: torch.Tensor) -> torch.Tensor:
        b, _, h, w = offset.shape
        offset = offset.view(b, 2, -1, h, w)

        coords_h = torch.arange(h, dtype=x.dtype, device=x.device) + 0.5
        coords_w = torch.arange(w, dtype=x.dtype, device=x.device) + 0.5
        yy, xx = torch.meshgrid(coords_h, coords_w, indexing="ij")
        coords = torch.stack((xx, yy), dim=0).unsqueeze(0).unsqueeze(2)
        normalizer = torch.tensor([w, h], dtype=x.dtype, device=x.device).view(1, 2, 1, 1, 1)
        coords = 2.0 * (coords + offset) / normalizer - 1.0
        coords = F.pixel_shuffle(coords.view(b, -1, h, w), self.scale)
        coords = coords.view(b, 2, -1, self.scale * h, self.scale * w)
        coords = coords.permute(0, 2, 3, 4, 1).contiguous().flatten(0, 1)

        sampled = F.grid_sample(
            x.reshape(b * self.groups, -1, h, w),
            coords,
            mode="bilinear",
            align_corners=False,
            padding_mode="border",
        )
        return sampled.view(b, -1, self.scale * h, self.scale * w)

    def forward_lp(self, x: torch.Tensor) -> torch.Tensor:
        offset = self.offset(x)
        if self.scope is not None:
            offset = offset * self.scope(x).sigmoid() * 0.5
        else:
            offset = offset * 0.25
        return self._sample(x, offset + self.init_pos)

    def forward_pl(self, x: torch.Tensor) -> torch.Tensor:
        x_ = F.pixel_shuffle(x, self.scale)
        offset = self.offset(x_)
        if self.scope is not None:
            offset = offset * self.scope(x_).sigmoid() * 0.5
        else:
            offset = offset * 0.25
        offset = F.pixel_unshuffle(offset, self.scale) + self.init_pos
        return self._sample(x, offset)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.forward_lp(x) if self.style == "lp" else self.forward_pl(x)


class LocalDetailRefine(nn.Module):
    """Lightweight local detail refinement block placed after DySample only."""

    def __init__(self, in_channels: int):
        super().__init__()
        self.dw = nn.Conv2d(in_channels, in_channels, 3, 1, 1, groups=in_channels, bias=False)
        self.bn1 = nn.BatchNorm2d(in_channels)
        self.act1 = nn.SiLU(inplace=True)
        self.pw = nn.Conv2d(in_channels, in_channels, 1, 1, 0, bias=False)
        self.bn2 = nn.BatchNorm2d(in_channels)
        self.act2 = nn.SiLU(inplace=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        y = self.act1(self.bn1(self.dw(x)))
        y = self.bn2(self.pw(y))
        return self.act2(x + y)


class WeightedFeatureFusion(nn.Module):
    """Learnable non-negative weighted sum with channel and size alignment."""

    def __init__(self, channels: list[int], out_channels: int | None = None, eps: float = 1e-4):
        super().__init__()
        if not channels:
            raise ValueError("WeightedFeatureFusion requires at least one input feature")
        self.out_channels = int(out_channels or channels[0])
        self.eps = eps
        self.weights = nn.Parameter(torch.ones(len(channels), dtype=torch.float32))
        self.align = nn.ModuleList(
            nn.Identity() if c == self.out_channels else nn.Conv2d(c, self.out_channels, 1, 1, 0, bias=False)
            for c in channels
        )

    def forward(self, features: list[torch.Tensor]) -> torch.Tensor:
        if not isinstance(features, (list, tuple)):
            raise TypeError("WeightedFeatureFusion expects a list of tensors")
        size = features[0].shape[-2:]
        weights = F.relu(self.weights)
        out = None
        for i, (feature, align) in enumerate(zip(features, self.align)):
            if feature.shape[-2:] != size:
                feature = F.interpolate(feature, size=size, mode="nearest")
            feature = align(feature)
            weighted = feature * weights[i]
            out = weighted if out is None else out + weighted
        return out / (weights.sum() + self.eps)
