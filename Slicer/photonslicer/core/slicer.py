# Core slicer package

import trimesh
import trimesh.creation
import math
import numpy as np
from shapely.geometry import LineString, MultiLineString, Point
from shapely.geometry.polygon import Polygon
from shapely.ops import nearest_points
import turtle
import pyclipper
from anytree import Node as TreeNode
from anytree import RenderTree, LevelOrderIter, PreOrderIter
#import matplotlib
from random import randint #temp, for debugging


def model_to_layer_paths(model_filepath, layer_height):

    # Load the mesh using trimesh
    mesh = trimesh.load_mesh(model_filepath)
    #mesh.apply_scale(3)

    # Config settings
    contour_offset = 7
    turtle.pensize(1)
    turtle.speed(4)

    # -Slicing process-:

    # Generate each of the layers
    layers = slice_mesh_into_layers(mesh, layer_height)

    # Convert each layer to a path
    layer_paths = []
    for layer in layers:
        contours = _generate_offset_contours(layer, contour_offset)
        contour_tree = _calculate_contour_spanning_tree(contours, contour_offset)
        grouped_contour_tree = _convert_to_grouped_contour_tree(contour_tree)
        connected_path = _connect_parents_to_children(grouped_contour_tree)

        layer_paths.append(connected_path)#layer_paths.append(_legacy_slice_to_path(layer))


    return layer_paths


def slice_mesh_into_layers(mesh, layer_height):

    # Translate the mesh so that the bottom middle of the bounding box is centered at the origin

    # First center mesh
    mesh.vertices -= mesh.center_mass

    # Then raise the mesh so that the bottom of the bounding box is at z=0
    min_point = min(mesh.bounding_box.vertices, key=lambda t: t[2])
    translation_vector = (0, 0, -min_point[2])
    mesh.apply_translation(translation_vector)

    # Calculate how many slices need to be taken
    mesh_height = mesh.bounding_box.extents[2]
    layer_count = math.ceil(mesh_height/layer_height)

    # Take slices from regular points in the model
    slices = []
    center = mesh.centroid
    for i in np.linspace(0, mesh_height, layer_count):

        # Take layer slice
        layer_slice = mesh.section(plane_origin=(center[0], center[1], i),
                                   plane_normal=[0, 0, 1])

        # Check if this intersection exists
        if layer_slice:
            slices.append(layer_slice)

    return slices


def _legacy_slice_to_path(layer_slice):

    # Make sure that this layer is 2 dimensional
    prepped_slice, _ = layer_slice.to_planar()  # 2nd tuple component is map to convert 2d path back to 3d path

    # Convert the slice into a an array of path sections, with each section being an array of vertices
    path_sections = []
    for section in prepped_slice.polygons_full:

        # Add this polygons exterior
        path_sections.append(list(section.exterior.coords))

        # Add this polygons interior sections
        for interior in section.interiors:
            path_sections.append(list(interior.coords))

        # Calculate infill
        laser_dot_diameter = 4
        minx, miny, maxx, maxy = section.exterior.bounds
        infill_lines_count = math.ceil((maxy - miny) / laser_dot_diameter)

        # Start at top of polygon and scan down to bottom
        for j in np.linspace(miny, maxy, infill_lines_count):
            #break
            infill_line = LineString([(minx - 8, j), (maxx + 8, j)])
            infill_line_sections = section.intersection(infill_line)

            # Check whether more than one intersection occurred
            if type(infill_line_sections) is LineString:
                path_sections.append(list(infill_line_sections.coords))
            elif type(infill_line_sections) is MultiLineString:
                for line in infill_line_sections:
                    path_sections.append(list(line.coords))

    return path_sections


