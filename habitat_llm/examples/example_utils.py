#!/usr/bin/env python3

# Copyright (c) Meta Platforms, Inc. and affiliates.
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import os
import time
from typing import Any, Dict, List, Tuple
import subprocess
import threading

import cv2
import imageio
import numpy as np
from io import BytesIO

from habitat_llm.agent.env import EnvironmentInterface
from habitat_llm.examples.hls_client import HLSClient


class DebugVideoUtil:
    """
    This class provides an interface wrapper for creating, saving, and viewing third person videos of individual skill runs using the EnvironmentInterface API.

    For example, see `execute_skill` function below.
    NOTE: This code was largely adapted from the evaluation_runner.py
    """

    # HLS stream URL for streaming video
    # HLS_STREAM_URL = "http://localhost:8080/hls/stream.m3u8"
    

    def __init__(
        self, env_interface_arg: EnvironmentInterface, output_dir: str,
        stream_name: str = "simulation_stream"  # HLS流名称
    ) -> None:
        """
        Construct the DebugVideoUtil instance from an EnvironmentInterface.

        :param env_interface_arg: The EnvironmentInterface instance.
        :param output_dir: The desired directory for saving output frames and videos.
        """

        self.env_interface = env_interface_arg

        # Declare container to store frames used for generating video
        self.frames: List[Any] = []

        self.output_dir = output_dir

        self.num_agents = 0
        for _agent_conf in self.env_interface.conf.evaluation.agents.values():
            self.num_agents += 1

        # 初始化HLS客户端
        self.hls_client = HLSClient("http://localhost:5000")  # 根据服务器地址修改

        # create HLS stream
        self.ffmpeg_process = None
        # self.hls_output_path = f"{output_dir}/dvu_stream.m3u8"  # HLS输出路径
        self.target_fps = 30  # 根据实际情况调整帧率
        self.segment_duration = 1  # 每个TS分段时长（秒）
        self.segment_counter = 0
        self.current_segment = BytesIO()
        self.upload_thread = None
        self.running = True
        self.stream_name = stream_name  # HLS流名称
        
        # 创建推流目录结构
        if env_interface_arg.conf.evaluation.hls_streaming:
            print("Creating HLS stream...")
            self._init_streaming_paths()
    
    def _init_streaming_paths(self):
        """初始化推流路径"""
        self.m3u8_path = f"{self.stream_name}/playlist.m3u8"
        self.ts_pattern = f"{self.stream_name}/segment%03d.ts"
        
        # 初始化服务器端目录
        self.hls_client.push_file("", self.m3u8_path)  # 创建空m3u8文件
        
    def _start_upload_thread(self):
        """启动分段上传后台线程"""
        def upload_worker():
            while self.running:
                # 读取FFmpeg输出
                if self.ffmpeg_process is None:
                    print("FFmpeg进程未初始化")
                    break
                data = self.ffmpeg_process.stdout.read(4096)
                if not data:
                    continue
                
                # 写入内存缓冲区
                self.current_segment.write(data)
                
                # 达到分段时长时上传
                if self.current_segment.tell() / (self.target_fps * 1e6) >= self.segment_duration:
                    self._upload_segment()
                    self.segment_counter += 1
                    self.current_segment = BytesIO()
        
        self.upload_thread = threading.Thread(target=upload_worker)
        self.upload_thread.start()
        
    def _upload_segment(self):
        """上传单个TS分段和更新m3u8"""
        # 生成分段文件名
        ts_name = f"segment{self.segment_counter:04d}.ts"
        m3u8_path = f"{self.stream_name}/playlist.m3u8"
        
        # 上传TS文件
        self.hls_client.push_file(
            self.current_segment.getvalue(),
            f"{self.stream_name}/{ts_name}"
        )
        
        # 更新m3u8播放列表
        m3u8_content = f"#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:{self.segment_duration}\n"
        for i in range(max(0, self.segment_counter-5), self.segment_counter+1):
            m3u8_content += f"#EXTINF:{self.segment_duration},\nsegment{i:04d}.ts\n"
        self.hls_client.push_file(
            m3u8_content.encode(),
            m3u8_path
        )
    def _start_ffmpeg_process(self, width, height):
        """启动FFmpeg HLS推流进程"""
        print("Starting FFmpeg process...")
        command = [
            'ffmpeg',
            '-y',
            '-f', 'rawvideo',
            '-pix_fmt', 'bgr24',
            '-s', f'{width}x{height}',
            '-r', str(self.target_fps),
            '-i', '-',
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-hls_time', str(self.segment_duration),
            '-hls_list_size', '200',      # 播放列表保留的分段数
            '-hls_flags', 'delete_segments+append_list',
            '-hls_segment_filename', self.ts_pattern,  # 直接使用服务器路径模式
            self.m3u8_path
        ]
        
        return subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

    def __get_combined_frames(self, batch: Dict[str, Any]) -> np.ndarray:
        """
        For each agent, extract the observation from the "third_rgb" sensor and merge them into a single split-screen image.

        :param batch: A dict mapping observation names to values.
        :return: The composite image as a numpy array.
        """
        # Extract first agent frame
        images = []
        for obs_name, obs_value in batch.items():
            if "third_rgb" in obs_name:
                if self.num_agents == 1:
                    if "0" in obs_name or "main_agent" in obs_name:
                        images.append(obs_value)
                else:
                    images.append(obs_value)

        # Extract dimensions of the first image
        height, width = images[0].shape[1:3]

        # Create an empty canvas to hold the concatenated images
        concat_image = np.zeros((height, width * len(images), 3), dtype=np.uint8)

        # Iterate through the images and concatenate them horizontally
        for i, image in enumerate(images):
            concat_image[:, i * width : (i + 1) * width] = image.cpu()

        return concat_image

    def _store_for_video(
        self, observations: Dict[str, Any], hl_actions: Dict[int, Any]
    ) -> None:
        """
        Store a video with observations and text from an observation dict and an agent to action metadata dict.
        NOTE: Could probably go into utils?

        :param observations: A dict mapping observation names to values.
        :param hl_actions: A dict mapping agent action indices to actions.
        """
        frames_concat = self.__get_combined_frames(observations)
        frames_concat = np.ascontiguousarray(frames_concat)

        for idx, action in hl_actions.items():
            # text = f"Agent_{id}:{action[0]}[{action[1]}]"
            agent_name = "Human" if str(idx) == "1" else "Robot"
            text = f"{agent_name}: {action[0]}[{action[1]}]"
            frames_concat = cv2.putText(
                frames_concat,
                text,
                (20, (int(idx) + 1) * 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                (255, 255, 255),
                2,
            )

        self.frames.append(frames_concat)
        
        # Streaming frames to HLS
        # HLS推流处理
        if self.env_interface.conf.evaluation.hls_streaming:
            if self.ffmpeg_process is None:
                # 根据第一帧初始化FFmpeg
                h, w, _ = frames_concat.shape
                self.ffmpeg_process = self._start_ffmpeg_process(w, h)
                if self.ffmpeg_process is None:
                    print("FFmpeg进程启动失败")
                    return
                self._start_upload_thread()

            try:
                # 将帧写入FFmpeg管道
                # CV2的图像格式是BGR，FFmpeg要求的是RGB，所以这里需要转换
                rgb_frame = cv2.cvtColor(frames_concat, cv2.COLOR_BGR2RGB)
                self.ffmpeg_process.stdin.write(rgb_frame.tobytes())
            except BrokenPipeError as e:
                print(f"HLS流错误: {str(e)}")
                # 这里可以添加重新初始化逻辑
                self._restart_ffmpeg_process(frames_concat.shape)
            
            return
        
    def _restart_ffmpeg_process(self, frame_shape):
        """重启FFmpeg进程"""
        h, w, _ = frame_shape
        self.ffmpeg_process = self._start_ffmpeg_process(w, h)
        if self.ffmpeg_process is None:
            print("FFmpeg进程启动失败")
        self._start_upload_thread()
        print("FFmpeg进程已重启")
        
    def close_stream(self):
        self.running = False
        if self.upload_thread:
            self.upload_thread.join()
        """关闭推流资源"""
        if self.ffmpeg_process:
            self.ffmpeg_process.stdin.close()
            self.ffmpeg_process.wait()
            self.ffmpeg_process = None

    def _make_video(self, play: bool = True, postfix: str = "") -> None:
        """
        Makes a video from a pre-processed set of frames using imageio and saves it to the output directory.

        :param play: Whether or not to play the video immediately.
        :param postfix: An optional postfix for the video file name.
        """
        out_file = f"{self.output_dir}/videos/video-{postfix}.mp4"
        print(f"Saving video to {out_file}")
        os.makedirs(f"{self.output_dir}/videos", exist_ok=True)
        writer = imageio.get_writer(
            out_file,
            fps=30,
            quality=4,
        )
        for frame in self.frames:
            writer.append_data(frame)

        writer.close()
        
        # 关闭HLS推流
        if self.env_interface.conf.evaluation.hls_streaming:
            print("Closing HLS stream...")
            self.close_stream()
        if play:
            print("     ...playing video, press 'q' to continue...")
            self.play_video(out_file)

    def play_video(self, filename: str) -> None:
        """
        Play and loop video from a filepath with cv2.

        :param filename: The filepath of the video.
        """
        cap = cv2.VideoCapture(filename)
        last_time = time.time()
        while cap.isOpened():
            if time.time() - last_time > 1.0 / 30:
                last_time = time.time()
                ret, frame = cap.read()
                # cv2.namedWindow("window", cv2.WND_PROP_FULLSCREEN)
                # cv2.setWindowProperty("window",cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN)

                if ret:
                    cv2.imshow("Image", frame)
                else:
                    # looping
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue

                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

        cap.release()
        cv2.destroyAllWindows()


def execute_skill(
    high_level_skill_actions: Dict[Any, Any],
    llm_env,
    make_video: bool = True,
    vid_postfix: str = "",
    play_video: bool = True,
) -> Tuple[Dict[Any, Any], Dict[Any, Any], List[Any]]:
    """
    Execute a high-level skill from a string (e.g. as produced by the planner).
    Can create and display a video of the running skill.

    :param high_level_skill_actions: The map of agent indices to actions. TODO: typing
    :param llm_env: The planner instance. TODO: typing
    :param make_video: whether or not to create, save, and display a video of the skill.
    :param vid_postfix: An optional postfix for the video file. For example, the action name.
    :param play_video: Whether or not to immediately play the generated video.
    :return: A tuple with two dict(the first contains responses per-agent skill, the second contains the number of skill steps taken) and a list of frames.
    """
    dvu = DebugVideoUtil(
        llm_env.env_interface, llm_env.env_interface.conf.paths.results_dir
    )

    # Get the env observations
    observations = llm_env.env_interface.get_observations()
    agent_idx = list(high_level_skill_actions.keys())[0]
    skill_name = high_level_skill_actions[agent_idx][0]

    # Set up the variables
    skill_steps = 0
    max_skill_steps = 1500
    skill_done = None

    # While loop for executing skills
    while not skill_done:
        # Check if the maximum number of steps is reached
        assert (
            skill_steps < max_skill_steps
        ), f"Maximum number of steps reached: {skill_name} skill fails."

        # Get low level actions and responses
        low_level_actions, responses = llm_env.process_high_level_actions(
            high_level_skill_actions, observations
        )

        assert (
            len(low_level_actions) > 0
        ), f"No low level actions returned. Response: {responses.values()}"

        # Check if the agent finishes
        if any(responses.values()):
            skill_done = True

        # Get the observations
        obs, reward, done, info = llm_env.env_interface.step(low_level_actions)
        observations = llm_env.env_interface.parse_observations(obs)

        if make_video:
            dvu._store_for_video(observations, high_level_skill_actions)

        # Increase steps
        skill_steps += 1

    if make_video and skill_steps > 1:
        dvu._make_video(postfix=vid_postfix, play=play_video)

    return responses, {"skill_steps": skill_steps}, dvu.frames
