#!/usr/bin/env python3

# Copyright (c) Meta Platforms, Inc. and affiliates.
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree

import os
import random
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import torch
from habitat.config.default_structured_configs import (
    HabitatConfigPlugin,
    register_hydra_plugin,
)
from habitat_baselines.config.default_structured_configs import (
    HabitatBaselinesConfigPlugin,
)
from hydra import compose, initialize
from hydra.core.hydra_config import HydraConfig
from omegaconf import DictConfig, OmegaConf, open_dict


def get_config(config_file: str, overrides: List[str] = None) -> DictConfig:
    """
    Creates a base config object from a file and passes it to calling function to be tweaked as needed
    """
    with initialize(version_base=None, config_path="../conf"):
        config = compose(
            config_name=config_file,
            overrides=overrides,
        )
    HydraConfig().cfg = config
    # emulate a regular hydra initialization
    with open_dict(config):
        config.hydra = {}
        config.hydra.runtime = {}  # type: ignore
        config.hydra.runtime.output_dir = "outputs/test"  # type: ignore
    return config


def get_random_seed():
    """
    Generates random seed.
    """
    seed = (
        os.getpid()
        + int(datetime.now().strftime("%S%f"))
        + int.from_bytes(os.urandom(2), "big")
    )
    print("Using a generated random seed {}".format(seed))
    return seed


# resolver used for setting hydra output path based on dataset
OmegaConf.register_new_resolver("file_stem", lambda x: Path(x).stem)


def fix_config(cfg, root: bool = True) -> None:
    """
    Recursive function to fix all vars in a config. Resolves interpolations relying on Hydra global state immediately to prevent downstream resolution issues when the global state is changed (e.g. by another process).
    This is an in-place operation.

    NOTE: fix for multi-process hydra resolver issues from https://github.com/ashleve/lightning-hydra-template/issues/495

    :param root: Whether or not this is the root config of the recursion.
    """
    keys = list(cfg.keys())
    if root:
        # skip habitat config because this config is missing required param
        keys = [k for k in keys if k not in ["habitat", "habitat_baselines"]]
    for k in keys:
        if type(cfg[k]) is DictConfig:
            fix_config(cfg[k], False)
        else:
            setattr(cfg, k, getattr(cfg, k))


def setup_config(config: DictConfig = None, seed: int = 47668090) -> DictConfig:
    """
    Setups the random seed and the wandb logger.
    """

    # Exit if config is not provided
    if config is None:
        print("Config file must be provided.")
        return None

    # Habitat environment variables
    os.environ["GLOG_minloglevel"] = "3"  # noqa: SIM112
    os.environ["MAGNUM_LOG"] = "quiet"
    os.environ["HABITAT_SIM_LOG"] = "quiet"

    # Register habitat hydra plugins
    register_hydra_plugin(HabitatBaselinesConfigPlugin)
    register_hydra_plugin(HabitatConfigPlugin)

    # Set random seed
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    with open_dict(config):
        # Add the seed to the config
        config.habitat.seed = seed

        # Agent setup
        config.habitat.simulator.agents_order = sorted(
            config.habitat.simulator.agents.keys()
        )

        # Add the wandb information to the habitat config
        if "WANDB" in config:
            config.habitat_baselines.wb.project_name = config.WANDB.project
            config.habitat_baselines.wb.run_name = config.WANDB.name
            config.habitat_baselines.wb.group = config.WANDB.group
            config.habitat_baselines.wb.entity = config.WANDB.entity

        # Propagate the metadata folder config to the simulator
        config_dict = OmegaConf.create(
            OmegaConf.to_container(config.habitat, resolve=True)
        )
        # TODO: refactor this. We shouldn't need to copy configs into other subconfigs to pass information. This is done now because CollaborationSim needs metadata paths for init.
        config_dict.simulator.metadata = config.habitat.dataset.metadata
        config.habitat = config_dict

    print("Finished setting up config")

    return config


