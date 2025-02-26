import random

import pytest
import torch

import flag_gems

from .accuracy_utils import (
    CONTIGUOUS_SHAPE_STRIDES_2D,
    FLOAT_DTYPES,
    INT_DTYPES,
    IRREGULAR_SHAPE_STRIDES,
    REDUCTION_SHAPES,
    REDUCTION_SMALL_SHAPES,
    SHAPE_STRIDES,
    gems_assert_close,
    gems_assert_equal,
    to_reference,
)
from .conftest import QUICK_MODE

FLOAT_DTYPES = [torch.float32] if QUICK_MODE else FLOAT_DTYPES
DIM_LIST = [1] if QUICK_MODE else [0, 1]
DIMS_LIST = [1] if QUICK_MODE else [0, 1, [0, 1], [1, 0]]
KEEPDIM_DIMS_SHAPE = (
    [(True, DIMS_LIST[0], REDUCTION_SHAPES[0])]
    if QUICK_MODE
    else list(zip([True, False] * 2, DIMS_LIST, REDUCTION_SHAPES + [(7, 4, 11, 1)]))
)
SMOOTH_IGNORE_SHAPE = (
    [(0.1, 1, REDUCTION_SHAPES[0])]
    if QUICK_MODE
    else list(zip([0, 0.1, 1], [1, 200, -100], REDUCTION_SHAPES))
)
SMOOTH_SHAPE = (
    [(0.1, REDUCTION_SHAPES[0])]
    if QUICK_MODE
    else list(zip([1, 0.1, 0], REDUCTION_SHAPES))
)
DIM_SHAPE_STRIDES = (
    [(1, *CONTIGUOUS_SHAPE_STRIDES_2D[1])]
    if QUICK_MODE
    else list(
        (random.randint(0, len(shape) - 1), shape, stride)
        for shape, stride in SHAPE_STRIDES
    )
)
REGULAR_DIM_SHAPE_STRIDES = (
    [(1, *CONTIGUOUS_SHAPE_STRIDES_2D[1])]
    if QUICK_MODE
    else list(
        (random.randint(0, len(shape) - 1), shape, stride)
        for shape, stride in CONTIGUOUS_SHAPE_STRIDES_2D
    )
)
IRREGULAR_DIM_SHAPE_STRIDES = [(3, *IRREGULAR_SHAPE_STRIDES)]

THRESHOLD_SHAPE = (
    [(0.3, REDUCTION_SHAPES[0])]
    if QUICK_MODE
    else list(zip([0.3, 0.5, 0.7], REDUCTION_SHAPES))
)
CROSS_ENTROPY_LOSS_REDUCTION = ["sum"] if QUICK_MODE else ["mean", "none", "sum"]


@pytest.mark.amax
@pytest.mark.parametrize("keepdim, dim, shape", KEEPDIM_DIMS_SHAPE)
@pytest.mark.parametrize("dtype", FLOAT_DTYPES)
def test_accuracy_amax(shape, dim, keepdim, dtype):
    inp = torch.randn(shape, dtype=dtype, device="cuda")
    ref_inp = to_reference(inp)

    ref_out = torch.amax(ref_inp, dim=dim, keepdim=keepdim)
    with flag_gems.use_gems():
        res_out = torch.amax(inp, dim=dim, keepdim=keepdim)

    gems_assert_equal(res_out, ref_out)


# TODO: There are some bugs in argmax with large size.
@pytest.mark.argmax
@pytest.mark.parametrize("shape", REDUCTION_SMALL_SHAPES)
@pytest.mark.parametrize("dim", DIM_LIST)
@pytest.mark.parametrize("keepdim", [True, False])
@pytest.mark.parametrize("dtype", FLOAT_DTYPES)
def test_accuracy_argmax(shape, dim, keepdim, dtype):
    inp = torch.randn(shape, dtype=dtype, device="cuda")
    ref_inp = to_reference(inp)

    ref_out = torch.argmax(ref_inp, dim=dim, keepdim=keepdim)
    with flag_gems.use_gems():
        res_out = torch.argmax(inp, dim=dim, keepdim=keepdim)

    gems_assert_equal(res_out, ref_out)


