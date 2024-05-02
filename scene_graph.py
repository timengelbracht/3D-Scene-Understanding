import numpy as np
from scipy.spatial import cKDTree
import open3d as o3d


class ObjectNode:
    def __init__(self, object_id, centroid, color, sem_label, points):
        self.object_id = object_id
        self.centroid = centroid
        self.points = points
        self.sem_label = sem_label
        self.color = color
        self.neighbors = []

class SceneGraph:
    def __init__(self):
        self.index = 0
        self.nodes = []
        self.tree = None

    def add_node(self, centroid, color, sem_label, points):
        self.nodes.append(ObjectNode(self.index, centroid, color, sem_label, points))
        self.index += 1
    
    def read_ply(self, file_path="point_lifted_mesh_ascii.ply", label_file='labels.txt'):
        # TODO: check whether this works
        pcd = o3d.io.read_point_cloud(file_path)
        with open(label_file, 'r') as f:
            labels = [int(label.strip()) for label in f.readlines()]
        return np.array(pcd.points), np.array(pcd.colors), np.array(labels)

    def build(self, file_path="point_lifted_mesh_ascii.ply", label_file='labels.txt', k=2):
        points, colors, labels = self.read_ply(file_path, label_file)

        unique_labels = np.unique(labels, axis=0)
        for label in unique_labels:
            indices = np.where(labels == label)
            mean_point = np.mean(points[indices], axis=0)
            color = np.array(colors[indices])
            self.add_node(mean_point, color[0], label, points[indices])

        sorted_nodes = sorted(self.nodes, key=lambda node: node.object_id)

        # Get centroids of sorted nodes
        centroids = np.array([node.centroid for node in sorted_nodes])
        # centroids = np.array([node.centroid for node in self.nodes])
        self.tree = cKDTree(centroids)

        for node in self.nodes:
            _, indices = self.tree.query(node.centroid, k=k+1)
            for idx in indices[1:]:
                neighbor = self.nodes[idx]
                node.neighbors.append(neighbor)
    
    def get_distance(self, point):
        _, idx = self.tree.query(point)
        node = self.nodes[idx]
        return np.linalg.norm(point - node.centroid)
    
    def nearest_neighbor_bbox(self, points):
        distances = np.array([self.get_distance(point) for point in points])
        index = np.argmin(distances)
        _, idx = self.tree.query(points[index])
        node = self.nodes[idx]
        bbox = o3d.geometry.AxisAlignedBoundingBox.create_from_points(o3d.utility.Vector3dVector(node.points))
        bbox.color = [1,0,0]
        return bbox


    
    def visualize(self, centroids=True, connections=True, scale=0.0, exlcude=[], threshold=0):
        if threshold:
            nodes = [node for node in self.nodes if (node.object_id not in exlcude) and (node.points.shape[0] < threshold )]
        else:
            nodes = [node for node in self.nodes if node.object_id not in exlcude]
            
        geometries = []
        for node in nodes:
            pcd = o3d.geometry.PointCloud()
            pcd_points = node.points + scale*node.centroid
            pcd.points = o3d.utility.Vector3dVector(pcd_points)
            pcd_color = np.array(node.color, dtype=np.float64)
            pcd.paint_uniform_color(pcd_color)
            geometries.append(pcd)
        
        if centroids:        
            centroid_pcd = o3d.geometry.PointCloud()
            centroids_xyz = np.array([node.centroid + scale*node.centroid for node in nodes])
            centroids_colors = np.array([node.color for node in nodes], dtype=np.float64) / 255.0
            centroid_pcd.points = o3d.utility.Vector3dVector(centroids_xyz)
            centroid_pcd.colors = o3d.utility.Vector3dVector(centroids_colors)
            geometries.append(centroid_pcd)
        
        if connections:
            # Add cluster centroids as points to the original point cloud
            for node in nodes:
                for neighbor in node.neighbors:
                    line = o3d.geometry.LineSet()
                    line.points = o3d.utility.Vector3dVector([node.centroid + scale*node.centroid, neighbor.centroid + scale*neighbor.centroid])
                    lines = [[0, 1]]
                    line.lines = o3d.utility.Vector2iVector(lines)
                    geometries.append(line)
        
        o3d.visualization.draw_geometries(geometries)



