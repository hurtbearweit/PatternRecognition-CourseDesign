"""Lightweight weighted feature fusion for local P3 -> P2 neck fusion."""

from __future__ import annotations

from collections.abc import Sequence

import torch
import torch.nn as nn
import torch.nn.functional as F


class WeightedFeatureFusion(nn.Module):
    """Fuse same-resolution features with normalized learnable scalar weights.

    The module accepts exactly two input tensors in this package. If input
    channels are different, each branch is projected by an independent 1x1
    convolution before weighted summation.
    """

    def __init__(
        self,
        in_channels: int | Sequence[int],
        out_channels: int | None = None,
        num_inputs: int = 2,
        eps: float = 1e-4,
        use_projection: bool = True,
    ) -> None:
        super().__init__()
        if isinstance(in_channels, int):
            channels = [in_channels] * num_inputs
        else:
            channels = list(in_channels)
        if len(channels) != 2:
            raise ValueError(f"WeightedFeatureFusion in week17 expects 2 inputs, got {len(channels)}")
        if num_inputs != len(channels):
            raise ValueError(f"num_inputs={num_inputs} does not match channels={channels}")

        self.in_channels = channels
        self.out_channels = int(out_channels or channels[0])
        self.num_inputs = len(channels)
        self.eps = float(eps)
        self.use_projection = bool(use_projection)
        self.weights = nn.Parameter(torch.ones(self.num_inputs, dtype=torch.float32))

        projections: list[nn.Module] = []
        for c in channels:
            if c != self.out_channels or self.use_projection:
                projections.append(nn.Conv2d(c, self.out_channels, kernel_size=1, stride=1, bias=False))
            else:
                projections.append(nn.Identity())
        self.projections = nn.ModuleList(projections)
        self.out = nn.Sequential(
            nn.Conv2d(self.out_channels, self.out_channels, kernel_size=1, stride=1, bias=False),
            nn.BatchNorm2d(self.out_channels),
            nn.SiLU(inplace=True),
        )

    def forward(self, features: Sequence[torch.Tensor]) -> torch.Tensor:
        if not isinstance(features, (list, tuple)):
            raise TypeError("WeightedFeatureFusion expects a list/tuple of feature tensors")
        if len(features) != self.num_inputs:
            raise ValueError(f"WeightedFeatureFusion expects {self.num_inputs} inputs, got {len(features)}")

        height_width = features[0].shape[-2:]
        projected = []
        for i, (feature, projection, expected_c) in enumerate(zip(features, self.projections, self.in_channels)):
            if feature.ndim != 4:
                raise ValueError(f"Input {i} must be BCHW tensor, got shape {tuple(feature.shape)}")
            if feature.shape[1] != expected_c:
                raise ValueError(f"Input {i} channel mismatch: expected {expected_c}, got {feature.shape[1]}")
            if feature.shape[-2:] != height_width:
                raise ValueError(
                    f"Input spatial sizes must match. Input 0 has {height_width}, "
                    f"input {i} has {feature.shape[-2:]}"
                )
            projected.append(projection(feature))

        weights = F.relu(self.weights)
        weights = weights / (weights.sum() + self.eps)
        fused = sum(w * x for w, x in zip(weights, projected))
        return self.out(fused)

