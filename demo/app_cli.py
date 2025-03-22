"""
Demo CLI application

1. generate episode data

2. reset scene

3. get rendering result

4. run episode

"""

import sys
import os
import hydra
from omegaconf import DictConfig
from omegaconf import OmegaConf
from habitat_llm.utils import cprint, setup_config, fix_config

dataset_cfg_path = 'demo/dataset.yaml'

@hydra.main(config_path="../habitat_llm/conf")
def main(cfg: DictConfig) -> None:
    dataset_cfg = OmegaConf.load(dataset_cfg_path)
    print(dataset_cfg)
    
    return

if __name__ == '__main__':
    
    main()
    
    print('done')
    sys.exit(0)
