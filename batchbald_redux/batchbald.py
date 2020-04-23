# AUTOGENERATED! DO NOT EDIT! File to edit: batchbald.ipynb (unless otherwise specified).

__all__ = ['compute_conditional_entropy', 'compute_entropy', 'CandidateBatch', 'get_batchbald_batch']

# Cell
from dataclasses import dataclass
from typing import List
import torch

from toma import toma

from batchbald_redux import joint_entropy

# Cell

def compute_conditional_entropy(probs_N_K_C: torch.Tensor) -> torch.Tensor:
    N, K, C = probs_N_K_C.shape

    entropies_N = torch.empty(N, dtype=torch.double)
    @toma.chunked(probs_N_K_C, 1024)
    def compute(probs_n_K_C, start:int, end: int):
        entropies_N[start:end].copy_(-torch.sum(probs_n_K_C*torch.log(probs_n_K_C), dim=(1,2))/K)

    return entropies_N


def compute_entropy(probs_N_K_C: torch.Tensor) -> torch.Tensor:
    N, K, C = probs_N_K_C.shape

    entropies_N = torch.empty(N, dtype=torch.double)
    @toma.chunked(probs_N_K_C, 1024)
    def compute(probs_n_K_C, start:int, end: int):
        mean_probs_N_C = probs_N_K_C.mean(dim=1)
        entropies_N[start:end].copy_(-torch.sum(mean_probs_N_C*torch.log(mean_probs_N_C), dim=1))

    return entropies_N


# Cell


@dataclass
class CandidateBatch:
    scores: List[float]
    indices: List[int]


def get_batchbald_batch(probs_N_K_C: torch.Tensor,
                        batch_size: int,
                        num_samples: int,
                        dtype=None,
                        device=None) -> CandidateBatch:
    N, K, C = probs_N_K_C.shape

    batch_size = min(batch_size, N)

    candidate_indices = []
    candidate_scores = []

    if batch_size == 0:
        return CandidateBatch(candidate_scores, candidate_indices)

    batch_joint_entropy = joint_entropy.DynamicJointEntropy(num_samples,
                                                            batch_size - 1,
                                                            K,
                                                            C,
                                                            dtype=dtype,
                                                            device=device)

    conditional_entropies_N = compute_conditional_entropy(probs_N_K_C)

    # We always keep these on the CPU.
    scores_N = torch.empty(N, dtype=torch.double)

    for i in range(batch_size):
        if i > 0:
            latest_index = candidate_indices[-1]
            batch_joint_entropy.add_variables(
                probs_N_K_C[latest_index:latest_index + 1])
            shared_conditinal_entropies = conditional_entropies_N[candidate_indices].sum()
        else:
            shared_conditinal_entropies = 0.

        batch_joint_entropy.compute_batch(probs_N_K_C,
                                          output_entropies_B=scores_N)

        scores_N -= conditional_entropies_N + shared_conditinal_entropies
        scores_N[candidate_indices] = -float('inf')

        candidate_score, candidate_index = scores_N.max()

        candidate_indices.append(candidate_index.item())
        candidate_scores.append(candidate_scores.item())

    return CandidateBatch(candidate_scores, candidate_indices)