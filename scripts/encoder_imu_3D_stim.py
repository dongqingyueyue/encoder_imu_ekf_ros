#!/usr/bin/env python
# HJ: 2/11/20
# This program performs dead reckoning using the wheel encoders only

import time
import serial
import rospy
import struct
import math
from std_msgs.msg import Int32MultiArray
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Point, Pose, Quaternion, Twist, Vector3
from sensor_msgs.msg import Imu
import tf

# state for 3D robot (x,y,z,quat)
x = 0
y = 0
z = 0

# record previous state 
ticks_l_prev = 0
tickr_r_prev = 0
first_time_encoder = True
quat = []

# previous covariance
# update orientation here. use RK3
def quat_callback(data):
	global quat
	quat = [data.x, data.y,data.z, data.w]

def rotate(q1, v):
	if (sum(v) == 0.0):
		return [0,0,0]
	q2 = list(v)
	q2.append(0.0)
	q3 = tf.transformations.quaternion_multiply(
		tf.transformations.quaternion_multiply(q1, q2), 
		tf.transformations.quaternion_conjugate(q1))
	return tf.transformations.quaternion_multiply(
		tf.transformations.quaternion_multiply(q1, q2), 
		tf.transformations.quaternion_conjugate(q1)
	)[:3]

def callbackTicks(data):
	global x, y, z, quat, ticks_l_prev, ticks_r_prev, first_time_encoder

	if (len(quat) == 0):
		return

	if (first_time_encoder):
		ticks_l_prev = data.data[0]
		ticks_r_prev = data.data[1]
		first_time_encoder = False		
		return
		
	# base width (m)
	L = 0.6096
	R = 0.127

	# ticks/m... 1316 ticks per revolution	
	ticks_per_m = 1316/(math.pi*2*R)

	# Distance moved by each wheel
	ticks_l_curr = data.data[0]
	ticks_r_curr = data.data[1]

	# Compute distance moved by each wheel	
	Dl = (ticks_l_curr-ticks_l_prev)/ticks_per_m
	Dr = (ticks_r_curr-ticks_r_prev)/ticks_per_m
	Dc = (Dl+Dr)/2
	
	# update states
	d_pos_local = [Dc, 0.0, 0.0]
	d_pos_global = rotate(quat, d_pos_local)

	x = x + d_pos_global[0]
	y = y + d_pos_global[1]
	z = z + d_pos_global[2]

	# update previous tick count
	ticks_l_prev = ticks_l_curr
	ticks_r_prev = ticks_r_curr
		
	# odometry publisher
	odom_pub = rospy.Publisher('odom', Odometry, queue_size=10)
	odom = Odometry()

	# header
	odom.header.seq = seq
	odom.header.stamp = rospy.Time.now()
	odom.header.frame_id = "odom"

	# pose
	# quaternion created from yaw, pitch, roll. the 'szyx' means rotation applied to moving frame in order z y x (yaw, pitch, roll)
	odom_quat = tf.transformations.quaternion_from_euler(psi, theta, phi, 'rzyx')
	odom.pose.pose = Pose(Point(x, y, z), Quaternion(*odom_quat))
	odom_pub.publish(odom)

	# publish tf
	br = tf.TransformBroadcaster()
	br.sendTransform((x, y, z),
					 quat,
					 rospy.Time.now(),
					 "/base_footprint",
					 "/odom")

def main():
	# start node
	rospy.init_node('dead_reckoning', anonymous=True)

	# subscribe to encoder
	rospy.Subscriber("wheels", Int32MultiArray, callbackTicks)

	# subscribe to IMU
	rospy.Subscriber("/quat", Quaternion, quat_callback)

	# spin() simply keeps python from exiting until this node is stopped
	rospy.spin()

if __name__ == '__main__':
	main()
