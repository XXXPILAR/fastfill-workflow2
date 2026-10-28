# local stub replacing SceneEval's registry: the decorators register nothing
def register_non_vlm_metric(config_class=None):
    return lambda cls: cls
def register_vlm_metric(config_class=None):
    return lambda cls: cls
