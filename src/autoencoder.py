from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset


class VanillaAutoencoder(nn.Module):
    """Single-layer bottleneck autoencoder with ReLU activations (paper eq. 2-3)."""

    def __init__(self, n_assets: int, n_factors: int) -> None:
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(n_assets, n_factors),
            nn.ReLU(),
        )
        self.decoder = nn.Sequential(
            nn.Linear(n_factors, n_assets),
        )

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        return self.encoder(x)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.decoder(self.encode(x))


@dataclass
class AETrainConfig:
    n_factors: int = 5
    epochs: int = 100
    batch_size: int = 64
    learning_rate: float = 1e-3
    patience: int = 5
    seed: int = 42


def train_vanilla_autoencoder(
    window_returns: np.ndarray,
    config: AETrainConfig | None = None,
) -> tuple[VanillaAutoencoder, np.ndarray]:
    """
    Train a vanilla AE on cross-sectional return vectors in the window.

    Parameters
    ----------
    window_returns : ndarray, shape (M, N)
        Z-scored returns for the estimation window.

    Returns
    -------
    model : trained VanillaAutoencoder
    factors : ndarray, shape (M, K)
        Latent factors f_t from the encoder for each day in the window.
    """
    config = config or AETrainConfig()
    torch.manual_seed(config.seed)

    n_obs, n_assets = window_returns.shape
    device = torch.device("cpu")
    model = VanillaAutoencoder(n_assets, config.n_factors).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
    criterion = nn.MSELoss()

    x = torch.tensor(window_returns, dtype=torch.float32)
    loader = DataLoader(
        TensorDataset(x),
        batch_size=min(config.batch_size, n_obs),
        shuffle=True,
    )

    best_loss = float("inf")
    best_state: dict[str, torch.Tensor] | None = None
    stale_epochs = 0

    for _ in range(config.epochs):
        model.train()
        epoch_loss = 0.0
        n_batches = 0
        for (batch_x,) in loader:
            batch_x = batch_x.to(device)
            optimizer.zero_grad()
            recon = model(batch_x)
            loss = criterion(recon, batch_x)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()
            n_batches += 1

        epoch_loss /= max(n_batches, 1)
        if epoch_loss < best_loss - 1e-8:
            best_loss = epoch_loss
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            stale_epochs = 0
        else:
            stale_epochs += 1
            if stale_epochs >= config.patience:
                break

    if best_state is not None:
        model.load_state_dict(best_state)

    model.eval()
    with torch.no_grad():
        factors = model.encode(x.to(device)).cpu().numpy()
    return model, factors