@pytest.mark.CrossEntropyLoss
@pytest.mark.parametrize("label_smoothing, ignore_index, shape", SMOOTH_IGNORE_SHAPE)
@pytest.mark.parametrize("reduction", CROSS_ENTROPY_LOSS_REDUCTION)
@pytest.mark.parametrize("dtype", FLOAT_DTYPES)
def test_accuracy_cross_entropy_loss_indices(
    shape, dtype, ignore_index, reduction, label_smoothing
):
    dim = 1
    up_limit = shape[dim] - 1
    target_shape = list(shape)
    del target_shape[dim]

    inp = torch.randn(shape, dtype=dtype, device="cuda", requires_grad=True)
    target = torch.randint(0, up_limit, target_shape, device="cuda")
    weight = torch.randn(shape[dim], dtype=dtype, device="cuda")
    ref_inp = to_reference(inp, True)
    ref_target = to_reference(target)
    ref_weight = to_reference(weight, True)
    ref_criterion = torch.nn.CrossEntropyLoss(
        weight=ref_weight,
        ignore_index=ignore_index,
        reduction=reduction,
        label_smoothing=label_smoothing,
    )
    res_criterion = torch.nn.CrossEntropyLoss(
        weight=weight,
        ignore_index=ignore_index,
        reduction=reduction,
        label_smoothing=label_smoothing,
    )

    ref_out = ref_criterion(ref_inp, ref_target)
    with flag_gems.use_gems():
        res_out = res_criterion(inp, target)
    gems_assert_close(res_out, ref_out, dtype, reduce_dim=shape[dim])

    out_grad = torch.randn_like(res_out)
    ref_grad = to_reference(out_grad, True)
    (ref_in_grad,) = torch.autograd.grad(ref_out, ref_inp, ref_grad)
    (res_in_grad,) = torch.autograd.grad(res_out, inp, out_grad)
    gems_assert_close(res_in_grad, ref_in_grad, dtype, reduce_dim=shape[dim])


@pytest.mark.CrossEntropyLoss
@pytest.mark.parametrize("label_smoothing, shape", SMOOTH_SHAPE)
@pytest.mark.parametrize("reduction", CROSS_ENTROPY_LOSS_REDUCTION)
@pytest.mark.parametrize("dtype", FLOAT_DTYPES)
def test_accuracy_cross_entropy_loss_probabilities(
    shape, dtype, reduction, label_smoothing
):
    dim = 1
    inp = torch.randn(shape, dtype=dtype, device="cuda", requires_grad=True)
    target = torch.randn(shape, dtype=dtype, device="cuda")
    weight = torch.randn(shape[dim], dtype=dtype, device="cuda")
    ref_inp = to_reference(inp, True)
    ref_target = to_reference(target, True)
    ref_weight = to_reference(weight, True)
    ref_criterion = torch.nn.CrossEntropyLoss(
        weight=ref_weight,
        reduction=reduction,
        label_smoothing=label_smoothing,
    )
    res_criterion = torch.nn.CrossEntropyLoss(
        weight=weight,
        reduction=reduction,
        label_smoothing=label_smoothing,
    )

    ref_out = ref_criterion(ref_inp, ref_target)
    with flag_gems.use_gems():
        res_out = res_criterion(inp, target)
    gems_assert_close(res_out, ref_out, dtype, reduce_dim=shape[dim])

    out_grad = torch.randn_like(res_out)
    ref_grad = to_reference(out_grad, True)
    (ref_in_grad,) = torch.autograd.grad(ref_out, ref_inp, ref_grad)
    (res_in_grad,) = torch.autograd.grad(res_out, inp, out_grad)
    gems_assert_close(res_in_grad, ref_in_grad, dtype, reduce_dim=shape[dim])


CUMSUM_SHAPES = (
    [(2, 32)] if QUICK_MODE else REDUCTION_SHAPES + [(2637,), (16, 1025, 255)]
)


@pytest.mark.cumsum
@pytest.mark.parametrize("shape", CUMSUM_SHAPES)
@pytest.mark.parametrize("dtype", FLOAT_DTYPES + INT_DTYPES)
def test_accuracy_cumsum(shape, dtype):
    dim = 1 if shape == REDUCTION_SHAPES[-1] else -1
    if dtype in INT_DTYPES:
        inp = torch.randint(-3, 3, shape, device="cuda").to(dtype)
    else:
        inp = torch.randn(shape, dtype=dtype, device="cuda")
    ref_inp = to_reference(inp, True)

    ref_out = torch.cumsum(ref_inp, dim=dim)
    with flag_gems.use_gems():
        res_out = torch.cumsum(inp, dim=dim)

    gems_assert_close(res_out, ref_out, dtype, reduce_dim=shape[dim])


