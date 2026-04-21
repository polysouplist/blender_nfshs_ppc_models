#-*- coding:utf-8 -*-

# Blender Need for Speed High Stakes Pocket PC importer Add-on
# Add-on developed by PolySoupList


bl_info = {
	"name": "Import Need for Speed High Stakes Pocket PC models format (.z3d, .trk)",
	"description": "Import meshes files from Need for Speed High Stakes Pocket PC",
	"author": "PolySoupList",
	"version": (1, 0, 0),
	"blender": (3, 6, 23),
	"location": "File > Import > Need for Speed High Stakes Pocket PC (.z3d, .trk)",
	"warning": "",
	"wiki_url": "",
	"tracker_url": "",
	"support": "COMMUNITY",
	"category": "Import-Export"}


import bpy
from bpy.types import (
	Operator,
	OperatorFileListElement
)
from bpy.props import (
	StringProperty,
	BoolProperty,
	CollectionProperty
)
from bpy_extras.io_utils import (
	ImportHelper,
	orientation_helper,
	axis_conversion,
)
import bmesh
import binascii
import math
from mathutils import Matrix, Quaternion
import os
import time
import struct


def main(context, file_path, clear_scene, global_matrix):
	if bpy.ops.object.mode_set.poll():
		bpy.ops.object.mode_set(mode='OBJECT')
	
	if clear_scene == True:
		print("Clearing scene...")
		clearScene(context)
	
	status = import_nfshs_ppc_models(context, file_path, clear_scene, global_matrix)
	
	return status


