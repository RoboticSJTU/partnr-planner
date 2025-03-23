import os
import re
import sys
import json
import argparse
from openai import OpenAI
from rich.console import Console
from rich.json import JSON
from rich.table import Table
# sys.path.append('.')
# sys.path.append('/home/jintian/code/partnr-planner/third_party/scene_graph_sim')
# sys.path.append('/home/jintian/code/partnr-planner/third_party')
from scene_graph_sim.Simulator import Simulator
from dotenv import load_dotenv
from habitat_llm.utils import cprint
# from utils import remove_comments, call_LLM, update_sub_graph
import inflect

PROMPT_1 = """
Agent Role: You are an excellent graph planning agent. Given a graph representation of an environment, you can explore the graph by expanding nodes to find the items of interest. You can then use this graph to generate a step-by-step task plan that the agent can follow to solve a given instruction.
Environment Functions:
Navigate: [NAV_TARGET]
Pick: [OBJECT], If you pick something, you can't pick it again before you place the item in your hand.
Place: [OBJECT, SPATIAL_RELATION, FURNITURE], SPATIAL_RELATION can only be 'on'
Open: [FURNITURE]
Close: [FURNITURE]
Environment API:
expand(<node>): Reveal assets/objects connected to a room node.
contract(<node>): Hide assets/objects. After expanding a room node and the room does not have anything relevant towards solving this task, you should immediately contract the room node in the next step to reduce the number of input tokens to support longer tasks.
Your output must strictly conform to the Output Response Format below, and only the final result needs to be output.
Please output JSON data directly, do not use Markdown format.
Output Response Format(IMPORTANT NOTE: I will use json.loads() to parse the output, so you must follow the format, do not add any other characters.):
{chain_of_thought: break your problem down into a series of intermediate reasoning steps to help you determine your next command,
reasoning: justify why the next action is important
mode: "exploring" OR "planning"
command: {
"command_name": In exploring mode, choose a commmand between "expand" and "contract". In planning mode, should be ""
"node_name": node to perform "expand" or "contract" in exploring mode, empty otherwise
"plan": complete task plan if in planning mode, refering to the <Example during planning mode>, which is a list of actions}}
Instruction: Natural language description of the task
3D Scene Graph: Text-serialised JSON description of a 3D scene graph
Memory: History of previously expanded nodes
Feedback: External textual feedback from scene graph simulator Ensure the response can be parsed by Python json.loads.
Example during exploring mode:
{
Instruction: bring some food for Tom and place it in his room
3D Scene Graph: {nodes: {room: [{id: bobs_room}, {id: toms_room}, {id: jacks_room}, {id: kitchen}, {id: livingroom}], agent: [{location: bobs_room, id: agent}]}, links: []}
Memory: []
SayPlan [Mode->Search]: chain-of-thought: explore graph to find some food and somewhere in toms room where can place the food -> perform common sense exploration first -> explore kitchen where there might be food -> if items not found then explore other nodes 
command: expand(kitchen)
Scene Graph Simulator: {nodes: {room: [{id: bobs_room}, {id: toms_room}, {id: jacks_room}, {id: kitchen}, {id: livingroom}], agent: [{location: bobs_room, id: agent}], asset: [{id: counter1, room: kitchen, affordance: [place], attributes: [clean]}], object: [{id: apple1, room: kitchen, parent: counter1, affordances: [pick, place], attributes: [red]}, {id: bow1, room: kitchen, parent: counter1, affordances: [pick, place], attributes: [empty]}]}, links: [kitchen↔counter1, counter1↔apple1, counter1↔bow1]}
Memory: [kitchen]
SayPlan [Mode->Search]: chain-of-thought:in the kitchen, i've found the apple1, the food, on the counter  -> i will explore toms room to find a place to put the apples ->  i will try tom's room next 
reasoning: i will expand toms room next 
command: expand(toms_room)
Scene Graph Simulator: {nodes: {room: [{id: bobs_room}, {id: toms_room}, {id: jacks_room}, {id: kitchen}, {id: livingroom}], agent: [{location: bobs_room, id: agent}], asset: [{id: counter1, room: kitchen, affordance: [place], attributes: [clean]}, {id: desk1, room: toms_room, affordance: [place], attributes: [clean]}], object: [{id: apple1, room: kitchen, parent: counter1, affordances: [pick, place], attributes: [red]}, {id: bow1, room: kitchen, parent: counter1, affordances: [pick, place], attributes: [empty]}, {id: book1, room: toms_room, parent: desk1, affordances: [pick, place], attributes: [closed]}]}, links: [kitchen↔counter1, toms_room↔desk1 counter1↔apple1, counter1↔bow1, desk1↔book1]}
Memory: [kitchen, toms_room]
SayPlan [Mode->Search]: chain-of-thought: i have found the apple and tom's desk on the graph -> search complete -> I will switch to planning mode-> navigate to counter and pick the apple ->  navigate to tom's desk and place apple1
reasoning: I will generate a task plan using the identified subgraph
}
Example during planning mode:
{
Instruction: bring some food for Tom and place it in his room
3D Scene Graph: {nodes: {room: [{id: bobs_room}, {id: toms_room}, {id: jacks_room}, {id: kitchen}, {id: livingroom}], agent: [{location: bobs_room, id: agent}], asset: [{id: counter1, room: kitchen, affordance: [place], attributes: [clean]}, {id: desk1, room: toms_room, affordance: [place], attributes: [clean]}], object: [{id: apple1, room: kitchen, parent: counter1, affordances: [pick, place], attributes: [red]}, {id: bow1, room: kitchen, parent: counter1, affordances: [pick, place], attributes: [empty]}, {id: book1, room: toms_room, parent: desk1, affordances: [pick, place], attributes: [closed]}]}, links: [kitchen↔counter1, toms_room↔desk1 counter1↔apple1, counter1↔bow1, desk1↔book1]}
Memory: [kitchen, toms_room]
SayPlan [Mode->Planning]: chain-of-thought: "i have found the apple and tom's desk on the graph -> search complete -> I will switch to planning mode-> navigate to counter and pick the apple ->  navigate to tom's desk and place apple1" 
reasoning: I will generate a task plan using the identified subgraph 
plan: ["Navigate[kitchen]", "Navigate[counter1]", "Pick[apple1]", "Navigate[toms_room]", "Navigate[desk1]", "Place[apple1, on ,desk1]", "done"]
}
"""


