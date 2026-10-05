"""Adaptive PyTorch Tabular MLP surrogate model for multi-output regression."""

from typing import Optional
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

from autocompliant.models.base import BaseSurrogateModel


class TabularMLPNet(nn.Module):
    """Residual Tabular MLP Architecture dynamically sized for (D_in, D_out)."""

    def __init__(self, D_in: int, D_out: int, hidden_dim: int = 64, dropout: float = 0.05):
        super().__init__()
        self.input_layer = nn.Sequential(
            nn.Linear(D_in, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.SiLU(),
        )

        self.block1 = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.SiLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
        )
        self.act = nn.SiLU()

        self.head = nn.Linear(hidden_dim, D_out)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h0 = self.input_layer(x)
        h1 = self.act(h0 + self.block1(h0))  # Skip connection
        out = self.head(h1)
        return out


class AdaptiveMLPSurrogate(BaseSurrogateModel):
    """Deep Neural Network Surrogate adapting to arbitrary input and output dimensionality."""

    def __init__(
        self,
        hidden_dim: int = 64,
        lr: float = 0.003,
        epochs: int = 80,
        batch_size: int = 32,
        weight_decay: float = 1e-4,
        random_state: int = 42,
    ):
        super().__init__(name="AdaptiveMLP")
        self.hidden_dim = hidden_dim
        self.lr = lr
        self.epochs = epochs
        self.batch_size = batch_size
        self.weight_decay = weight_decay
        self.random_state = random_state
        self.net: Optional[TabularMLPNet] = None
        self.device = torch.device("cpu")

    def fit(self, X: np.ndarray, Y: np.ndarray) -> "AdaptiveMLPSurrogate":
        torch.manual_seed(self.random_state)
        np.random.seed(self.random_state)

        X_arr = np.asarray(X, dtype=np.float32)
        Y_arr = np.asarray(Y, dtype=np.float32)
        if Y_arr.ndim == 1:
            Y_arr = Y_arr.reshape(-1, 1)

        self.D_in = X_arr.shape[1]
        self.D_out = Y_arr.shape[1]

        self.net = TabularMLPNet(
            D_in=self.D_in, D_out=self.D_out, hidden_dim=self.hidden_dim
        ).to(self.device)

        dataset = TensorDataset(torch.from_numpy(X_arr), torch.from_numpy(Y_arr))
        loader = DataLoader(dataset, batch_size=self.batch_size, shuffle=True)

        optimizer = torch.optim.AdamW(
            self.net.parameters(), lr=self.lr, weight_decay=self.weight_decay
        )
        criterion = nn.MSELoss()
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer, T_max=self.epochs, eta_min=1e-5
        )

        self.net.train()
        for _ in range(self.epochs):
            for batch_x, batch_y in loader:
                batch_x = batch_x.to(self.device)
                batch_y = batch_y.to(self.device)

                optimizer.zero_grad()
                pred = self.net(batch_x)
                loss = criterion(pred, batch_y)
                loss.backward()
                optimizer.step()
            scheduler.step()

        self.is_fitted = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted or self.net is None:
            raise RuntimeError("Model must be fitted before calling predict.")

        X_arr = np.asarray(X, dtype=np.float32)
        self.net.eval()
        with torch.no_grad():
            tensor_x = torch.from_numpy(X_arr).to(self.device)
            pred = self.net(tensor_x).cpu().numpy()
        return pred.astype(np.float64)
