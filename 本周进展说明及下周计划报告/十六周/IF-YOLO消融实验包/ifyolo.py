"""IF-YOLO modules: IPFA and CSFM."""

import torch
import torch.nn as nn
import torch.nn.functional as F

__all__ = ("IPFA", "CSFM")


class IPFA(nn.Module):
    """Information-Preserving Feature Aggregation."""

    def __init__(self, c1: int, c2: int):
        super().__init__()
        if c1 % 2:
            raise ValueError("IPFA input channels must be even")
        self.conv_3x3_dw = nn.Conv2d(c1, c1, 3, 1, 1, bias=False)
        self.conv_1x1_pw = nn.Conv2d(c1 * 4, c2, 1, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.conv_3x3_dw(x)
        left, right = x.chunk(2, dim=1)
        parts = []
        for feature in (left, right):
            parts.extend(
                (
                    feature[:, :, 0::2, 0::2],
                    feature[:, :, 1::2, 0::2],
                    feature[:, :, 0::2, 1::2],
                    feature[:, :, 1::2, 1::2],
                )
            )
        return self.conv_1x1_pw(torch.cat(parts, dim=1))


class CRC(nn.Module):
    """Two-convolution channel recalibration block."""

    def __init__(self, channels: int):
        super().__init__()
        self.conv1 = nn.Conv2d(channels, channels, 3, 1, 1)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = nn.Conv2d(channels, channels, 3, 1, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.conv2(self.relu(self.conv1(x)))


class CCSM(nn.Module):
    """Channel Conflict Suppression Module."""

    def __init__(self, channels: int):
        super().__init__()
        self.crc_a = CRC(channels)
        self.crc_m = CRC(channels)
        self.avg_pool = nn.AdaptiveAvgPool2d(1)
        self.max_pool = nn.AdaptiveMaxPool2d(1)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        weight = self.sigmoid(self.crc_a(self.avg_pool(x)) + self.crc_m(self.max_pool(x)))
        return x * weight


class SCSM(nn.Module):
    """Spatial Conflict Suppression Module."""

    def __init__(self, channels: int, levels: int = 3):
        super().__init__()
        self.conv3_list = nn.ModuleList(nn.Conv2d(channels, 8, 3, 1, 1) for _ in range(levels))
        self.conv1 = nn.Conv2d(8 * levels, levels, 1, 1)
        self.softmax = nn.Softmax(dim=1)

    def forward(self, features: list[torch.Tensor]) -> torch.Tensor:
        attention = self.softmax(self.conv1(torch.cat([conv(x) for conv, x in zip(self.conv3_list, features)], 1)))
        weighted = [x * attention[:, i : i + 1] for i, x in enumerate(features)]
        return torch.cat(weighted, dim=1)


class CSFM(nn.Module):
    """Conflict Information Suppression Feature Fusion Module."""

    def __init__(self, channels: list[int]):
        super().__init__()
        if len(channels) != 3:
            raise ValueError("CSFM requires three input feature maps")
        shallow, middle, deep = channels
        self.conv_downsample = nn.Conv2d(shallow, shallow, 3, 2, 1)
        self.conv_align_shallow = nn.Conv2d(shallow, middle, 1, 1)
        self.conv_align_deep = nn.Conv2d(deep, middle, 1, 1)
        fused_channels = middle * 3
        self.ccsm = CCSM(fused_channels)
        self.scsm = SCSM(middle)
        self.out_conv = nn.Conv2d(fused_channels, middle, 1, 1)

    def forward(self, x: list[torch.Tensor]) -> torch.Tensor:
        shallow, middle, deep = x
        shallow = self.conv_align_shallow(self.conv_downsample(shallow))
        deep = F.interpolate(deep, size=middle.shape[-2:], mode="bilinear", align_corners=False)
        deep = self.conv_align_deep(deep)
        features = [shallow, middle, deep]
        fused = torch.cat(features, dim=1)
        return self.out_conv(self.ccsm(fused) + self.scsm(features))
