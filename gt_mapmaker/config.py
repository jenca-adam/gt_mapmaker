import os
import yaml
import importlib
import sys
import gt_api
from .err import MapMakerError

REQUIRED = {
    "token",
    "map_type",
    "map_id",
    "drop_picker",
    "num_threads",
}


def module_from_file(file_path):
    module_name = os.path.splitext(os.path.split(file_path)[1])[0]
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class Config(dict):
    def __init__(self, file_path="config.yaml"):
        if not os.path.exists(file_path):
            raise MapMakerError(
                f"No config file found at {file_path!r}. Please refer to the documentation."
            )
        with open(file_path, "r") as f:
            try:
                config = yaml.load(f, yaml.Loader)
                assert isinstance(config, dict), "Not a dictionary"
            except Exception as e:
                raise MapMakerError(f"Config file malformed: {str(e)}") from None
        missing = REQUIRED.difference(config.keys())
        if missing:
            raise MapMakerError(f"Config missing required keys: {missing}")
        if config["map_type"] not in ("single", "grouped"):
            raise MapMakerError(
                f"Invalid map type {config['map_type']!r}: must be one of 'single', 'grouped'"
            )
        if config["map_type"] == "grouped" and "group_picker" not in config:
            raise MapMakerError(f"Missing required key 'group_picker' for grouped maps")
        if config["map_type"] == "single" and "num_drops" not in config:
            raise MapMakerError(f"Missing required key 'num_drops' for single maps")
        drop_picker_module = module_from_file(config["drop_picker"])
        if not hasattr(drop_picker_module, "pick_drop"):
            raise MapMakerError(f"Drop picker needs to have pick_drop defined")
        self.pick_drop = drop_picker_module.pick_drop
        if "group_picker" in config:
            group_picker_module = module_from_file(config["group_picker"])
            if not hasattr(group_picker_module, "pick_group"):
                raise MapMakerError(f"Group picker needs to have pick_group defined")
            self.pick_group = group_picker_module.pick_group
        else:
            self.pick_group = None
        self.client = gt_api.Client(config["token"])
        super().__init__(config)
