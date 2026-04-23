#-*- coding:utf-8 -*-

# Blender Need for Speed High Stakes Pocket PC exporter Add-on
# Add-on developed by PolySoupList


bl_info = {
	"name": "Export to Need for Speed High Stakes Pocket PC models format (.z3d)",
	"description": "Save objects as Need for Speed High Stakes Pocket PC files",
	"author": "PolySoupList",
	"version": (1, 0, 0),
	"blender": (3, 6, 23),
	"location": "File > Export > Need for Speed High Stakes Pocket PC (.z3d)",
	"warning": "",
	"wiki_url": "",
	"tracker_url": "",
	"support": "COMMUNITY",
	"category": "Import-Export"}


import bpy
from bpy.types import Operator
from bpy.props import (
	StringProperty,
	BoolProperty
)
from bpy_extras.io_utils import (
	ExportHelper,
	orientation_helper,
	axis_conversion,
)
import bmesh
import math
from mathutils import Matrix
import os
import time
import struct
import numpy as np


def main(context, export_path, m):
	os.system('cls')
	start_time = time.time()
	
	if bpy.ops.object.mode_set.poll():
		bpy.ops.object.mode_set(mode='OBJECT')
	
	for main_collection in bpy.context.scene.collection.children:
		is_hidden = bpy.context.view_layer.layer_collection.children.get(main_collection.name).hide_viewport
		is_excluded = bpy.context.view_layer.layer_collection.children.get(main_collection.name).exclude
		
		if is_hidden or is_excluded:
			print("WARNING: skipping main collection %s since it is hidden or excluded." % (main_collection.name))
			print("")
			continue
		
		file_path = os.path.join(export_path, main_collection.name)
		
		print("Reading scene data for main collection %s..." % (main_collection.name))
		
		file_extension = file_path[-4:].lower()
		
		if file_extension == ".z3d":
			objects = main_collection.objects
			object_index = -1
			
			Z3D_Objects = []
			
			for object in objects:
				if object.type == 'MESH':
					try:
						object_index = object["object_index"]
					except:
						object_index = object_index + 1
					
					name, vertices, uvs, faces, material_name, status = read_object(object, False, False)
					
					if status == 1:
						return {'CANCELLED'}
					
					Z3D_Objects.append([object_index, [name, vertices, uvs, faces, material_name]])
			
			Z3D_Objects.sort(key=lambda x:x[0])
		
		elif file_extension == ".trk":
			print("Experimental .trk export requires adding the rest of data with a hex editor.")
			
			TRK_Cameras = []
			TRK_SpriteList = []
			TRK_Objects = []
			TRK_Walls = []
			TRK_NavMesh = []
			
			Quad_Sprites = {}
			Quad_Objects = {}
			Quad_Walls = {}
			Quad_Quaternion = {}
			
			for collection in main_collection.children:
				if collection.name.lower() == "cameras":
					cameras = collection.objects
					
					for camera in cameras:
						if camera.type == 'EMPTY':
							try:
								camera_index = camera["camera_index"]
							except:
								camera_index = camera_index + 1
							
							nearest_quad = camera["nearest_quad"]
							camera_pos = Matrix(np.linalg.inv(m) @ camera.matrix_world)
							camera_pos = camera_pos.to_translation()
							camera_pos = scale_position(camera_pos)
							
							TRK_Cameras.append([camera_index, [nearest_quad, camera_pos]])
				
				elif collection.name.lower() == "sprites":
					TRK_SpriteList = collection["spritelist"]
					
					sprites = collection.objects
					
					for sprite in sprites:
						if sprite.type == 'EMPTY':
							try:
								nearest_quad = sprite["nearest_quad"]
							except:
								pass
							sprite_index = sprite["sprite_index"]
							sprite_pos = Matrix(np.linalg.inv(m) @ sprite.matrix_world)
							sprite_pos = sprite_pos.to_translation()
							sprite_pos = scale_position(sprite_pos)
							
							if nearest_quad not in Quad_Sprites:
								Quad_Sprites[nearest_quad] = []
							Quad_Sprites[nearest_quad].append([sprite_pos, sprite_index])
				
				elif collection.name.lower() == "objects":
					objects = collection.objects
					object_index = -1
					
					for object in objects:
						if object.type == 'MESH':
							try:
								object_index = object["object_index"]
							except:
								object_index = object_index + 1
							
							try:
								nearest_quad = object["nearest_quad"]
								for i in nearest_quad:
									if i not in Quad_Objects:
										Quad_Objects[i] = []
									Quad_Objects[i].append(object_index)
							except:
								pass
							
							name, vertices, uvs, faces, material_name, status = read_object(object, True, False)
							
							if status == 1:
								return {'CANCELLED'}
							
							TRK_Objects.append([object_index, [vertices, uvs, faces, material_name]])
				
				elif collection.name.lower() == "walls":
					walls = collection.objects
					wall_index = -1
					
					for wall in walls:
						if wall.type == 'MESH':
							try:
								wall_index = wall["wall_index"]
							except:
								wall_index = wall_index + 1
							
							name, vertices, uvs, faces, material_name, status = read_object(wall, True, True)
							
							for face in faces:
								nearest_quad = face[0]
								wall_polygon = face[1]
								
								if nearest_quad not in Quad_Walls:
									Quad_Walls[nearest_quad] = []
								
								Quad_Walls[nearest_quad].append([wall_index, wall_polygon])
							
							if status == 1:
								return {'CANCELLED'}
							
							TRK_Walls.append([wall_index, [vertices, uvs, material_name]])
				
				elif collection.name.lower() == "road":
					roads = collection.objects
					road = roads[0]
					
					if road.type == 'MESH':
						
						name, vertices, uvs, faces, material_name, status = read_object(road, True, False)
						
						for i in range(0, len(faces)):
							quad_index = str(i)
							
							if i not in Quad_Quaternion:
								Quad_Quaternion[i] = []
							
							try:
								Quad_Quaternion[i] = road[quad_index].to_list()
							except:
								pass
						
						if status == 1:
							return {'CANCELLED'}
						
						TRK_Road = [vertices, uvs, faces, material_name, Quad_Walls, Quad_Objects, Quad_Sprites, Quad_Quaternion]
				
				elif collection.name.lower() == "navmesh":
					navmeshes = collection.objects
					navmesh = navmeshes[0]
					
					if navmesh.type == 'MESH':
						mesh = navmesh.data
						for vert in mesh.vertices:
							TRK_NavMesh.append(scale_position(vert.co))
			
			TRK_Cameras.sort(key=lambda x:x[0])
			TRK_Objects.sort(key=lambda x:x[0])
			TRK_Walls.sort(key=lambda x:x[0])
			#print(Quad_Sprites)
			#print(Quad_Objects)
			#print(Quad_Walls)
			#print(Quad_Quaternion)
			trk = [TRK_Cameras, TRK_SpriteList, TRK_Objects, TRK_Walls, TRK_Road, TRK_NavMesh]
		
		else:
			print("ERROR: Unknown file extension %s." % (file_extension))
			return {'CANCELLED'}
		
		## Writing data
		print("\tWriting data...")
		writing_time = time.time()
		
		if file_extension == ".z3d":
			write_z3d(file_path, Z3D_Objects)
		elif file_extension == ".trk":
			write_trk(file_path, trk)
		
		elapsed_time = time.time() - writing_time
		print("\t... %.4fs" % elapsed_time)	
	
	print("Finished")
	elapsed_time = time.time() - start_time
	print("Elapsed time: %.4fs" % elapsed_time)
	
	return {'FINISHED'}


