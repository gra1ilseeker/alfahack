"""PyTorch only; no PyG, no dense N x N adjacency matrices."""
from __future__ import annotations

import math
import torch
from torch import nn
from torch.nn import functional as F
from .schema import FEATURES, CATEGORIES, SCENARIOS


def cat_onehot(cats: torch.Tensor) -> torch.Tensor:
    return torch.cat([F.one_hot(cats[:, i], len(choices)).float()
                      for i, choices in enumerate(CATEGORIES.values())], dim=1)


def gaussian_kl(mu_q, logvar_q, mu_p=None, logvar_p=None):
    if mu_p is None:
        return .5 * (mu_q.square() + logvar_q.exp() - 1 - logvar_q).sum(1).mean()
    return .5 * (logvar_p - logvar_q +
                 (logvar_q.exp() + (mu_q - mu_p).square()) / logvar_p.exp() - 1).sum(1).mean()


class ConditionalVAE(nn.Module):
    def __init__(self, hidden: int = 128, latent: int = 12):
        super().__init__()
        self.latent = latent
        n_num = len(FEATURES)
        n_cat = sum(map(len, CATEGORIES.values()))
        n_cond = len(SCENARIOS)
        self.encoder = nn.Sequential(nn.Linear(n_num + n_cat + n_cond, hidden), nn.SiLU(),
                                     nn.Linear(hidden, hidden), nn.SiLU())
        self.mu = nn.Linear(hidden, latent)
        self.logvar = nn.Linear(hidden, latent)
        self.decoder = nn.Sequential(nn.Linear(latent + n_cond, hidden), nn.SiLU(),
                                     nn.Linear(hidden, hidden), nn.SiLU())
        self.numeric_mean = nn.Linear(hidden, n_num)
        self.numeric_logvar = nn.Linear(hidden, n_num)
        self.cat_heads = nn.ModuleList([nn.Linear(hidden, len(c)) for c in CATEGORIES.values()])

    def decode(self, z, condition):
        h = self.decoder(torch.cat([z, F.one_hot(condition, len(SCENARIOS)).float()], 1))
        return (self.numeric_mean(h), self.numeric_logvar(h).clamp(-4, 2),
                [head(h) for head in self.cat_heads])

    def forward(self, x, cats, condition, stochastic: bool = True):
        h = self.encoder(torch.cat([x, cat_onehot(cats),
                                   F.one_hot(condition, len(SCENARIOS)).float()], 1))
        mu, logvar = self.mu(h), self.logvar(h).clamp(-8, 5)
        z = mu + torch.randn_like(mu) * (.5 * logvar).exp() if stochastic else mu
        return (*self.decode(z, condition), mu, logvar)

    @staticmethod
    def loss(output, x, cats, beta: float = 1.):
        mean, logvar, logits, mu, latent_logvar = output
        nll_num = .5 * (math.log(2 * math.pi) + logvar +
                        (x - mean).square() / logvar.exp()).sum(1).mean()
        nll_cat = sum(F.cross_entropy(head, cats[:, i]) for i, head in enumerate(logits))
        kl = gaussian_kl(mu, latent_logvar)
        return nll_num + nll_cat + beta * kl, nll_num + nll_cat, kl

    @torch.no_grad()
    def sample(self, conditions: torch.Tensor):
        z = torch.randn(len(conditions), self.latent, device=conditions.device)
        mean, logvar, logits = self.decode(z, conditions)
        numeric = mean + torch.randn_like(mean) * (.5 * logvar).exp()
        cats = torch.stack([torch.distributions.Categorical(logits=h).sample() for h in logits], 1)
        return numeric.cpu().numpy(), cats.cpu().numpy()


def normalized_edges(edges: torch.Tensor, n: int):
    """Symmetric A + I normalization in sparse edge-list form."""
    loops = torch.arange(n, device=edges.device)
    src = torch.cat([edges[0], edges[1], loops])
    dst = torch.cat([edges[1], edges[0], loops])
    degree = torch.bincount(dst, minlength=n).float().clamp_min(1)
    weight = degree[src].rsqrt() * degree[dst].rsqrt()
    return src, dst, weight


def aggregate(x, adjacency):
    src, dst, weight = adjacency
    return torch.zeros_like(x).index_add_(0, dst, x[src] * weight[:, None])


class ConditionalVGAE(nn.Module):
    """VGAE with a learned p(z|x), allowing *new* nodes without a seed graph.

    q(z|x,A_train): sparse GCN; p(z|x): MLP; decoder: dot product.
    This is a conditional-prior adaptation, not the exact Kipf-Welling model.
    """
    def __init__(self, input_dim: int, hidden: int = 64, latent: int = 12):
        super().__init__()
        self.latent = latent
        self.gcn = nn.Linear(input_dim, hidden)
        self.q_mu = nn.Linear(hidden, latent)
        self.q_logvar = nn.Linear(hidden, latent)
        self.prior = nn.Sequential(nn.Linear(input_dim, hidden), nn.SiLU())
        self.p_mu = nn.Linear(hidden, latent)
        self.p_logvar = nn.Linear(hidden, latent)
        self.bias = nn.Parameter(torch.zeros(()))

    def prior_parameters(self, x):
        h = self.prior(x)
        return self.p_mu(h), self.p_logvar(h).clamp(-8, 3)

    def encode(self, x, adjacency):
        h = F.silu(aggregate(self.gcn(x), adjacency))
        return (aggregate(self.q_mu(h), adjacency),
                aggregate(self.q_logvar(h), adjacency).clamp(-8, 3))

    def decode(self, z, edges):
        return (z[edges[0]] * z[edges[1]]).sum(1) / math.sqrt(self.latent) + self.bias

    @torch.no_grad()
    def sample_prior(self, x):
        mu, logvar = self.prior_parameters(x)
        return mu + torch.randn_like(mu) * (.5 * logvar).exp()