NONZERO_SHAPES = [(2, 32)] if QUICK_MODE else REDUCTION_SHAPES + [(2637,)]


@pytest.mark.nonzero
@pytest.mark.parametrize("shape", NONZERO_SHAPES)
@pytest.mark.parametrize("dtype", FLOAT_DTYPES + INT_DTYPES + [torch.bool])
def test_accuracy_nonzero(shape, dtype):
    if dtype == torch.bool:
        inp = torch.randint(0, 2, shape, dtype=torch.int, device="cuda").to(dtype)
    elif dtype in INT_DTYPES:
        inp = torch.randint(-3, 3, shape, device="cuda").to(dtype)
    else:
        inp = torch.randn(shape, dtype=dtype, device="cuda")
    ref_inp = to_reference(inp, False)

    ref_out = torch.nonzero(ref_inp)
    with flag_gems.use_gems():
        res_out = torch.nonzero(inp)

    gems_assert_equal(res_out, ref_out)


@pytest.mark.log_softmax
@pytest.mark.parametrize("shape", REDUCTION_SMALL_SHAPES)
@pytest.mark.parametrize("dtype", FLOAT_DTYPES)
def test_accuracy_log_softmax(shape, dtype):
    dim = 1
    inp = torch.randn(shape, dtype=dtype, device="cuda", requires_grad=True)
    ref_inp = to_reference(inp, True)

    ref_out = torch.nn.functional.log_softmax(ref_inp, dim=dim)
    with flag_gems.use_gems():
        res_out = torch.nn.functional.log_softmax(inp, dim=dim)
    gems_assert_close(res_out, ref_out, dtype)

    out_grad = torch.randn_like(res_out)
    ref_grad = to_reference(out_grad, True)

    (ref_in_grad,) = torch.autograd.grad(ref_out, ref_inp, ref_grad)
    (res_in_grad,) = torch.autograd.grad(res_out, inp, out_grad)
    gems_assert_close(res_in_grad, ref_in_grad, dtype, reduce_dim=shape[dim])


# TODO: failed at (1, 2) (200, 40999, 3)
@pytest.mark.softmax
@pytest.mark.parametrize(
    "shape", [(1, 256)] if QUICK_MODE else [(1, 256), (4096, 256), (200, 2560, 3)]
)
@pytest.mark.parametrize("dtype", FLOAT_DTYPES)
@pytest.mark.parametrize("dim", DIM_LIST)
def test_accuracy_softmax(shape, dtype, dim):
    inp = torch.randn(shape, dtype=dtype, device="cuda", requires_grad=True)
    ref_inp = to_reference(inp, True)

    ref_out = torch.nn.functional.softmax(ref_inp, dim=dim)
    with flag_gems.use_gems():
        res_out = torch.nn.functional.softmax(inp, dim=dim)
    gems_assert_close(res_out, ref_out, dtype)

    out_grad = torch.randn_like(inp)
    ref_grad = to_reference(out_grad, True)

    (ref_in_grad,) = torch.autograd.grad(ref_out, ref_inp, ref_grad)
    (res_in_grad,) = torch.autograd.grad(res_out, inp, out_grad)
    gems_assert_close(res_in_grad, ref_in_grad, dtype, reduce_dim=shape[dim])


@pytest.mark.var_mean
@pytest.mark.parametrize("shape", REDUCTION_SHAPES)
@pytest.mark.parametrize("dim", DIMS_LIST)
@pytest.mark.parametrize("correction", [1] if QUICK_MODE else [0, 1])
@pytest.mark.parametrize("keepdim", [True] if QUICK_MODE else [True, False])
@pytest.mark.parametrize("dtype", FLOAT_DTYPES)
def test_accuracy_varmean(shape, dim, correction, keepdim, dtype):
    if shape[0] == 1:  # TODO: res is inf, while ref is nan
        shape = (2, 2)
    inp = torch.randn(shape, dtype=dtype, device="cuda")
    ref_inp = to_reference(inp, True)

    ref_var, ref_mean = torch.var_mean(
        ref_inp, dim, correction=correction, keepdim=keepdim
    )
    with flag_gems.use_gems():
        res_var, res_mean = torch.var_mean(
            inp, dim, correction=correction, keepdim=keepdim
        )

    gems_assert_close(res_mean, ref_mean, dtype)
    gems_assert_close(res_var, ref_var, dtype)