def import_nfshs_ppc_models(context, file_path, clear_scene, m):
	start_time = time.time()
	
	main_collection_name = os.path.basename(file_path)
	main_collection = bpy.data.collections.new(main_collection_name)
	bpy.context.scene.collection.children.link(main_collection)
	
	print("Importing file %s" % os.path.basename(file_path))
	
	## PARSING FILES
	print("Parsing file...")
	parsing_time = time.time()
	
	file_extension = file_path[-4:].lower()
	
	if file_extension == ".z3d":
		objects = read_z3d(file_path)
	elif file_extension == ".trk":
		trk = read_trk(file_path)
	else:
		print("ERROR: Unknown file extension %s." % (file_extension))
		return {'CANCELLED'}
	
	elapsed_time = time.time() - parsing_time
	print("... %.4fs" % elapsed_time)
	
	## IMPORTING TO SCENE
	print("Importing data to scene...")
	importing_time = time.time()
	
	if file_extension == ".z3d":
		for i in range(0, len(objects)):
			name, vertices, uvs, polygons, texture_name = objects[i]
			if len(vertices) > 0:
				obj = create_object(name, vertices, uvs, polygons, texture_name, False, False)
				obj["object_index"] = i
				main_collection.objects.link(obj)
				obj.matrix_world = m
	
	elif file_extension == ".trk":
		cameras_collection = bpy.data.collections.new("Cameras")
		main_collection.children.link(cameras_collection)
		objects_collection = bpy.data.collections.new("Objects")
		main_collection.children.link(objects_collection)
		walls_collection = bpy.data.collections.new("Walls")
		main_collection.children.link(walls_collection)
		road_collection = bpy.data.collections.new("Road")
		main_collection.children.link(road_collection)
		nodes_collection = bpy.data.collections.new("Nodes")
		road_collection.children.link(nodes_collection)
		sprites_collection = bpy.data.collections.new("Sprites")
		main_collection.children.link(sprites_collection)
		navmesh_collection = bpy.data.collections.new("Navmesh")
		main_collection.children.link(navmesh_collection)
		
		cameras, spritelist, objects, walls, road, navmesh = trk
		
		for i in range(0, len(cameras)):
			nearest_quad, camera_pos = cameras[i]
			camera_pos = scale_position(camera_pos)
			
			camera = bpy.data.objects.new("Camera", None)
			camera["nearest_quad"] = nearest_quad
			camera["camera_index"] = i
			cameras_collection.objects.link(camera)
			camera.matrix_world = m @ Matrix.Translation(camera_pos)
		
		walls_indices = {}
		objects_nearest_quads = {}
		quads = road[2]
		
		for i in range(0, len(quads)):
			temp = quads[i][3]
			temp2 = quads[i][4]
			temp3 = quads[i][5]
			
			for j in range(0, len(temp)):
				wall_index = temp[j][0]
				wall_polygon = temp[j][1]
				
				if wall_index not in walls_indices:
					walls_indices[wall_index] = []
				walls_indices[wall_index].append([i, wall_polygon])
			
			for j in range(0, len(temp2)):
				rendered_object = temp2[j]
				
				if rendered_object not in objects_nearest_quads:
					objects_nearest_quads[rendered_object] = []
				objects_nearest_quads[rendered_object].append(i)
		
		for i in range(0, len(objects)):
			vertices, uvs, polygons, texture_name = objects[i]
			if len(vertices) >= 1:
				object = create_object("Object", vertices, uvs, polygons, texture_name, True, False)
				object["object_index"] = i
				if i in objects_nearest_quads:
					object["nearest_quad"] = objects_nearest_quads[i]
				objects_collection.objects.link(object)
				object.matrix_world = m
		
		for i in range(0, len(walls)):
			vertices, uvs, texture_name = walls[i]
			
			if len(vertices) >= 1:
				wall = create_object("Wall", vertices, uvs, walls_indices[i], texture_name, True, True)
				wall["wall_index"] = i
				walls_collection.objects.link(wall)
				wall.matrix_world = m
		
		vertices, uvs, polygons, texture_name = trk[4]
		unpacked_polygons = []
		for i in range(0, len(polygons)):
			unpacked_polygon = polygons[i][0]
			unpacked_locator = polygons[i][1]
			unpacked_locator = scale_position(unpacked_locator)
			locator_quaternion = polygons[i][2]
			sprite_positions = polygons[i][5]
			
			unpacked_polygons.append(unpacked_polygon)
			locator = bpy.data.objects.new("Node", None)
			locator.empty_display_type = 'SINGLE_ARROW'
			nodes_collection.objects.link(locator)
			locator.matrix_world = m @ Matrix.Translation(unpacked_locator)
			locator.rotation_mode = 'QUATERNION'
			locator.rotation_quaternion = [locator_quaternion[2], locator_quaternion[0], locator_quaternion[1], locator_quaternion[3]]
			
			sprites_collection["spritelist"] = trk[1]		
			for j in range(0, len(sprite_positions)):
				sprite_pos, sprite_index = sprite_positions[j]
				sprite_pos = scale_position(sprite_pos)
				
				sprite_empty = bpy.data.objects.new(trk[1][sprite_index], None)
				sprite_empty["sprite_index"] = sprite_index
				sprite_empty["nearest_quad"] = i
				
				sprites_collection.objects.link(sprite_empty)
				sprite_empty.matrix_world = m @ Matrix.Translation(sprite_pos)
		
		if len(vertices) > 0:
			obj = create_object("Road", vertices, uvs, unpacked_polygons, texture_name, True, False)
			road_collection.objects.link(obj)
			obj.matrix_world = m
		
		navmesh = trk[5]
		if len(navmesh) > 0:
			mesh = bpy.data.meshes.new("Navmesh")
			obj = bpy.data.objects.new("Navmesh", mesh)
			mesh.from_pydata(navmesh, [], [])
			navmesh_collection.objects.link(obj)
			obj.matrix_world = m
	
	elapsed_time = time.time() - importing_time
	print("... %.4fs" % elapsed_time)
	
	## Adjusting scene
	for window in bpy.context.window_manager.windows:
		for area in window.screen.areas:
			if area.type == 'VIEW_3D':
				for space in area.spaces:
					if space.type == 'VIEW_3D':
						space.shading.type = 'MATERIAL'
				region = next(region for region in area.regions if region.type == 'WINDOW')
				override = bpy.context.copy()
				override['area'] = area
				override['region'] = region
				bpy.ops.view3d.view_all(override, use_all_regions=False, center=False)
	
	print("Finished")
	elapsed_time = time.time() - start_time
	print("Elapsed time: %.4fs" % elapsed_time)
	return {'FINISHED'}