def _generate_offset_contours(layer_slice, contour_offset):

    clipper_scale_factor = 10000

    # Make sure that this layer is 2 dimensional
    prepped_slice, _ = layer_slice.to_planar()  # 2nd tuple component is map to convert 2d path back to 3d path

    # Prepare the polygon for input to clipper
    for section in prepped_slice.polygons_full:

        # Add this polygons exterior
        outline = list(section.exterior.coords)

        source_polygon = pyclipper.scale_to_clipper(outline, clipper_scale_factor)
        clipper_object = pyclipper.PyclipperOffset()
        clipper_object.AddPath(source_polygon, pyclipper.JT_MITER, pyclipper.ET_CLOSEDPOLYGON)  # JT_MITER #JT_ROUND

        # Add this polygons interior sections
        for interior in section.interiors:
            hole_polygon = pyclipper.scale_to_clipper(list(interior.coords), clipper_scale_factor)
            clipper_object.AddPath(hole_polygon, pyclipper.JT_MITER, pyclipper.ET_CLOSEDPOLYGON)

    # Offset each contour
    contours = []
    hole_contours = []
    for i in range(200):
        contour_layer = []
        hole_contour_layer = []
        solution = clipper_object.Execute(-(contour_offset*clipper_scale_factor)*i)

        # Check whether any contours were returned
        if len(solution) == 0:
            break

        # Convert contour points back to floats
        contour_sets = pyclipper.scale_from_clipper(solution, clipper_scale_factor)

        # Iterate over each of the contour groups
        for contour in contour_sets:
            # Add first point to end of path to close the loop
            contour.append(contour[0])

            # Simplify contour
            contour = _simplify_path(contour)

            # Check if this is a hole:
            not_a_hole = pyclipper.Orientation(contour)
            if not_a_hole:
                # Add generated contour to list of contours
                contour_layer.append(contour)
            else:
                # Reverse direction of this contour
                contour.reverse()

                # Add generated contour to list of holes
                hole_contour_layer.append(contour)

        # Add this layer of contours to the contours list
        contours.append(contour_layer)
        hole_contours.append(hole_contour_layer)

    # In reverse order add holes onto to contour layers
    #print(contours)
    #print(hole_contours)
    for hole in reversed(hole_contours):
        contours.append(hole)
    #print(contours)

    # Temporary debugging
    #turtle.tracer(False)
    turtle.colormode(255)
    #for i in range(len(contours)):
    #    turtle.pencolor((i*30, i*30, 0))
    #    print(contours[5])
    #    _debug_draw_paths(contours[i])
    #turtle.exitonclick()

    # Return the set of contours
    return contours


# Returns a spanning tree representing the structure of the shapes contours, whereby consecutive contours are grouped
# under the same branch
def _calculate_contour_spanning_tree(contour_sets, contour_offset):

    root = TreeNode(None)
    parent_nodes = [root]
    next_parent_nodes = []

    # Iterate over each of the contour sets, from the perimeter contours through to the center contours
    for contour_set in contour_sets:

        for contour in contour_set:

            # First get a normal vector from arbitrary point on child
            vector = np.subtract(contour[1], contour[0])
            theta = math.pi / 2
            cos = math.cos(theta)
            sin = math.sin(theta)
            normal = [vector[0] * cos - vector[1] * sin,
                      vector[0] * sin + vector[1] * cos]
            normal = np.divide(normal, np.linalg.norm(normal))
            normal = np.multiply(normal, contour_offset * 2.1)

            starting_point = np.subtract(np.multiply(np.add(contour[0], contour[1]), 0.5), np.multiply(normal, 0.5))
            end_point = np.add(starting_point, normal)
            normal_line = LineString([starting_point, end_point])

            # temp debug
            #turtle.tracer(True)
            #turtle.pencolor((255, 0, 0))
            #_debug_draw_path([starting_point, end_point])

            # For each contour at this level determine which of the previous contours it is nested within
            parent_found = False
            for node in parent_nodes:

                # Check for intersection against the parent contour specified by the node
                polygon = Polygon(node.name)
                if normal_line.intersects(polygon) or node.name is None:

                    # Once the parent contour is found, add this child contour as a node under the parent
                    new_node = TreeNode(contour, parent=node)
                    next_parent_nodes.append(new_node)
                    parent_found = True
                    break

            if not parent_found:  # this will happen when a hole contour is encountered

                # Reverse level order iterate over parents
                reverse_level_order_nodes = reversed([node for node in LevelOrderIter(root)])
                for node in reverse_level_order_nodes:

                    # Check for intersection against the parent contour specified by the node
                    polygon = Polygon(node.name)
                    if normal_line.intersects(polygon):

                        # Once the parent contour is found, add this child contour as a node under the parent
                        new_node = TreeNode(contour, parent=node)
                        next_parent_nodes.append(new_node)
                        break

        parent_nodes = next_parent_nodes
        next_parent_nodes = []

    # temp debug
    #print(RenderTree(root))
    #turtle.tracer(True)
    #[_debug_draw_path(node.name) for node in PreOrderIter(root) if not node.name is None]
    #turtle.exitonclick()

    return root