@pytest.mark.scatter
@pytest.mark.parametrize(
    "src_shape", [(32, 8, 4)] if QUICK_MODE else [(128, 16, 4), (256, 32, 8)]
)
@pytest.mark.parametrize(
    "inp_shape", [(64, 16, 8)] if QUICK_MODE else [(512, 128, 32), (1024, 64, 16)]
)
@pytest.mark.parametrize("dim", [0, 1, 2])
@pytest.mark.parametrize("dtype", FLOAT_DTYPES)
def test_accuracy_scatter_src(src_shape, inp_shape, dim, dtype):
    inp = torch.randn(inp_shape, dtype=dtype, device="cuda")
    src = torch.randn(src_shape, dtype=dtype, device="cuda")
    size_dim = min(src_shape[dim], inp_shape[dim])

    import random

    index_shape = [
        random.randint(1, min(src_shape[0], inp_shape[0])),
        random.randint(1, min(src_shape[1], inp_shape[1])),
        random.randint(1, min(src_shape[2], inp_shape[2])),
    ]
    index = torch.empty(tuple(index_shape), dtype=torch.long, device="cuda")

    m, n, o = index_shape

    index_size_dim = index_shape[dim]
    # make unique indices
    for i in range(1 if dim == 0 else m):
        for j in range(1 if dim == 1 else n):
            for k in range(1 if dim == 2 else o):
                ii = [i, j, k]
                ii[dim] = slice(0, index.size(dim) + 1)
                index[tuple(ii)] = torch.randperm(size_dim)[0:index_size_dim]

    ref_inp = to_reference(inp)
    ref_index = to_reference(index)
    ref_src = to_reference(src)
    ref_out = torch.scatter(ref_inp, dim, ref_index, ref_src)
    with flag_gems.use_gems():
        res_out = torch.scatter(inp, dim, index, src)

    gems_assert_equal(res_out, ref_out)


@pytest.mark.scatter
@pytest.mark.parametrize(
    "src_shape", [(32, 8, 4)] if QUICK_MODE else [(128, 16, 4), (256, 32, 8)]
)
@pytest.mark.parametrize(
    "inp_shape", [(64, 16, 8)] if QUICK_MODE else [(512, 128, 32), (1024, 64, 16)]
)
@pytest.mark.parametrize("dim", [0, 1, 2])
@pytest.mark.parametrize("dtype", FLOAT_DTYPES)
def test_accuracy_scatter_add(src_shape, inp_shape, dim, dtype):
    inp = torch.randn(inp_shape, dtype=dtype, device="cuda")
    src = torch.randn(src_shape, dtype=dtype, device="cuda")
    size_dim = min(src_shape[dim], inp_shape[dim])

    import random

    index_shape = [
        random.randint(1, min(src_shape[0], inp_shape[0])),
        random.randint(1, min(src_shape[1], inp_shape[1])),
        random.randint(1, min(src_shape[2], inp_shape[2])),
    ]
    index = torch.empty(tuple(index_shape), dtype=torch.long, device="cuda")

    m, n, o = index_shape

    index_size_dim = index_shape[dim]
    # make unique indices
    for i in range(1 if dim == 0 else m):
        for j in range(1 if dim == 1 else n):
            for k in range(1 if dim == 2 else o):
                ii = [i, j, k]
                ii[dim] = slice(0, index.size(dim) + 1)
                index[tuple(ii)] = torch.randperm(size_dim)[0:index_size_dim]

    ref_inp = to_reference(inp)
    ref_index = to_reference(index)
    ref_src = to_reference(src)
    ref_out = torch.scatter(ref_inp, dim, ref_index, ref_src, reduce="add")
    with flag_gems.use_gems():
        res_out = torch.scatter(inp, dim, index, src, reduce="add")

    gems_assert_close(res_out, ref_out, dtype)


