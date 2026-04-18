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
			meshes = []
			
			for object in objects:
				if object.type == 'MESH':
					name, vertices, uvs, faces, material_name, status = read_object(object)
					mesh = [name, vertices, uvs, faces, material_name]
				
				if status == 1:
					return {'CANCELLED'}
				
				meshes.append(mesh)
		
		elif file_extension == ".trk":
			print("ERROR: Exporting .trk not supported yet.")
			return {'CANCELLED'}
			
			for collection in main_collection.children:
				if collection.name == "Cameras":
					cameras = collection.objects
					cameras_ = []
					
					for camera in cameras:
						if camera.type == 'EMPTY':
							nearest_road_quad = camera["nearest_road_quad"]
							camera_pos = Matrix(np.linalg.inv(m) @ camera.matrix_world)
							camera_pos = camera_pos.to_translation()
							camera_ = [nearest_road_quad, camera_pos]
						cameras_.append(camera_)
			
		else:
			print("ERROR: Unknown file extension %s." % (file_extension))
			return {'CANCELLED'}
		
		## Writing data
		print("\tWriting data...")
		writing_time = time.time()
		
		if file_extension == ".z3d":
			write_z3d(file_path, meshes)
		elif file_extension == ".trk":
			write_trk_cameras(file_path, cameras_)
		
		elapsed_time = time.time() - writing_time
		print("\t... %.4fs" % elapsed_time)	
	
	print("Finished")
	elapsed_time = time.time() - start_time
	print("Elapsed time: %.4fs" % elapsed_time)
	
	return {'FINISHED'}


def read_object(object):
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
			vertices.append([vert_co for i, vert_co in enumerate(vert.co)])
			vertices_list[vert.index] = vert_ind
			vert_ind += 1
	
	try:
		uv_layer = mesh.uv_layers.active.data
		has_uv = True
	except:
		has_uv = False
	
	for face in mesh.polygons:
		if face.hide == True:
			continue
		
		vertexIds = []
		for loop_ind in face.loop_indices:
			vert_index = vertices_list[loops[loop_ind].vertex_index]
			vertexIds.append(vert_index)
			if has_uv == True:
				if vert_index not in uvs:
					uvs[vert_index] = uv_layer[loop_ind].uv
		
		vertexId0, vertexId1, vertexId2 = vertexIds
		
		faces.append([vertexId0, vertexId1, vertexId2])
	
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
			name, vertices, uvs, polygons, material_name = objects[i]
			
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


def write_trk_cameras(file_path, cameras):
	os.makedirs(os.path.dirname(file_path), exist_ok = True)
	
	with open(file_path, "wb") as f:
		
		num_cameras = len(cameras)
		
		f.write(struct.pack('<I', num_cameras))
		
		for i in range(0, num_cameras):
			nearest_road_quad, camera_pos = cameras[i]
			
			f.write(struct.pack('<I', nearest_road_quad))
			f.write(struct.pack('<3f', *camera_pos))
	
	return 0


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
			default="*.z3d",
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
	self.layout.operator(ExportNFSHSPPC.bl_idname, text="Need for Speed High Stakes Pocket PC (.z3d)", icon_value=my_icon.icon_id)


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