# Recursive function to remove consecutive contour nodes, instead storing them as lists on each node, with tree
# splits only happening once a new contour group is encountered
def _convert_to_grouped_contour_tree(contour_spanning_tree):

    node = contour_spanning_tree
    contour_group = []

    while len(node.children) == 1:
        # Add this node to the group, ignoring the root node
        if node.name is not None:
            contour_group.append(node.name)

        # Update node variable ahead of next iteration
        node = node.children[0]

    # Ignore root node
    if node.name is not None:
        contour_group.append(node.name)
    new_node = TreeNode(contour_group)

    for child in node.children:
        returned_node = _convert_to_grouped_contour_tree(child)
        returned_node.parent = new_node

    return new_node


def _connect_parents_to_children(grouped_contour_tree):

    # Initial variable declarations
    continuous_path = grouped_contour_tree.name[0:-1]
    parent = grouped_contour_tree.name
    parent_line = LineString(parent[-1])
    children = grouped_contour_tree.children

    # Find the closest point between each child and the parent
    connections = []
    for child in children:
        child_line = LineString(child.name[0])
        p1, p2 = nearest_points(parent_line, child_line)
        connections.append((p1, p2, child))

    # Order connections by distance along parent
    connections.sort(key=lambda connect: parent_line.project(connect[0]))

    # Split the parent at each connection point and re-align the child
    for connection in connections:
        p_point, c_point, child = connection

        # Split the parent
        path1, path2 = _split_line_at_point(parent_line, p_point)
        parent_line = LineString(path2)

        # Re-align child to the connection point
        new_child = _align_contour_group_to_point(child.name, (c_point.x, c_point.y))

        # Recursively connect children's children
        child.name = new_child
        new_child = _connect_parents_to_children(child)

        # Add this new path to parent
        continuous_path.append(path1)
        continuous_path.extend(new_child)

    # Add final path segment
    continuous_path.append(list(parent_line.coords))

    return continuous_path


def _align_contour_group_to_point(contour_group, point):

    start_point = Point(point)
    new_group = []

    for contour in contour_group:
        # Re-order this contour so that it starts in line with the specified point
        contour_line = LineString(contour)
        closest_point_distance = contour_line.project(start_point)
        closest_point = contour_line.interpolate(closest_point_distance)

        # Create new contour
        new_contour = _reorder_with_start_distance(contour_line, closest_point_distance)
        new_contour_points = list(new_contour.coords)
        new_contour_points.insert(0, [closest_point.x, closest_point.y])
        new_contour_points[-1] = new_contour_points[0]

        # Update start point for next contour
        start_point = Point(new_contour_points[0])

        # Add this new contour to the new group
        new_group.append(new_contour_points)

        #temp debug
        #_debug_draw_paths(_debug_make_cross_at_point((closest_point.x, closest_point.y)))
        #_debug_draw_path(new_contour_points)

    return new_group