@pytest.mark.scatter
@pytest.mark.parametrize(
    "src_shape", [(32, 8, 4)] if QUICK_MODE else [(128, 16, 4), (256, 32, 8)]
)
@pytest.mark.parametrize(
    "inp_shape", [(64, 16, 8)] if QUICK_MODE else [(512, 128, 32), (1024, 64, 16)]
)
@pytest.mark.parametrize("dim", [0, 1, 2])
@pytest.mark.parametrize("dtype", FLOAT_DTYPES)
def test_accuracy_scatter_mul(src_shape, inp_shape, dim, dtype):
    inp = torch.randn(inp_shape, dtype=dtype, device="cuda")
    src = torch.randn(src_shape, dtype=dtype, device="cuda")
    size_dim = min(src_shape[dim], inp_shape[dim])

    import random

    index_shape = [
        random.randint(1, min(src_shape[0], inp_shape[0])),
        random.randint(1, min(src_shape[1], inp_shape[1])),
        random.randint(1, min(src_shape[2], inp_shape[2])),
    ]
    index = torch.empty(tuple(index_shape), dtype=torch.long, device="cuda")

    m, n, o = index_shape

    index_size_dim = index_shape[dim]
    # make unique indices
    for i in range(1 if dim == 0 else m):
        for j in range(1 if dim == 1 else n):
            for k in range(1 if dim == 2 else o):
                ii = [i, j, k]
                ii[dim] = slice(0, index.size(dim) + 1)
                index[tuple(ii)] = torch.randperm(size_dim)[0:index_size_dim]

    ref_inp = to_reference(inp)
    ref_index = to_reference(index)
    ref_src = to_reference(src)
    ref_out = torch.scatter(ref_inp, dim, ref_index, ref_src, reduce="multiply")
    with flag_gems.use_gems():
        res_out = torch.scatter(inp, dim, index, src, reduce="multiply")

    gems_assert_close(res_out, ref_out, dtype)


@pytest.mark.gather
@pytest.mark.parametrize(
    "inp_shape",
    [(32, 8, 4)] if QUICK_MODE else [(512, 128, 32), (1024, 64, 16), (128, 32, 256)],
)
@pytest.mark.parametrize("dim", [0, 1, 2])
@pytest.mark.parametrize("dtype", FLOAT_DTYPES)
def test_accuracy_gather(inp_shape, dim, dtype):
    inp = torch.randn(inp_shape, dtype=dtype, device="cuda")
    size_dim = inp_shape[dim]

    import random

    index_shape = [
        random.randint(1, inp_shape[0]),
        random.randint(1, inp_shape[1]),
        random.randint(1, inp_shape[2]),
    ]
    index = torch.empty(tuple(index_shape), dtype=torch.long, device="cuda")

    m, n, o = index_shape

    index_size_dim = index_shape[dim]
    # make unique indices
    for i in range(1 if dim == 0 else m):
        for j in range(1 if dim == 1 else n):
            for k in range(1 if dim == 2 else o):
                ii = [i, j, k]
                ii[dim] = slice(0, index.size(dim) + 1)
                index[tuple(ii)] = torch.randperm(size_dim)[0:index_size_dim]

    ref_inp = to_reference(inp)
    ref_index = to_reference(index)
    ref_out = torch.gather(ref_inp, dim, ref_index)

    with flag_gems.use_gems():
        res_out = torch.gather(inp, dim, index)

    gems_assert_equal(res_out, ref_out)


@pytest.mark.select_scatter
@pytest.mark.parametrize("shape", REDUCTION_SHAPES)
@pytest.mark.parametrize("dim", DIM_LIST)
@pytest.mark.parametrize("dtype", FLOAT_DTYPES)
def test_accuracy_select_scatter(shape, dim, dtype):
    import random

    index = random.randint(0, shape[dim] - 1)
    inp = torch.randn(shape, dtype=dtype, device="cuda")

    src_shape = list(inp.shape)
    del src_shape[dim]
    src = torch.randn(src_shape, dtype=dtype, device="cuda")

    ref_inp = to_reference(inp)
    ref_src = to_reference(src)
    ref_out = torch.select_scatter(ref_inp, dim=dim, index=index, src=ref_src)
    with flag_gems.use_gems():
        res_out = torch.select_scatter(inp, dim=dim, index=index, src=src)

    gems_assert_equal(res_out, ref_out)