def read_z3d(file_path):
	z3d = []
	
	with open(file_path, "rb") as f:
		header_size = struct.unpack('<I', f.read(0x4))[0]
		header = f.read(header_size)
		
		num_meshes = struct.unpack('<I', f.read(0x4))[0]
		
		for i in range(0, num_meshes):
			vertices = []
			uvs = []
			polygons = []
			
			has_uv = struct.unpack('<I', f.read(0x4))[0]
			unknown = struct.unpack('<I', f.read(0x4))[0]
			
			name_length = struct.unpack('<I', f.read(0x4))[0]
			name = f.read(name_length)
			name = str(name, 'ascii')
			f.read(0x1)
			
			num_vrtx = struct.unpack('<I', f.read(0x4))[0]
			num_plgn = struct.unpack('<I', f.read(0x4))[0]
			
			for j in range(0, num_vrtx):
				vertex = struct.unpack('<3f', f.read(0xC))
				vertices.append(vertex)
			
			if has_uv != 0:
				for j in range(0, num_vrtx):
					uv = struct.unpack('<2f', f.read(0x8))
					uvs.append(uv)
			
			for j in range(0, num_plgn):
				polygon = struct.unpack('<3H', f.read(0x6))
				polygons.append(polygon)
			
			texture_length = struct.unpack('<I', f.read(0x4))[0]
			texture_name = f.read(texture_length)
			f.read(0x1)
			
			z3d.append([name, vertices, uvs, polygons, texture_name])
	
	return z3d


def read_trk_walls(f):
	walls = {}
	
	num_walls = struct.unpack('<I', f.read(0x4))[0]
	
	for i in range (0, num_walls):
		vertices, uvs = read_trk_vertex_data(f)
		
		texture_length = struct.unpack('<I', f.read(0x4))[0]
		texture_name = f.read(texture_length)
		
		walls[i] = [vertices, uvs, texture_name]
	
	return walls


def read_trk_objects(f):
	objects = {}
	
	num_objects = struct.unpack('<I', f.read(0x4))[0]
	
	for i in range(0, num_objects):
		polygons = []
		
		vertices, uvs = read_trk_vertex_data(f)
		
		num_plgn = struct.unpack('<I', f.read(0x4))[0]
		
		for j in range(0, num_plgn):
			polygon = struct.unpack('<3H', f.read(0x6))
			polygons.append(polygon)
		
		texture_length = struct.unpack('<I', f.read(0x4))[0]
		texture_name = f.read(texture_length)
		
		objects[i] = [vertices, uvs, polygons, texture_name]
	
	return objects


def read_trk_vertex_data(f):
	vertices = []
	uvs = []
	
	num_vrtx = struct.unpack('<I', f.read(0x4))[0]
	
	for i in range(0, num_vrtx):
		vertex = struct.unpack('<3f', f.read(0xC))
		vertices.append(vertex)
	
	for i in range(0, num_vrtx):
		uv = struct.unpack('<2f', f.read(0x8))
		uvs.append(uv)
	
	vertex_data = [vertices, uvs]
	
	return vertex_data


def read_trk_spritelist(f):
	spritelist = []
	
	num_spritenames = struct.unpack('<I', f.read(0x4))[0]
	
	for i in range(0, num_spritenames):
		sprite_name_length = struct.unpack('<I', f.read(0x4))[0]
		sprite_name = f.read(sprite_name_length)
		sprite_name = str(sprite_name, 'ascii')
		
		spritelist.append(sprite_name)
	
	return spritelist


def read_trk_cameras(f):
	cameras = {}
	
	num_cameras = struct.unpack('<I', f.read(0x4))[0]
	
	for i in range(0, num_cameras):
		nearest_quad = struct.unpack('<I', f.read(0x4))[0]
		camera_pos = struct.unpack('<3f', f.read(0xC))
		cameras[i] = [nearest_quad, camera_pos]
	
	return cameras