# 获取当前工作目录并添加src路径
# current_dir = os.getcwd()
# sys.path.append(os.path.join(current_dir, 'src'))
# from utils import semantic_search
# from constants import TASKS

# 设置命令行参数解析
# parser = argparse.ArgumentParser()
# parser.add_argument('-n', '--model_name', type=str, default="gpt-4o", help='语言模型的名称')
# # parser.add_argument('-bn', '--building_name', type=str, default="Allensville", help='语言模型的名称')
# # parser.add_argument('-ts', '--task', type=str, default="Open the oven and clean it.", help='任务')

# args = parser.parse_args() 

def update_sub_graph(simulator, response, memory):
    response = remove_comments(response)
    response_json = json.loads(response)
    command = response_json['command']['command_name']
    node_name = response_json['command']['node_name']
    if node_name not in simulator.get_room_list():
        return
    if command == "expand":
        memory.append(node_name)
        simulator.expand(node_name)
    elif command == "contract":
        simulator.contract(node_name)

def call_LLM(model_name, messages):
    load_dotenv(override=True)
    # OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_API_KEY = "sk-8ad8780714b7462d950860ee8f9dc4c8"
    endpoint = "https://api.deepseek.com/v1"
        # self.client = AzureOpenAI(
        #     api_version="2024-06-01",
        #     api_key=api_key,
        #     azure_endpoint=f"https://{endpoint}",
        # )
    client = OpenAI(
            api_key=OPENAI_API_KEY, base_url=endpoint)
    # client = OpenAI(api_key=OPENAI_API_KEY)
    try:
        response = ""
        stream = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            stream=True,
            temperature=0.0# 启用流式
        )

        # 逐块处理响应
        for chunk in stream:
            if chunk.choices:  # 确保 choices 存在
                delta = chunk.choices[0].delta
                if delta and delta.content:  # 提取内容
                    cprint(delta.content, end="", flush=True, color="green")
                    response += delta.content
    except Exception as e:
        print(e)
    # 使用正则表达式提取最大范围的花括号
    pattern = r'```json\s*({.*})\s*```'
    match = re.search(pattern, response, re.DOTALL)
    if match:
        json_content = match.group(1)
        return json_content
    else:
        return response