def read_object(object, flipped_uv, additional_data):
	vertices = []
	faces = []
	uvs = {}
	vertices_list = {}
	vert_ind = 0
	
	# Inits
	mesh = object.data
	loops = mesh.loops
	bm = bmesh.new()
	bm.from_mesh(mesh)
	
	name = (object.name).encode('ascii')
	
	for vert in bm.verts:
		if vert.hide == False:
			vert_co = scale_position(vert.co)
			vertices.append(vert_co)
			vertices_list[vert.index] = vert_ind
			vert_ind += 1
	
	try:
		uv_layer = mesh.uv_layers.active.data
		has_uv = True
	except:
		has_uv = False
	
	if additional_data == True:
		nearest_quads = mesh.attributes.get("flag")
	
	for face in mesh.polygons:
		if face.hide == True:
			continue
		
		vertexIds = []
		for loop_ind in face.loop_indices:
			vert_index = vertices_list[loops[loop_ind].vertex_index]
			vertexIds.append(vert_index)
			if has_uv == True:
				if vert_index not in uvs:
					if flipped_uv == True:
						uvs[vert_index] = flip_uv(uv_layer[loop_ind].uv)
					else:	
						uvs[vert_index] = uv_layer[loop_ind].uv
		
		if additional_data == True:
			try:
				nearest_quad = nearest_quads.data[face.index].value
			except:
				pass
		
		if len(vertexIds) == 3:
			vertexId0, vertexId1, vertexId2 = vertexIds
		elif len(vertexIds) == 4:
			vertexId0, vertexId1, vertexId2, vertexId3 = vertexIds
		
		if additional_data == True:
			faces.append([nearest_quad, [vertexId0, vertexId2, vertexId1]])
		else:
			if len(vertexIds) == 4:
				face_center = scale_position(face.center)
				faces.append([face_center, [vertexId2, vertexId1, vertexId3, vertexId0]])
			else:	
				faces.append([vertexId0, vertexId2, vertexId1])
	
	material_name = (mesh.materials[0].name).encode('ascii')
	
	bm.clear()
	bm.free()
	
	return (name, vertices, uvs, faces, material_name, 0)