def read_trk(file_path):
	
	with open(file_path, "rb") as f:
		
		cameras = read_trk_cameras(f)
		spritelist = read_trk_spritelist(f)
		objects = read_trk_objects(f)
		walls = read_trk_walls(f)
		
		quads = {}
		
		vertices, uvs = read_trk_vertex_data(f)
		
		num_quad = struct.unpack('<I', f.read(0x4))[0]
		
		for i in range(0, num_quad):
			walls_indices = []
			sprites = []
			
			quad_indices = struct.unpack('<4H', f.read(0x8))
			quad_center = struct.unpack('<3f', f.read(0xC))
			quad_quaternion = struct.unpack('<4f', f.read(0x10))
			
			num_plgn = struct.unpack('<I', f.read(0x4))[0]
			for j in range(0, num_plgn):
				wall_index = struct.unpack('<I', f.read(0x4))[0]
				wall_polygon = struct.unpack('<3H', f.read(0x6))
				
				walls_indices.append([wall_index, wall_polygon])
			
			num_unknown = struct.unpack('<I', f.read(0x4))[0]
			rendered_objects = []
			if num_unknown >= 1:
				#print("quad_index:", i) 
				#print("num_unknown:", num_unknown)
				
				for j in range (0, num_unknown):
					unknown = struct.unpack('<I', f.read(0x4))[0]
					rendered_objects.append(unknown)
					
					#print("unknown:", unknown)
			
			num_sprites = struct.unpack('<I', f.read(0x4))[0]
			for j in range(0, num_sprites):
				sprite_position = struct.unpack('<3f', f.read(0xC))
				sprite_index = struct.unpack('<I', f.read(0x4))[0]
				
				sprites.append([sprite_position, sprite_index])
				
			quads[i] = [quad_indices, quad_center, quad_quaternion, walls_indices, rendered_objects, sprites]
		
		texture_length = struct.unpack('<I', f.read(0x4))[0]
		texture_name = f.read(texture_length)
		
		road = [vertices, uvs, quads, texture_name]
		
		navmesh = []
		for i in range(0, (num_quad*2)):
			navmesh_vertex = struct.unpack('<3f', f.read(0xC))
			navmesh_vertex = scale_position(navmesh_vertex)
			navmesh.append(navmesh_vertex)
	
	trk = [cameras, spritelist, objects, walls, road, navmesh]
	
	return trk


def create_object(name, vertices, uvs, faces, texture_name, flipped_uv, additional_data):
	#==================================================================================================
	#Building Mesh
	#==================================================================================================
	me_ob = bpy.data.meshes.new(name)
	obj = bpy.data.objects.new(name, me_ob)
	
	#Get a BMesh representation
	bm = bmesh.new()
	
	#Creating new properties
	if additional_data == True:
		flag = (bm.faces.layers.int.get("flag") or bm.faces.layers.int.new('flag'))
	
	BMVert_dictionary = {}
	
	if uvs:
		has_uv = True
		uvName = "UVMap" #or UV1Map
		uv_layer = bm.loops.layers.uv.get(uvName) or bm.loops.layers.uv.new(uvName)
	else:
		has_uv = False
	
	for i, position in enumerate(vertices):
		position = scale_position(position)
		
		BMVert = bm.verts.new(position)
		BMVert.index = i
		BMVert_dictionary[i] = BMVert
	
	for i, face in enumerate(faces):
		if additional_data == True:
			nearest_quad = face[0]
			face = face[1]
		
		if len(face) == 4:
			face_vertices = [BMVert_dictionary[face[0]], BMVert_dictionary[face[2]], BMVert_dictionary[face[3]], BMVert_dictionary[face[1]]]
			if has_uv == True:
				face_uvs = [uvs[face[0]], uvs[face[2]], uvs[face[3]], uvs[face[1]]]
		else:
			face_vertices = [BMVert_dictionary[face[0]], BMVert_dictionary[face[2]], BMVert_dictionary[face[1]]]
			if has_uv == True:
				face_uvs = [uvs[face[0]], uvs[face[2]], uvs[face[1]]]
		try:
			BMFace = bm.faces.get(face_vertices) or bm.faces.new(face_vertices)
		except:
			pass
		if BMFace.index != -1:
			BMFace = BMFace.copy(verts=False, edges=False)
		BMFace.index = i
		if additional_data == True:
			BMFace[flag] = nearest_quad
		
		if has_uv == True:
			for loop, uv in zip(BMFace.loops, face_uvs):
				if flip_uv == True:
					uv = flip_uv(uv)
					loop[uv_layer].uv = uv
				else:
					loop[uv_layer].uv = uv
	
	material_name = str(texture_name, 'ascii')
	mat = bpy.data.materials.get(material_name)
	if mat == None:
		mat = bpy.data.materials.new(material_name)
		mat.use_nodes = True
		mat.name = material_name
		
		if mat.node_tree.nodes[0].bl_idname != "ShaderNodeOutputMaterial":
			mat.node_tree.nodes[0].name = material_name
	
	if mat.name not in me_ob.materials:
		me_ob.materials.append(mat)
	
	#Finish up, write the bmesh back to the mesh
	bm.to_mesh(me_ob)
	bm.free()
	
	return obj