def remove_comments(json_str):
    """
    Remove comments (//) from the given JSON string so it can be parsed as a valid JSON structure.
    Args:
    - json_str: str, The JSON string with comments.

    Returns:
    - str, The JSON string with comments removed.
    """
    # 使用正则表达式去除以 // 开头的注释
    cleaned_json_str = re.sub(r'//.*', '', json_str)
    
    # 返回去除注释后的字符串
    return str(cleaned_json_str)

def check_consecutive_pickups(plan):
    """
    检查 plan 列表中是否出现连续多个 pickup 操作
    """
    last_was_pickup = False
    for i, step in enumerate(plan):
        if step.startswith("Pick"):
            if last_was_pickup:
                
                return 'There are continuous pickup operations, and the agent can only pick up one item at a time.'
            last_was_pickup = True
        else:
            last_was_pickup = False
    return True
console = Console()
def print_reply_rich(reply, step=None):
    title = f"Semantic Search Reply"
    if step is not None:
        title += f" - Step {step + 1}"
    console.rule(f"[bold cyan]{title}")

    # 如果是 dict，就转成 json 字符串
    if isinstance(reply, dict):
        reply = json.dumps(reply, indent=2, ensure_ascii=False)

    console.print(JSON(reply))
    console.rule()


def number_to_ordinal(number):
    p = inflect.engine()
    return p.ordinal(number)

def print_plan_rich(plan_list, step=None):
    title = f"Task Plan"
    if step is not None:
        title += f" - Step {step + 1}"
    console.rule(f"[bold magenta]{title}")

    if not plan_list:
        console.print("[bold red]⚠️ No plan found.[/bold red]")
        return

    table = Table(show_header=True, header_style="bold blue")
    table.add_column("Step", justify="right", width=6)
    table.add_column("Action", style="green")

    for i, step in enumerate(plan_list, 1):
        table.add_row(str(i), step)

    console.print(table)
    console.rule()
def semantic_search(scene_graph_path, task, model_name):
    llm_count = 0
    sim = Simulator()
    sim.load_scene(scene_graph_path)
    sim.collapse()
    expanded_nodes = []
    messages = [{"role": "system", "content": PROMPT_1}]
    faliure_count = 0
    while faliure_count < 5:
        if messages[-1]['role'] != 'user': 
            user_input = "Instruction: " + task + "\nScene Graph Simulator:" + str(sim.sub_graph.to_json()) + "\nMemory: " + str(expanded_nodes) + "\n"
            messages.append({"role": "user", "content": user_input})
        
        cprint("\n---------------------------------", "light")
        cprint(f"{number_to_ordinal(llm_count+1)} time calling LLM", "light")
        cprint("\n---------------------------------", "light")
        # cprint("Please press any button to continue.", "red")
        # input()
        
        gpt_reply = remove_comments(call_LLM(model_name, messages))
        llm_count += 1
        try:
            gpt_reply_json = json.loads(gpt_reply)
        except Exception as e:
            print(e)
            faliure_count += 1
            if faliure_count == 5:
                raise Exception('semantic search failed' + str(e))
            continue
        if gpt_reply_json['mode'] == 'exploring':
            if gpt_reply_json['command']['command_name'] != 'expand' and gpt_reply_json['command']['command_name'] != 'contract':
                print('invalid command in exploring mode')
                faliure_count += 1
                if faliure_count == 5:
                    raise Exception('semantic search failed: invalid command in exploring mode')
                continue
            else:
                if gpt_reply_json['command']['node_name'] not in sim.get_room_list():
                    messages.append({"role": "assistant", "content": gpt_reply})
                    messages.append({"role": "user", "content": "in exploring mode, the node name should be the room name"})
                else:
                    messages.append({"role": "assistant", "content": gpt_reply})
                    update_sub_graph(sim, gpt_reply, expanded_nodes)
                faliure_count = 0
        else:
            # print('plan: ', gpt_reply_json['command']['plan'])
            
            plan = gpt_reply_json['command']['plan']
            check_result = check_consecutive_pickups(plan)
            if check_result != True:
                messages.append({"role": "assistant", "content": gpt_reply})
                messages.append({"role": "user", "content": check_result})
                cprint("\n---------------------------------", "red")
                cprint("\n Plan is not executable, force LLM to replan", "red")
                # cprint("Please press any button to continue.", "red")
                # input()
            else:
                # print_plan_rich(gpt_reply_json['command']['plan'])
                cprint("\n---------------------------------", "green")
                cprint("\n We got a good plan, now it's time to MINGLE!", "green")
                cprint("Please press any button to continue.", "green")
                input()
               
                with open("/tmp/tmp_plan.json", "w") as f:
                    json.dump(gpt_reply_json['command']['plan'], f, indent=4)
                return str(sim.sub_graph.to_json()), llm_count, sim