def _spiralise_contour_group(contour_group):

    # Choose a random start point - to be later replaced by optimal start point selection
    start_point = Point(contour_group[0][0])#randint(0, len(contour_group[0])-1)])
    linked_contour = []

    for contour in contour_group:
        # Find the closest point on the contour to this start point
        contour_line = LineString(contour)
        closest_point_distance = contour_line.project(start_point)
        closest_point = contour_line.interpolate(closest_point_distance)
        end_point = contour_line.interpolate(closest_point_distance - 8)

        # Create new contour
        new_contour = _reorder_with_start_distance(contour_line, closest_point_distance)
        new_contour = _cut_after_distance(new_contour, - 8)
        new_contour_points = list(new_contour.coords)
        new_contour_points.insert(0, [closest_point.x, closest_point.y])
        new_contour_points[-1] = [end_point.x, end_point.y]
        linked_contour.extend(new_contour_points)

        # Update starting point for next contour
        start_point = closest_point
        #_debug_draw_paths(_debug_make_cross_at_point((closest_point.x, closest_point.y)))
        #_debug_draw_path(new_contour.coords)

    #turtle.pencolor((randint(0, 255), randint(0, 255), randint(0, 255)))
    _debug_draw_path(linked_contour)


# Reorders the points on a line so that the start of the line is offset by the specified distance
def _reorder_with_start_distance(line, distance):

    distance = distance % line.length

    coords = list(line.coords)
    for i, p in enumerate(coords):
        pd = line.project(Point(p))
        if pd >= distance:
            return LineString(coords[i:-1] + coords[:i] + [coords[i]])

    return LineString(line)


def _cut_after_distance(line, distance):
    distance = distance % line.length

    coords = list(line.coords)
    for i, p in enumerate(coords):
        pd = line.project(Point(p))

        if pd >= distance:
            return LineString(coords[:i])

    return LineString(line)


def _split_line_at_point(line, point):

    distance = line.project(point)

    distance = distance % line.length

    # Cuts a line in two at a distance from its starting point
    coords = list(line.coords)
    for i, p in enumerate(coords):
        pd = line.project(Point(p))
        if pd == distance:
            return [
                coords[:i+1],
                coords[i:]]
        if pd > distance:
            cp = line.interpolate(distance)
            return [
                coords[:i] + [(cp.x, cp.y)],
                [(cp.x, cp.y)] + coords[i:]]


def _flatten_paths(paths):

    flattened_paths = []

    for path in paths:
        flattened_paths.extend(path)

    return flattened_paths


# Function to take in a contour spanning tree and return an ordered array of groups whereby each group is
# next to its nearest neighbour. The proximity between 2 contour groups is defined by 4 distances
# 1) The distance from the closest point of group 1's center contour to the closest point of group 2's outer contour
# 2) The distance from the closest point of group 1's center contour to the closest point of group 2's center contour
# 3) The distance from the closest point of group 1's outer contour to the closest point of group 2's outer contour
# 4) The distance from the closest point of group 1's outer contour to the closest point of group 2's center contour
# This proximity is subject to the following constraints:
# 1) Each group must have at most 1 connection to its outer contour and at most 1 connection to its center contour
# 2) Each group must have at least 1 connection to its outer contour and at least 1 connection to its center contour
#    with the exception of 1 outer and 1 center contour which will be the start and end points for the layer
#    (the total number of outer connections = n-1 and total number of inner connections = n-1, where n is the number
#    of contour groups)
def _arrange_contour_groups_by_proximity(contour_spanning_tree):

    # First step is to separate tree into separate groups
    all_groups = []
    current_group = []
    for node in PreOrderIter(contour_spanning_tree):

        # Ignore root node
        if not node.name is None:

            # Add this contour to the current group
            current_group.append(node.name)

            # Check if this node has more than 1 child or is the last node on a branch
            if len(node.children) > 1 or node.is_leaf:
                # Create a new group and add this last group to the big list of all groups
                all_groups.append(current_group)
                current_group = []

    # temp debug
    print(RenderTree(contour_spanning_tree))
    turtle.tracer(True)
    for group in all_groups:
        print(group)
        turtle.pencolor((randint(0, 255), randint(0, 255), randint(0, 255)))
        _debug_draw_paths(group)
    turtle.exitonclick()

    return all_groups


def _debug_make_cross_at_point(point):
    x, y = point

    return [[[x-5, y], [x+5, y]], [[x, y-5], [x, y+5]]]


def _debug_draw_paths(paths, shift_colour):

    if shift_colour:
        val = 0

    for path in paths:
        if shift_colour:
            val = _debug_draw_path(path, val)
        else:
            _debug_draw_path(path)


