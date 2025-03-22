import argparse
import gc
from copy import deepcopy
from os import path as osp

import pytest

from dataset_generation.benchmark_generation.generate_episodes import (
    default_gen_config,
    generate_episode,
    get_generator_state_semantic_debug_info,
    initialize_generator,
)
from habitat_llm.agent.env.dataset import CollaborationDatasetV0
from habitat_llm.sims.metadata_interface import default_metadata_dict

if __name__ == "__main__":
    
    
    parser = argparse.ArgumentParser(description="Generate an episode")
    parser.add_argument(
        "--scene_dataset",
        type=str,
        default="data/hssd-hab/hssd-hab-partnr.scene_dataset_config.json",
        help="Path to the scene dataset JSON file"
    )
    parser.add_argument(
        "--scene_id",
        type=str,
        default="102817140",
        required=True,
        help="ID of the scene in the scene dataset"
    )
    parser.add_argument(
        "--in_file",
        type=str,
        required=True,
        help="Path to the JSON file containing the initial state"
    )
    parser.add_argument(
        "--out_file",
        type=str,
        required=True,
        help="Path to the output JSON file"
    )
    args = parser.parse_args()

    scene_dataset_path = args.scene_dataset
    print(f"Scene dataset path: {scene_dataset_path}")
    