def scale_position(position):
	x, y, z = position
	position = x, y*0.25, -z
	
	return position


def flip_uv(uv):
	u, v = uv
	uv = u, -v + 1.0
	
	return uv


def clearScene(context): # OK
	#for obj in bpy.context.scene.objects:
	#	obj.select_set(True)
	#bpy.ops.object.delete()

	for block in bpy.data.objects:
		#if block.users == 0:
		bpy.data.objects.remove(block, do_unlink = True)

	for block in bpy.data.meshes:
		if block.users == 0:
			bpy.data.meshes.remove(block)

	for block in bpy.data.materials:
		if block.users == 0:
			bpy.data.materials.remove(block)

	for block in bpy.data.textures:
		if block.users == 0:
			bpy.data.textures.remove(block)

	for block in bpy.data.images:
		if block.users == 0:
			bpy.data.images.remove(block)
	
	for block in bpy.data.cameras:
		if block.users == 0:
			bpy.data.cameras.remove(block)
	
	for block in bpy.data.lights:
		if block.users == 0:
			bpy.data.lights.remove(block)
	
	for block in bpy.data.armatures:
		if block.users == 0:
			bpy.data.armatures.remove(block)
	
	for block in bpy.data.collections:
		if block.users == 0:
			bpy.data.collections.remove(block)
		else:
			bpy.data.collections.remove(block, do_unlink=True)


