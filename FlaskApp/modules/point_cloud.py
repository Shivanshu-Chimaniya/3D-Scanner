# modules/point_cloud.py
import numpy as np
import os
from math import radians, cos, sin, tan
import cv2

def convert_to_3d(points_2d, angle, image_width, image_height, img_num, cylinder_radius=1000):
    """Convert 2D image points to 3D coordinates"""
    if len(points_2d) == 0:
        return np.array([])
    
    # Convert angles to radians
    theta = radians(30)
    theta2 = radians(angle)
    
    # Calculate image midpoint
    midpoint_x = image_width / 2
    
    # Initialize 3D points array
    points_3d = []
    
    for x, y in points_2d:
        # Calculate distance from center
        r = midpoint_x - x  # Radius from center (positive means left of center)
        
        # Calculate Z using triangulation based on laser angle
        z = r / tan(theta)
        
        # Normalize Y coordinate
        y_3d = (image_height - y) / image_height
        
        # Apply rotation to convert to final 3D coordinates
        x_3d = r * cos(theta2) - z * sin(theta2)
        z_3d = r * sin(theta2) + z * cos(theta2)
        
        # Scale coordinates to reasonable values
        scale = cylinder_radius / image_width
        x_3d *= scale
        z_3d *= scale
        y_3d *= cylinder_radius*1.35
        
        points_3d.append([x_3d, y_3d, z_3d])
    
    return np.array(points_3d)

def save_ply(points, output_file):
    """Save point cloud as PLY file"""
    with open(output_file, 'w') as f:
        # Write header
        f.write("ply\n")
        f.write("format ascii 1.0\n")
        f.write(f"element vertex {len(points)}\n")
        f.write("property float x\n")
        f.write("property float y\n")
        f.write("property float z\n")
        f.write("end_header\n")
        
        # Write vertices
        for x, y, z in points:
            f.write(f"{x} {y} {z}\n")
    
    return f"Saved {len(points)} points to {output_file}"