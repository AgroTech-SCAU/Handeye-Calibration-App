"""A generic ROS2 MoveIt2 MoveGroup action client

The robot side owns planning, collision checking, joint limits, hardware safety
and motion execution. This client never accesses motor drivers
"""
from __future__ import annotations
import threading
import time

class MoveGroupMotion:
    def __init__(self, action_name, group_name, timeout=18., velocity=.08):
        self.action_name=action_name
        self.group_name=group_name
        self.timeout=float(timeout)
        self.velocity=float(velocity)
        self.cancel_event=threading.Event()
        self._goal=None
        self._node=None
        self._client=None

    def cancel(self):
        self.cancel_event.set()
        goal=self._goal
        if goal is not None:
            try:goal.cancel_goal_async()
            except Exception:pass

    def execute(self, base_frame, target_link, position, quaternion, feedback=None):
        if self.cancel_event.is_set():raise RuntimeError('运动已取消')
        try:
            import rclpy
            from rclpy.action import ActionClient
            from moveit_msgs.action import MoveGroup
            from moveit_msgs.msg import Constraints, PositionConstraint, OrientationConstraint, BoundingVolume
            from shape_msgs.msg import SolidPrimitive
            from geometry_msgs.msg import Pose
        except ImportError as exc:
            raise RuntimeError('未安装 ROS2 MoveIt2 依赖 moveit_msgs / shape_msgs，机器人需提供 MoveGroup Action') from exc
        if not rclpy.ok():rclpy.init(args=None)
        node=rclpy.create_node('handeye_servo_movegroup_client')
        self._node=node
        client=ActionClient(node,MoveGroup,self.action_name)
        self._client=client
        try:
            if not client.wait_for_server(timeout_sec=2.0):
                raise RuntimeError(f'机器人未提供运动 Action {self.action_name}，请启动并配置 MoveIt2')
            goal=MoveGroup.Goal()
            request=goal.request
            request.group_name=self.group_name
            request.allowed_planning_time=min(self.timeout/2,8.)
            request.num_planning_attempts=2
            request.max_velocity_scaling_factor=self.velocity
            request.max_acceleration_scaling_factor=min(self.velocity,.08)
            request.start_state.is_diff=True
            c=Constraints()
            pos=PositionConstraint()
            pos.header.frame_id=base_frame
            pos.link_name=target_link
            pos.weight=1.
            volume=BoundingVolume()
            sphere=SolidPrimitive();sphere.type=SolidPrimitive.SPHERE;sphere.dimensions=[.004]
            anchor=Pose();anchor.position.x=float(position[0]);anchor.position.y=float(position[1]);anchor.position.z=float(position[2]);anchor.orientation.w=1.
            volume.primitives.append(sphere);volume.primitive_poses.append(anchor)
            pos.constraint_region=volume
            c.position_constraints.append(pos)
            orient=OrientationConstraint()
            orient.header.frame_id=base_frame
            orient.link_name=target_link
            orient.orientation.x=float(quaternion[0]);orient.orientation.y=float(quaternion[1]);orient.orientation.z=float(quaternion[2]);orient.orientation.w=float(quaternion[3])
            orient.absolute_x_axis_tolerance=.035
            orient.absolute_y_axis_tolerance=.035
            orient.absolute_z_axis_tolerance=.035
            orient.weight=1.
            c.orientation_constraints.append(orient)
            request.goal_constraints=[c]
            goal.planning_options.plan_only=False
            goal.planning_options.replan=False
            goal.planning_options.look_around=False
            deadline=time.monotonic()+self.timeout
            send=client.send_goal_async(goal,feedback_callback=lambda msg:feedback(str(getattr(msg.feedback,'state',''))) if feedback else None)
            while not send.done():
                if self.cancel_event.is_set():raise RuntimeError('运动已取消')
                if time.monotonic()>deadline:raise TimeoutError('等待机器人接收运动目标超时')
                rclpy.spin_once(node,timeout_sec=.05)
            handle=send.result()
            if not handle.accepted:raise RuntimeError('机器人拒绝了运动请求')
            self._goal=handle
            response=handle.get_result_async()
            while not response.done():
                if self.cancel_event.is_set():
                    handle.cancel_goal_async()
                    raise RuntimeError('已请求取消运动，请确认机器人停止')
                if time.monotonic()>deadline:
                    handle.cancel_goal_async()
                    raise TimeoutError('机械臂动作超时，已请求机器人取消')
                rclpy.spin_once(node,timeout_sec=.05)
            result=response.result().result
            if int(result.error_code.val)!=1:
                raise RuntimeError(f'机器人运动规划或执行失败，MoveIt 错误码 {result.error_code.val}')
            return {'success':True,'moveit_error':int(result.error_code.val)}
        finally:
            self._goal=None
            client.destroy()
            node.destroy_node()
            self._node=None