@pytest.mark.slice_scatter
@pytest.mark.parametrize(("dim", "shape", "stride"), DIM_SHAPE_STRIDES)
@pytest.mark.parametrize("dtype", FLOAT_DTYPES)
@pytest.mark.parametrize("start", [16, 64])
@pytest.mark.parametrize("end", [1024, 256])
@pytest.mark.parametrize("step", [1, 2])
def test_accuracy_slice_scatter_v2(shape, stride, dim, dtype, start, end, step):
    inp = torch.empty_strided(shape, stride, dtype=dtype, device="cuda")
    inp.copy_(1)

    valid_shape = list(inp.shape)
    size = valid_shape[dim]

    start = start % size
    end = end % (size + 1)

    if end < start:
        end, start = start, end
    elif end == start:
        end = size

    valid_shape[dim] = (end - start + step - 1) // step

    src = torch.rand(valid_shape, dtype=dtype, device="cuda")

    ref_inp = to_reference(inp)
    ref_src = to_reference(src)
    ref_out = torch.slice_scatter(
        ref_inp, dim=dim, src=ref_src, start=start, end=end, step=step
    )
    with flag_gems.use_gems():
        res_out = torch.slice_scatter(
            inp, dim=dim, src=src, start=start, end=end, step=step
        )

    gems_assert_equal(res_out, ref_out)


@pytest.mark.slice_scatter
@pytest.mark.parametrize(("dim", "shape", "stride"), REGULAR_DIM_SHAPE_STRIDES)
@pytest.mark.parametrize("dtype", FLOAT_DTYPES)
@pytest.mark.parametrize("start", [16, 64])
@pytest.mark.parametrize("end", [1024, 256])
@pytest.mark.parametrize("step", [1, 2])
def test_accuracy_slice_scatter_fallback(shape, stride, dim, dtype, start, end, step):
    inp = torch.empty_strided(shape, stride, dtype=dtype, device="cuda")
    inp.copy_(1)

    valid_shape = list(inp.shape)
    size = valid_shape[dim]

    start = start % size
    end = end % (size + 1)

    if end < start:
        end, start = start, end
    elif end == start:
        end = size

    valid_shape[dim] = (end - start + step - 1) // step

    src = torch.rand(valid_shape, dtype=dtype, device="cuda")

    ref_inp = to_reference(inp)
    ref_src = to_reference(src)
    ref_out = torch.slice_scatter(
        ref_inp, dim=dim, src=ref_src, start=start, end=end, step=step
    )

    res_out = flag_gems.ops.slice_scatter(
        inp, dim=dim, src=src, start=start, end=end, step=step
    )

    gems_assert_equal(res_out, ref_out)


# TODO: failed at (200, 40999, 3)
@pytest.mark.index_select
@pytest.mark.parametrize("shape", REDUCTION_SHAPES)
@pytest.mark.parametrize("dim", DIM_LIST)
@pytest.mark.parametrize("dtype", FLOAT_DTYPES)
def test_accuracy_index_select(shape, dim, dtype):
    inp = torch.randn(shape, dtype=dtype, device="cuda")
    index_size = inp.size(dim)
    from math import floor

    index = torch.randint(0, index_size, [floor(index_size * 0.8)], device="cuda")

    ref_inp = to_reference(inp)
    ref_index = to_reference(index)
    ref_out = torch.index_select(ref_inp, dim, ref_index)
    with flag_gems.use_gems():
        res_out = torch.index_select(inp, dim, index)

    gems_assert_equal(res_out, ref_out)


@pytest.mark.masked_select
@pytest.mark.parametrize("threshold, shape", THRESHOLD_SHAPE)
@pytest.mark.parametrize("dtype", FLOAT_DTYPES)
def test_accuracy_masked_select(shape, dtype, threshold):
    inp = torch.randn(shape, dtype=dtype, device="cuda")
    mask = torch.randn(shape, dtype=dtype, device="cuda") < threshold

    ref_inp = to_reference(inp)
    ref_mask = to_reference(mask)
    ref_out = torch.masked_select(ref_inp, ref_mask)
    with flag_gems.use_gems():
        res_out = torch.masked_select(inp, mask)

    gems_assert_equal(res_out, ref_out)