def write_z3d(file_path, objects):
	os.makedirs(os.path.dirname(file_path), exist_ok = True)
	
	with open(file_path, "wb") as f:
		
		f.write(struct.pack('<I', 0))
		
		num_meshes = len(objects)
		
		f.write(struct.pack('<I', num_meshes))
		
		for i in range(0, num_meshes):
			name, vertices, uvs, polygons, material_name = objects[i][1]
			
			if len(uvs) != 0:
				has_uv = True
				f.write(struct.pack('<I', 1))
			else:
				has_uv = False
				f.write(struct.pack('<I', 0))
			
			f.write(struct.pack('<I', 0))
			
			f.write(struct.pack('<I', len(name)))
			f.write(name)
			f.write(struct.pack('<B', 0))
			
			num_vrtx = len(vertices)
			num_plgn = len(polygons)
			
			f.write(struct.pack('<I', num_vrtx))
			f.write(struct.pack('<I', num_plgn))
			
			for j in range(0, num_vrtx):
				f.write(struct.pack('<3f', *vertices[j]))
			
			if has_uv == True:
				for j in range(0, num_vrtx):
					f.write(struct.pack('<2f', *uvs[j]))
				
			for j in range(0, num_plgn):
				f.write(struct.pack('<3H', *polygons[j]))
			
			f.write(struct.pack('<I', len(material_name)))
			f.write(material_name)
			f.write(struct.pack('<B', 0))
	
	return 0


def write_trk_road(f, road):
	vertices, uvs, quads, material_name, Quad_Walls, Quad_Objects, Quad_Sprites, Quad_Quaternion = road
	
	vertex_data = [vertices, uvs]
	write_trk_vertex_data(f, vertex_data)
	
	num_quads = len(quads)
	
	f.write(struct.pack('<I', num_quads))
	
	for i in range(0, num_quads):
		f.write(struct.pack('<4H', *quads[i][1]))
		f.write(struct.pack('<3f', *quads[i][0]))
		
		try:
			quaternion = Quad_Quaternion[i]
			f.write(struct.pack('<4f', *quaternion))
		except:
			f.write(struct.pack('<4f', 0.0, 1.0, 0.0, 0.0))
		
		try:
			polygons = Quad_Walls[i]
			num_plgn = len(polygons)
			
			f.write(struct.pack('<I', num_plgn))
			
			for j in range(0, num_plgn):
				wall_index = polygons[j][0]
				wall_polygon = polygons[j][1]
				
				f.write(struct.pack('<I', wall_index))
				f.write(struct.pack('<3H', *wall_polygon))
		except:
			f.write(struct.pack('<I', 0))
		
		try:
			child_objects = Quad_Objects[i]
			num_objects = len(child_objects)
			
			f.write(struct.pack('<I', num_objects))
			
			for j in range(0, num_objects):
				f.write(struct.pack('<I', child_objects[j]))
		except:
			f.write(struct.pack('<I', 0))
		
		try:
			child_sprites = Quad_Sprites[i]
			num_sprites = len(child_sprites)
			
			f.write(struct.pack('<I', num_sprites))
			
			for j in range(0, num_sprites):
				f.write(struct.pack('<3f', *child_sprites[j][0]))
				f.write(struct.pack('<I', child_sprites[j][1]))
		except:
			f.write(struct.pack('<I', 0))
	
	f.write(struct.pack('<I', len(material_name)))
	f.write(material_name)
	
	return 0


def write_trk_walls(f, walls):
	num_walls = len(walls)
	
	f.write(struct.pack('<I', num_walls))
	
	for i in range(0, num_walls):
		vertices, uvs, material_name = walls[i][1]
		
		vertex_data = [vertices, uvs]
		write_trk_vertex_data(f, vertex_data)
		
		f.write(struct.pack('<I', len(material_name)))
		f.write(material_name)
	
	return 0


def write_trk_objects(f, objects):
	num_objects = len(objects)
	
	f.write(struct.pack('<I', num_objects))
	
	for i in range(0, num_objects):
		vertices, uvs, polygons, material_name = objects[i][1]
		
		vertex_data = [vertices, uvs]
		write_trk_vertex_data(f, vertex_data)
		
		num_plgn = len(polygons)
		f.write(struct.pack('<I', num_plgn))
		
		for j in range(0, num_plgn):
			f.write(struct.pack('<3H', *polygons[j]))
		
		f.write(struct.pack('<I', len(material_name)))
		f.write(material_name)
	
	return 0


