import logging

import torch
import triton
from torch._prims_common import ELEMENTWISE_TYPE_PROMOTION_KIND
from torch._prims_common.wrappers import elementwise_type_promotion_wrapper

from ..utils import pointwise_dynamic


@pointwise_dynamic(is_tensor=[True, True, False])
@triton.jit
def add_func(x, y, alpha):
    return x + y * alpha


@pointwise_dynamic(is_tensor=[True, False, False])
@triton.jit
def add_func_tensor_scalar(x, y, alpha):
    return x + y * alpha


@pointwise_dynamic(is_tensor=[False, True, False])
@triton.jit
def add_func_scalar_tensor(x, y, alpha):
    return x + y * alpha


@elementwise_type_promotion_wrapper(
    type_promoting_args=("A", "B"),
    type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.DEFAULT,
)
def add(A, B, *, alpha=1):
    logging.debug("GEMS ADD")
    if isinstance(A, torch.Tensor) and isinstance(B, torch.Tensor):
        return add_func(A, B, alpha)
    elif isinstance(A, torch.Tensor):
        return add_func_tensor_scalar(A, B, alpha)
    elif isinstance(B, torch.Tensor):
        return add_func_scalar_tensor(A, B, alpha)
    else:
        return A + B * alpha