def convert_wg_to_sg(wg_path, sg_path):
    with open(wg_path, 'r') as f:
        wg = f.read()
    lines = wg.strip().split('\n')
    sg = {
        "nodes": {
            "room": [],
            "asset": [],
            "object": []
        },
        "links": []
    }
    
    current_room = None
    current_furniture = None
    
    for line in lines:
        line = line.strip()
        if line.startswith("Room:"):
            current_room = line.split(":")[1].strip()
            sg["nodes"]["room"].append({"id": current_room})
        elif line.startswith("Furniture:"):
            furniture_id = line.split(":")[1].strip()
            sg["nodes"]["asset"].append({"id": furniture_id, "room": current_room, "affordances": ["place"], "attributes": []})
            # if "table" in furniture_id:
            current_furniture = furniture_id
            sg["links"].append(f"{current_room}↔{furniture_id}")
        # elif line.startswith("Receptacle:"):
        #     receptacle_id = line.split(":")[1].strip()
        #     sg["nodes"]["position"].append({"id": receptacle_id})
        #     sg["links"].append(f"{furniture_id}↔{receptacle_id}")
        elif line.startswith("Object:"):
            object_id = line.split(":")[1].strip()
            sg["nodes"]["object"].append({"id": object_id, "room": current_room, "parent": current_furniture, "affordances": ["pick", "place"], "attributes": []})
            sg["links"].append(f"{current_furniture}↔{object_id}")

    sg["nodes"]["agent"] = [{"location": sg["nodes"]["room"][0]["id"], "id": "agent"}]
    with open(sg_path, 'w+') as f:
        json.dump(sg, f, indent=2, ensure_ascii=False)
    return sg

project_path = '/Users/liyang/Documents/code/SGSimulatorPy'
sg_path = os.path.join(project_path, 'data/3DSceneGraph_Gibson_2/merge_graph/3DSceneGraph_{}.json')
office_path = os.path.join(project_path, 'data/3DSceneGraph_Gibson_2/office.json')

if __name__ == "__main__":
    # print(f'building_name: {args.building_name}')
    # print(f'task: {args.task}')

    task = 'I just came back from shopping. I put all the things I bought in the living room. Please take some snacks to bedroom 2 for me, and storage the other food in the kitchen.'
    # wg_path = '/Users/liyang/Documents/code/partnr-planner/my_files/world_graph_0.txt'
    # sg_path = '/Users/liyang/Documents/code/partnr-planner/my_files/scene_graph_0.json'
    
    # convert_wg_to_sg(wg_path, sg_path)

    sg_path = '/home/jintian/Documents/xwechat_files/cjt171333003_a4ad/msg/file/2025-03/scene_graph_0_modify.json'

    load_dotenv(override=True)
    MODEL_NAME = os.getenv("MODEL_NAME")
    model_name = args.model_name if args.model_name != None else MODEL_NAME

    
    searched_graph, semantic_search_count, sim = semantic_search(sg_path,  task, model_name)
            
        