def cprint(text: str, color: str = None, end: str = "\n", flush=False) -> None:
    """
    Wrapper around print to set the text color from a pre-defined list of options.

    :param text: The string to print.
    :param color: The name of the color to use. From ["red", "green", "blue", "gray", "yellow", None]
    :param end: string appended after the last value, default newline.
    """
    def print_color(text, fg, bg):
        print(f"\033[38;2;{fg[0]};{fg[1]};{fg[2]}m\033[48;2;{bg[0]};{bg[1]};{bg[2]}m{text}\033[0m", end=end, flush=flush)

    # 1. 深海组合
    navy_fg = (20, 40, 60)        # 深海军蓝
    mist_bg = (200, 215, 220)     # 雾灰色

    # 2. 苔藓组合
    moss_fg = (50, 70, 40)        # 暗苔藓绿
    parchment_bg = (230, 220, 200) # 羊皮纸色

    # 3. 暮色组合
    dusk_fg = (90, 60, 80)        # 暮紫色
    dawn_bg = (240, 230, 235)     # 黎明粉

    # 4. 砂岩组合
    sienna_fg = (120, 80, 60)     # 赭石色
    sand_bg = (245, 235, 220)     # 沙色

    # 5. 钢灰组合
    slate_fg = (60, 70, 80)       # 板岩灰
    pearl_bg = (230, 235, 240)    # 珍珠白

    # 6. 咖啡组合
    espresso_fg = (70, 50, 40)    # 浓缩咖啡色
    latte_bg = (245, 240, 230)    # 拿铁色
    if color is None:
        print(text, end=end)
    elif color == "red":
        print_color(text, dusk_fg, dawn_bg)
    elif color == "green":
        print_color(text, moss_fg, parchment_bg)
    elif color == "blue":
        print_color(text, navy_fg, mist_bg)
    elif color == "gray":
        print_color(text, slate_fg, pearl_bg)
    elif color == "yellow":
        print_color(text, sienna_fg, sand_bg)
    elif color == "light":
        print_color(text, espresso_fg, latte_bg)
    else:
        raise NotImplementedError(f"Requested color name '{color}' is not supported.")


def rollout_print(text: str) -> None:
    """
    Print an LLM planner responses to console with specific formatting.

    :param text: The string response from the LLM planner.
    """
    for line in text.splitlines():
        # Skip if the line its empty
        if not line:
            continue

        # Split the line into prefix and postfix if it contains ":"
        if ":" in line:
            prefix = line.split(":", 1)[0] + ":"
            postfix = line.split(":", 1)[1]
        else:
            prefix = f"{line}\n"
            postfix = None

        # Remove any leading spaces
        prefix = prefix.lstrip()

        # if any(word in prefix.lower() for word in ["action", "assigned"]):
        #     cprint(prefix, "red", end=" ")
        # elif any(word in prefix.lower() for word in ["observation"]):
        #     cprint(prefix, "green", end=" ")
        # elif any(word in prefix.lower() for word in ["thought", "final"]):
        #     cprint(prefix, "blue", end=" ")
        # else:
        #     cprint(prefix, "gray", end=" ")

        if any(word in prefix.lower() for word in ["_0_"]):
            cprint(prefix, "red", end=" ")
        elif any(word in prefix.lower() for word in ["_1_"]):
            cprint(prefix, "green", end=" ")
        else:
            cprint(prefix, "gray", end=" ")

        if postfix:
            cprint(postfix, "gray")


def separate_agent_idx(key: str) -> Tuple[str, str]:
    """
    A helper function to separate the agent index from the observation key string.
    """
    keys = key.split("_")
    return "_".join(keys[0:2]), "_".join(keys[2:])


def save_data(save_path: str, save_name: str, data: List[Dict[str, Any]]) -> None:
    """
    Save the 'data' in .csv format with the provided name at the provided system path.

    :param save_path: The directory in which to save the data csv.
    :param save_name: The name of the csv file to save.
    :param data: The data to serialize. Expected to be a list of indexed entries. Each element is a Dict containing str keys ["instruction", "minimum_number_of_actions", "type", "success", "score", "efficiency_score", "step_count", "llm_call_count", "error"].
    """

    # Create save path
    os.makedirs(save_path, exist_ok=True)

    with open(save_path + "/" + save_name + ".csv", "w") as f:
        f.write(
            "index,instruction,minimum_number_of_actions,type,success,score,efficiency_score,step_count,llm_call_count,error\n"
        )

        for index, item in enumerate(data):
            f.write(
                f'{index},{item["instruction"]},{item["minimum_number_of_actions"]},{item["type"]},{item["success"]},{item["score"]},{item["efficiency_score"]},{item["step_count"]},{item["llm_call_count"]},{item["error"]}\n'
            )