@orientation_helper(axis_forward='-Y', axis_up='Z')
class ImportNFSHSPPC(Operator, ImportHelper):
	"""Load a Need for Speed High Stakes Pocket PC model file"""
	bl_idname = "import_nfshsppc.data"	# important since its how bpy.ops.import_test.some_data is constructed
	bl_label = "Import models"
	bl_options = {'PRESET'}
	
	# ImportHelper mixin class uses this
	filename_ext = "*.z3d;*.trk",
	
	filter_glob: StringProperty(
			options={'HIDDEN'},
			default="*.z3d;*.trk",
			maxlen=255,	 # Max internal buffer length, longer would be clamped.
			)
	
	files: CollectionProperty(
			type=OperatorFileListElement,
			)
	
	directory: StringProperty(
			# subtype='DIR_PATH' is not needed to specify the selection mode.
			subtype='DIR_PATH',
			)
	
	# List of operator properties, the attributes will be assigned
	# to the class instance from the operator settings before calling.
	
	clear_scene: BoolProperty(
			name="Clear scene",
			description="Check in order to clear the scene",
			default=True,
			)
	
	def execute(self, context): # OK
		global_matrix = axis_conversion(from_forward='Z', from_up='Y', to_forward=self.axis_forward, to_up=self.axis_up).to_4x4()
		
		if len(self.files) > 1:
			os.system('cls')
		
			files_path = []
			for file_elem in self.files:
				files_path.append(os.path.join(self.directory, file_elem.name))
			
			print("Importing %d files" % len(files_path))
			
			if self.clear_scene == True:
				print("Clearing initial scene...")
				clearScene(context)
				print("Setting 'clear_scene' to False now...")
				self.clear_scene = False
			
			print()
			
			for file_path in files_path:
				status = main(context, file_path, self.clear_scene, global_matrix)
				
				if status == {"CANCELLED"}:
					self.report({"ERROR"}, "Importing of file %s has been cancelled. Check the system console for information." % os.path.splitext(os.path.basename(file_path))[0])
				
				print()
				
			return {'FINISHED'}
		elif os.path.isfile(self.filepath) == False:
			os.system('cls')
			
			files_path = []
			for file in os.listdir(self.filepath):
				file_path = os.path.join(self.filepath, file)
				if os.path.isfile(file_path) == True:
					files_path.append(file_path)
				print("Importing %d files" % len(files_path))
			
			for file_path in files_path:
				status = main(context, file_path, self.clear_scene, global_matrix)
				
				if status == {"CANCELLED"}:
					self.report({"ERROR"}, "Importing of file %s has been cancelled. Check the system console for information." % os.path.splitext(os.path.basename(file_path))[0])
				
				print()
				
			return {'FINISHED'}
		else:
			os.system('cls')
			
			status = main(context, self.filepath, self.clear_scene, global_matrix)
			
			if status == {"CANCELLED"}:
				self.report({"ERROR"}, "Importing has been cancelled. Check the system console for information.")
			
			return status
	
	def draw(self, context):
		layout = self.layout
		layout.use_property_split = True
		layout.use_property_decorate = False  # No animation.
		
		sfile = context.space_data
		operator = sfile.active_operator
		
		##
		box = layout.box()
		split = box.split(factor=0.75)
		col = split.column(align=True)
		col.label(text="Preferences", icon="OPTIONS")
		
		box.prop(operator, "clear_scene")
		
		##
		box = layout.box()
		split = box.split(factor=0.75)
		col = split.column(align=True)
		col.label(text="Blender orientation", icon="OBJECT_DATA")
		
		row = box.row(align=True)
		row.label(text="Forward axis")
		row.use_property_split = False
		row.prop_enum(operator, "axis_forward", 'X', text='X')
		row.prop_enum(operator, "axis_forward", 'Y', text='Y')
		row.prop_enum(operator, "axis_forward", 'Z', text='Z')
		row.prop_enum(operator, "axis_forward", '-X', text='-X')
		row.prop_enum(operator, "axis_forward", '-Y', text='-Y')
		row.prop_enum(operator, "axis_forward", '-Z', text='-Z')
		
		row = box.row(align=True)
		row.label(text="Up axis")
		row.use_property_split = False
		row.prop_enum(operator, "axis_up", 'X', text='X')
		row.prop_enum(operator, "axis_up", 'Y', text='Y')
		row.prop_enum(operator, "axis_up", 'Z', text='Z')
		row.prop_enum(operator, "axis_up", '-X', text='-X')
		row.prop_enum(operator, "axis_up", '-Y', text='-Y')
		row.prop_enum(operator, "axis_up", '-Z', text='-Z')


def menu_func_import(self, context): # OK
	pcoll = preview_collections["main"]
	my_icon = pcoll["my_icon"]
	self.layout.operator(ImportNFSHSPPC.bl_idname, text="Need for Speed High Stakes Pocket PC (.z3d, .trk)", icon_value=my_icon.icon_id)


classes = (
		ImportNFSHSPPC,
)

preview_collections = {}


def register(): # OK
	import bpy.utils.previews
	pcoll = bpy.utils.previews.new()
	
	my_icons_dir = os.path.join(os.path.dirname(__file__), "polly_icons")
	pcoll.load("my_icon", os.path.join(my_icons_dir, "nfshs_ppc_icon.png"), 'IMAGE')

	preview_collections["main"] = pcoll
	
	for cls in classes:
		bpy.utils.register_class(cls)
	bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister(): # OK
	for pcoll in preview_collections.values():
		bpy.utils.previews.remove(pcoll)
	preview_collections.clear()
	
	for cls in classes:
		bpy.utils.unregister_class(cls)
	bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)


if __name__ == "__main__":
	register()