def _debug_draw_path(path, shift_colour_val):

    #turtle.colormode(255)
    #turtle.pencolor((0, 0, 0))

    points = iter(path)

    x, y = next(points)
    turtle.penup()
    turtle.setpos(x, y)
    turtle.pendown()

    i = shift_colour_val
    for x, y in path:
        if shift_colour_val is not None:
            if i > 255*3:
                r = min(max(255*4-i, 0), 255)
            else:
                r = min(i, 255)
            if i > 255*2:
                g = min(max(255*3-i, 0), 255)
            else:
                g = min(max(i-255, 0), 255)
            b = min(max(i - 255*2, 0), 255)
            r = math.floor(r)
            g = math.floor(g)
            b = math.floor(b)
            turtle.pencolor((r, g, b))
        turtle.setpos(x, y)
        i = i + 1
    return i


# Takes in a set of paths and removes points that lie on the same line
def _simplify_path(path):

    new_path = []
    point_iter = iter(path)
    prev_point1 = next(point_iter)
    prev_point2 = next(point_iter)

    # Append initial 2 points to end in order to complete loop when iterating in groups of 3
    path.append(path[1])
    path.append(path[2])

    # Iterate over points
    for point in point_iter:

        # Calculate d value to find winding order
        x, y = point
        x1, y1 = prev_point1
        x2, y2 = prev_point2
        d_val = (x-x1)*(y2-y1)-(y-y1)*(x2-x1)
        d_mag = (x-x1)*(y2-y1)+(y-y1)*(x2-x1)
        scaled_d_val = 0 if d_mag == 0 else d_val/d_mag
        #print(scaled_d_val)

        # If d is approximately zero then the point lies on the same tangent as the previous line segment
        if abs(scaled_d_val) > 0.01:  # arbitrary small value
            new_path.append(prev_point2)  # only keep points that have d > 0

        # Shift points
        prev_point1 = prev_point2
        prev_point2 = point

    # Add last point if needed:
    if not new_path[-1] == new_path[0]:
        new_path.append(new_path[0])

    return new_path


# temporary function that could potentially be useful
def _identify_convex_points(path):

    # Make sure contour is wound in a clockwise order
    if not pyclipper.Orientation(path):
        path.reverse()

    point_iter = iter(path)
    prev_point1 = next(point_iter)
    prev_point2 = next(point_iter)
    for point in point_iter:

        # Calculate d value to find winding order
        x, y = point
        x1, y1 = prev_point1
        x2, y2 = prev_point2
        d_val = (x-x1)*(y2-y1)-(y-y1)*(x2-x1)

        # If d is zero then the point lies on the same tangent as the previous line segment

        # If d is less than zero then the point is concave
        if d_val < 0:
            turtle.penup()
            turtle.setpos(x2-5, y2)
            turtle.pendown()
            turtle.setpos(x2+5, y2)
            turtle.penup()
            turtle.setpos(x2, y2-5)
            turtle.pendown()
            turtle.setpos(x2, y2+5)

        # Shift points
        prev_point1 = prev_point2
        prev_point2 = point


#def

#filepath = 'C:/Users/Alistair/Documents/Dark Materials/SLA1/Slicer/models/oscar.stl';
#mesh = trimesh.load_mesh(filepath);
#watertight = mesh.is_watertight;
#print("Mesh: {} is watertight? {}".format(filepath, watertight));
#print("The mesh has the euler number: {}".format(mesh.euler_number));
#viewer = mesh.show(callback=called)

#def called(scene):
#    viewer.scene = mesh.scene();


#print(mesh.centroid);
#slice = mesh.section(plane_origin=mesh.centroid,
#                     plane_normal=[0, 0, 1])
# viewer = slice.show(callback=called)

#for i in range(1, 100):
#    center = mesh.centroid;
#    center = (center[0], center[1], i);
#    slice = mesh.section(plane_origin=center,
#                         plane_normal=[0, 0, 1])
#    viewer = slice.show()
