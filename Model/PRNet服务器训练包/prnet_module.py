"""PRNet modules for Ultralytics YOLO."""

import torch
import torch.nn as nn

__all__ = ("ESSamp",)


class ESSamp(nn.Module):
    """Enhanced semantic sampling downsampling module used by PRNet."""

    def __init__(self, c1: int, c2: int, k: int = 3, s: int = 1, depth_multiplier: int = 2):
        super().__init__()
        sliced_channels = c1 * 4
        expanded_channels = sliced_channels * depth_multiplier
        self.slices = nn.PixelUnshuffle(2)
        self.dsconv = nn.Sequential(
            nn.Conv2d(
                sliced_channels,
                expanded_channels,
                kernel_size=k,
                stride=s,
                padding=k // 2,
                groups=sliced_channels,
                bias=False,
            ),
            nn.BatchNorm2d(expanded_channels),
            nn.GELU(),
            nn.Conv2d(expanded_channels, c2, kernel_size=1, stride=1, padding=0, bias=False),
            nn.BatchNorm2d(c2),
            nn.GELU(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.dsconv(self.slices(x))
