"""model.inference_autocast_bf16: the backbone runs under bf16 autocast in eval mode only; off by default, so earlier
checkpoints evaluate as before and their resume digest is unchanged."""
import pytest
import torch

from fastfill.v2 import train
from fastfill.v2.batch import TinyTokenizer, collate_samples
from fastfill.v2.model import ModelConfig, build_model, model_inputs
from fastfill.v2.tests.test_execution import sample


def _backbone_autocast(flag, training):
    """The autocast dtype the backbone ran under (None: no autocast); the decoder's outputs stay float32."""
    model = build_model(ModelConfig(backbone="tiny", lora_rank=0, train_backbone=True, inference_autocast_bf16=flag))
    model.train(training)
    seen = []
    model.backbone.register_forward_pre_hook(
        lambda module, args: seen.append(torch.get_autocast_dtype("cpu") if torch.is_autocast_enabled("cpu") else None))
    batch = collate_samples([sample()], TinyTokenizer(), max_length=4096, max_objects=model.config.max_objects)
    with torch.set_grad_enabled(training):
        predictions = model(**model_inputs(batch))
    assert torch.isfinite(predictions["size"]).all() and predictions["size"].dtype == torch.float32
    assert not torch.is_autocast_enabled("cpu")  # left after the backbone
    return seen[0]


@pytest.mark.parametrize("flag, training, expected", [(True, False, torch.bfloat16), (True, True, None), (False, False, None)])
def test_backbone_runs_under_bf16_autocast_only_at_inference_with_the_flag(flag, training, expected):
    assert _backbone_autocast(flag, training) == expected


def test_flag_is_a_boolean_off_by_default_and_left_out_of_the_resume_digest():
    assert ModelConfig(backbone="tiny").inference_autocast_bf16 is False
    with pytest.raises(ValueError, match="inference_autocast_bf16 must be a boolean"):
        ModelConfig(backbone="tiny", inference_autocast_bf16=1)
    assert train._digest_view({"model": {"inference_autocast_bf16": False}}) == {"model": {}}
    assert train._digest_view({"model": {"inference_autocast_bf16": True}}) == {"model": {"inference_autocast_bf16": True}}
