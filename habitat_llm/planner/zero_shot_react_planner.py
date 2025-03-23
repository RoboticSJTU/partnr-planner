# Copyright (c) Meta Platforms, Inc. and affiliates.
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union

from habitat_llm.llm.instruct.utils import get_objects_descr
from habitat_llm.utils.grammar import FREE_TEXT
from scene_graph_sim.sayplan import *
from habitat_llm.planner import LLMPlanner
import json

if TYPE_CHECKING:
    from omegaconf import DictConfig

    from habitat_llm.agent.env import EnvironmentInterface
    from habitat_llm.world_model.world_graph import WorldGraph


class ZeroShotReactPlanner(LLMPlanner):
    """
    This class builds the prompt for the, zero shot llm react planner format.
    """

    def __init__(
        self, plan_config: "DictConfig", env_interface: "EnvironmentInterface"
    ) -> None:
        """
        Initialize the ZeroShotReactPlanner.

        :param plan_config: The planner configuration.
        :param env_interface: The environment interface.
        """
        
        super().__init__(plan_config, env_interface)
        self.planning_chunk = []
        
    def build_response_grammar(self, world_graph: "WorldGraph") -> str:
        """
        Build a grammar that accepts all valid responses based on a world graph.

        :param world_graph: The world graph.
        :return: The response grammar.
        """
        delimiter = "\\n"
        tool_rules = self.build_tool_grammar(world_graph)

        root_rule = (
            f'root ::= {FREE_TEXT} "{delimiter}" tool_call "{delimiter}Assigned!"'
        )

        return "\n".join([root_rule, tool_rules])

    def replan(
        self,
        instruction: str,
        observations: Dict[str, Any],
        world_graph: Dict[int, "WorldGraph"],
    ):
        """
        Replan a high level action using the LLM/VLM
        """
        if len(self.planning_chunk) ==0:
            # Generate response
            tmp_sg_path = "/tmp/tmp_sg.txt"
            with open(tmp_sg_path, "w") as f:
                f.write(world_graph[0].to_string())
            tmp_sg_json_path = "/tmp/tmp_sg.json"
            convert_wg_to_sg(tmp_sg_path, tmp_sg_json_path)
            _, _, _ = semantic_search(tmp_sg_json_path, instruction, "deepseek-chat")
            with open("/tmp/tmp_plan.json", "r") as f:
                full_plan = json.load(f)
            self.planning_chunk = full_plan
            tmp_ret = self.planning_chunk[0]
            self.planning_chunk = self.planning_chunk[1:]
        else:
            tmp_ret = self.planning_chunk[0]
            self.planning_chunk = self.planning_chunk[1:]
        llm_response = tmp_ret
        # Format the response
        # This removes extra text followed by end expression when needed.
        llm_response = self.format_response(llm_response, self.end_expression)
        info = {"llm_response": llm_response}
        return info



    def _add_responses_to_prompt(self, responses: Dict[int, str]) -> str:
        """
        Add skill responses to the prompt optionally including object descriptions (depending on the config).

        :param responses: A dictionary of agent responses.
        :return: The updated print string.
        """
        if self.planner_config.objects_response:
            assert len(self.agents) == 1
            agent = self.agents[0]
            result = ""
            world_graph = self.env_interface.world_graph[agent.uid]
            if responses[agent.uid] != "":
                response_format = (
                    "{user_tag}Result: {result}\nObjects: {objects}{eot_tag}"
                )
                objects = get_objects_descr(
                    world_graph,
                    agent.uid,
                    include_room_name=True,
                    add_state_info=self.planner_config.objects_response_include_states,
                )
                result = response_format.format(
                    result=responses[agent.uid],
                    objects=objects,
                    user_tag=self.planner_config.llm.user_tag,
                    eot_tag=self.planner_config.llm.eot_tag,
                )
                self.curr_prompt += result + self.planner_config.llm.assistant_tag
                # print(result + self.planner_config.llm.assistant_tag, end="")
                self.trace += result + self.planner_config.llm.assistant_tag
        else:
            result = super()._add_responses_to_prompt(responses)
        return result

    def get_next_action(
        self,
        instruction: str,
        observations: Dict[str, Any],
        world_graph: Dict[int, "WorldGraph"],
        verbose: bool = False,
    ) -> Tuple[Dict[int, Any], Dict[str, Any], bool]:
        """
        Get the next low-level action to execute.

        :param instruction: The instruction for the task.
        :param observations: The current observations.
        :param world_graph: The world graph for each agent.
        :param verbose: Whether to print verbose output. Defaults to False.
        :return: A tuple containing:
                 - The low-level actions for each agent
                 - Planner information
                 - Whether the planner is done
        """
        planner_info: Dict[str, Union[Any, str]] = {}
        # Early return if planner is already done
        if self.is_done:
            planner_info = {
                "prompts": {agent.uid: self.curr_prompt for agent in self.agents},
                "traces": {agent.uid: self.trace for agent in self.agents},
                "replanning_count": {
                    agent.uid: self.replanning_count for agent in self.agents
                },
                "replanned": {agent.uid: False for agent in self.agents},
                "replan_required": {
                    agent.uid: self.replan_required for agent in self.agents
                },
                "is_done": {agent.uid: self.is_done for agent in self.agents},
            }
            return {}, planner_info, self.is_done

        if self.curr_prompt == "":
            # Prepare prompts
            self.curr_prompt, self.params = self.prepare_prompt(
                instruction, world_graph[self._agents[0].uid], observations=observations
            )
            self.curr_obj_states = get_objects_descr(
                world_graph[self._agents[0].uid],
                self._agents[0].uid,
                include_room_name=True,
                add_state_info=self.planner_config.objects_response_include_states,
                centralized=self.planner_config.centralized,
            )

        if self.trace == "":
            self.trace += f"Task: {instruction}\nThought: "

        print_str = ""
        self.is_done = False

        if self.replan_required:
            planner_info["replanned"] = {agent.uid: True for agent in self.agents}
            if verbose:
                # calculate the total time of response generation
                start_time = time.time()

            response_info = self.replan(instruction, observations, world_graph)
            llm_response = response_info["llm_response"]
            # parse thought from the response
            thought = self.parse_thought(llm_response)
            
            if verbose:
                total_time = time.time() - start_time
                print(
                    f"Time taken for LLM response generation: {total_time}; replanning_count: {self.replanning_count}"
                )

            # Update prompt with the first response
            print_str += f"""{llm_response}\n{self.stopword}\n"""
            prompt_addition = (
                f"""{llm_response}\n{self.stopword}{self.planner_config.llm.eot_tag}"""
            )
            self.curr_prompt += prompt_addition
            self.trace += prompt_addition

            # Check if the planner should stop
            # Stop if the replanning count exceed a certain threshold
            # or end expression is found in llm response
            # This is helpful to break infinite planning loop.
            self.is_done = (self.check_if_agent_done(llm_response)) or (
                self.replanning_count == self.planner_config.replanning_threshold
            )
            # Increment the llm call counter on every replan
            # doesn't get incremented before comparison as first "replan" is technically
            # the first required plan
            self.replanning_count += 1

            # Early return if stop is required
            if self.is_done:
                planner_info = {
                    "print": print_str,
                    # "print_no_tags": print_str_no_tags,
                    "prompts": {agent.uid: self.curr_prompt for agent in self.agents},
                    "traces": {agent.uid: self.trace for agent in self.agents},
                    "replanning_count": {
                        agent.uid: self.replanning_count for agent in self.agents
                    },
                    "replan_required": {
                        agent.uid: self.replan_required for agent in self.agents
                    },
                    "replanned": {agent.uid: True for agent in self.agents},
                    "is_done": {agent.uid: self.is_done for agent in self.agents},
                    "thought": {agent.uid: thought for agent in self.agents},
                    "high_level_actions": {
                        agent.uid: ("Done", None, None) for agent in self.agents
                    },
                }
                return {}, planner_info, self.is_done

            if "Place" in llm_response:
                start = llm_response.find('[') + 1
                end = llm_response.find(']')
                params_str = llm_response[start:end]
                params = [p.strip() for p in params_str.split(',')]
                required_length = 5
                while len(params) < required_length:
                    params.append("None")
                # 4. 重组字符串
                llm_response = llm_response[:llm_response.find('[')+1] + ", ".join(params) + "]"
            # Parse high level action directives from llm response
            high_level_actions = self.actions_parser(
                self.agents, llm_response, self.params
            )
            # high_level_dir = "/home/jintian/Desktop/high_level_actions"
            # with open(f"{high_level_dir}/{self.replanning_count}.txt", "a") as f:
            #     f.writelines(llm_response)
            # import json
            # with open(f"{high_level_dir}/{self.replanning_count}.json", "a") as f:
            #     json.dump(high_level_actions, f, indent=4)
            # with open(f"{high_level_dir}/{self.replanning_count}.json", "r") as f:
            #     pseudo_plan = json.load(f)
            # def custom_deserializer(json_obj):
            #     if isinstance(json_obj, dict):
            #         return {int(k): tuple(v) if isinstance(v, list) else v for k, v in json_obj.items()}
            #     return json_obj
            # high_level_actions = custom_deserializer(pseudo_plan)
            # print('--------diff')
            # print(pseudo_plan, type(pseudo_plan))
            # print('---------')
            # print(high_level_actions, type(high_level_actions))
            # print("high_level_actionshigh_level_actionshigh_level_actions")
            # print(high_level_actions)
            print(f"\n\n[Info] Now Executing: {high_level_actions}\n\n")

            # Get low level actions and/or responses
            # print(f"ret----------------------")
            low_level_actions, responses = self.process_high_level_actions(
                high_level_actions, observations
            )
            # print(responses)

            # Store last executed high level action
            self.last_high_level_actions = high_level_actions
        else:
            planner_info["replanned"] = {agent.uid: False for agent in self.agents}
            # Set thought to None
            thought = None
            # Get low level actions and/or responses using last high level actions
            low_level_actions, responses = self.process_high_level_actions(
                self.last_high_level_actions, observations
            )

        # Log if replanning was done or not before overwriting the value
        planner_info["replan_required"] = {
            agent.uid: self.replan_required for agent in self.agents
        }

        # Check if replanning is required
        # Replanning is required when any of the actions being executed
        # have a response indicating success or failure (and the reason)
        # print(responses)
        # print("zzzzzzzzzzzzzzz")
        self.replan_required = any(responses.values())
        print_str += self._add_responses_to_prompt(responses)

        # Update planner info
        planner_info["responses"] = responses
        planner_info["thought"] = {agent.uid: thought for agent in self.agents}
        planner_info["is_done"] = {agent.uid: self.is_done for agent in self.agents}
        planner_info["print"] = print_str
        # planner_info["print_no_tags"] = print_str_no_tags
        planner_info["high_level_actions"] = self.last_high_level_actions
        planner_info["prompts"] = {agent.uid: self.curr_prompt for agent in self.agents}
        planner_info["traces"] = {agent.uid: self.trace for agent in self.agents}
        planner_info["replanning_count"] = {
            agent.uid: self.replanning_count for agent in self.agents
        }
        planner_info["agent_states"] = self.get_last_agent_states()
        planner_info["agent_positions"] = self.get_last_agent_positions()
        planner_info["agent_collisions"] = self.get_agent_collisions()
        return low_level_actions, planner_info, self.is_done

    def check_if_agent_done(self, llm_response: str) -> bool:
        """
        Check if the agent is done based on the LLM response.

        :param llm_response: The LLM response to check.
        :return: True if the agent is done, False otherwise.
        """
        return "done" in llm_response