def write_trk_vertex_data(f, vertex_data):
	vertices, uvs = vertex_data
	
	num_vrtx = len(vertices)
	f.write(struct.pack('<I', num_vrtx))
	
	for i in range(0, num_vrtx):
		f.write(struct.pack('<3f', *vertices[i]))
	
	for i in range(0, num_vrtx):
		f.write(struct.pack('<2f', *uvs[i]))
	
	return 0


def write_trk_spritelist(f, spritelist):
	num_spritenames = len(spritelist)
	
	f.write(struct.pack('<I', num_spritenames))
	
	for i in range(0, num_spritenames):
		sprite_name = (spritelist[i].encode('ascii'))
		
		f.write(struct.pack('<I', len(sprite_name)))
		f.write(sprite_name)
	
	return 0


def write_trk_cameras(f, cameras):
	num_cameras = len(cameras)
	
	f.write(struct.pack('<I', num_cameras))
	
	for i in range(0, num_cameras):
		nearest_road_quad, camera_pos = cameras[i][1]
		
		f.write(struct.pack('<I', nearest_road_quad))
		f.write(struct.pack('<3f', *camera_pos))
	
	return 0


def write_trk(file_path, trk):
	os.makedirs(os.path.dirname(file_path), exist_ok = True)
	
	cameras, spritelist, objects, walls, road, navmesh = trk
	
	with open(file_path, "wb") as f:
		write_trk_cameras(f, cameras)
		write_trk_spritelist(f, spritelist)
		write_trk_objects(f, objects)
		write_trk_walls(f, walls)
		write_trk_road(f, road)
		
		num_quads = len(road[2])
		for i in range(0, num_quads*2):
			try:
				f.write(struct.pack('<3f', *navmesh[i]))
			except:
				f.write(struct.pack('<3f', 0.0, 0.0, 0.0))
	
	return 0


def scale_position(position):
	x, y, z = position
	position = x, y*4, -z
	
	return position


def flip_uv(uv):
	u, v = uv
	uv = u, -v + 1.0
	
	return uv


def id_to_bytes(id):
	id_old = id
	id = id.replace('_', '')
	id = id.replace(' ', '')
	id = id.replace('-', '')
	try:
		int(id, 16)
	except ValueError:
		print("ERROR: Invalid hexadecimal string: %s" % id_old)
	return bytearray.fromhex(id)


def id_to_int(id):
	id_old = id
	id = id.replace('_', '')
	id = id.replace(' ', '')
	id = id.replace('-', '')
	id = ''.join(id[::-1][x:x+2][::-1] for x in range(0, len(id), 2))
	return int(id, 16)


@orientation_helper(axis_forward='-Y', axis_up='Z')
class ExportNFSHSPPC(Operator, ExportHelper):
	"""Export as a Need for Speed High Stakes Pocket PC Model file"""
	bl_idname = "export_nfshsppc.data"
	bl_label = "Export to folder"
	bl_options = {'PRESET'}

	filename_ext = ""
	use_filter_folder = True

	filter_glob: StringProperty(
			options={'HIDDEN'},
			default="*.z3d;*.trk",
			maxlen=255,
			)

	
	def execute(self, context):
		userpath = self.properties.filepath
		if os.path.isfile(userpath):
			self.report({"ERROR"}, "Please select a directory not a file\n" + userpath)
			return {"CANCELLED"}
		
		global_matrix = axis_conversion(from_forward='Z', from_up='Y', to_forward=self.axis_forward, to_up=self.axis_up).to_4x4()
		
		status = main(context, self.filepath, global_matrix)
		
		if status == {"CANCELLED"}:
			self.report({"ERROR"}, "Exporting has been cancelled. Check the system console for information.")
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


def menu_func_export(self, context):
	pcoll = preview_collections["main"]
	my_icon = pcoll["my_icon"]
	self.layout.operator(ExportNFSHSPPC.bl_idname, text="Need for Speed High Stakes Pocket PC (.z3d, .trk)", icon_value=my_icon.icon_id)


classes = (
		ExportNFSHSPPC,
)

preview_collections = {}


def register():
	import bpy.utils.previews
	pcoll = bpy.utils.previews.new()
	
	my_icons_dir = os.path.join(os.path.dirname(__file__), "polly_icons")
	pcoll.load("my_icon", os.path.join(my_icons_dir, "nfshs_ppc_icon.png"), 'IMAGE')

	preview_collections["main"] = pcoll
	
	for cls in classes:
		bpy.utils.register_class(cls)
	bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
	for pcoll in preview_collections.values():
		bpy.utils.previews.remove(pcoll)
	preview_collections.clear()
	
	for cls in classes:
		bpy.utils.unregister_class(cls)
	bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":
	register()
