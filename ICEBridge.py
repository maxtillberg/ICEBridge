"""
[Blender and Python] Sending data to IDA ICE
Max Tillberg - August 2022
Email: max.tillberg@equa.se
--------
Copyright (c) 2022 Equa Simulation AB

Bugs:
    - External objects are not visible if not placed in ARCDATA and objects can only e imported oce with script
    - Zone and building bodies tend to be placed on top of each other origo
    - Problems with with and normal direction of windows and doors
    
Tod do:
    - Give windows and doors names if available
    - Get data from IFC-files
    
"""

bl_info = {
    # required
    'name': 'ICE Bridge',
    'blender': (3, 0, 0),
    'category': 'Object',
    # optional
    'version': (0, 4, 0),
    'author': 'Max Tillberg',
    'description': 'Export tool to IDA ICE',
}

import bpy
import os
import mathutils
import math

#Function to determine largest object
def maximum(a, b):
    if a >= b:
        return a
    else:
        return b

# == GLOBAL VARIABLES
object_types = [
                ("0","Building bodies","Building bodies"),
                ("1","Zones","Zones"),
                ("2","Building bodies and Zones","Building bodies and Zones"),
                ("3","Windows","Windows"),
                ("4","Doors","Doors"),
                ("5","External objects","External objects"),
                ]
version_types = [
                ("0","4.8 or earlier","4.8 or earlier"),
                #("1","5.0 or later","5.0 or later"),
                ]
#source_types = [
#                ("0","Volumes","Volumes"),
#                ("1","Planes","Planes"),
#              ]

PROPS = [
    ('object', bpy.props.EnumProperty(name='Object', description="object", items=object_types)),
    #('source', bpy.props.EnumProperty(name='Source', description="source", items=source_types)),
    #('rotate_normals', bpy.props.BoolProperty(name='Rotate Normals', default=False)),
    ('version', bpy.props.EnumProperty(name='Version', description="version", items=version_types)),
    ('path', bpy.props.StringProperty(name="Path",description="Path to Directory", default="", maxlen=1024, subtype='DIR_PATH')),
    #('name', bpy.props.StringProperty(name="Name",description="Script name", default="")),
    ('shading', bpy.props.BoolProperty(name='Shading', default=False)),
    ('transparency', bpy.props.IntProperty(name='Transparency', default=0, min=0, max=100)),
]

# == UTILS
def export_object(params):
    #print (params)
    if params[0] == "0": #Building bodies
        ICEScript=open(str(params[1]) + 'ImportBuildingBodies.txt','w')
        view_layer = bpy.context.view_layer
        obj_active = view_layer.objects.active
        selection = bpy.context.selected_objects
        bpy.ops.object.select_all(action='DESELECT')

        for obj in selection:
            obj.select_set(True)
            #Get Speckle category, type and family
            #Check if a name exists. We should also check if name is valid and unique
            custompropertyexists = bpy.data.objects[str(obj.name)].get('name') is not None
            if custompropertyexists == True:
                fn = (str(bpy.data.objects[str(obj.name)]['name']))
            elif custompropertyexists == False:
                fn = str(obj.name)
                
            fn = fn.replace('/', '_') #IFC-names can be invalid file names
            fn = (str(params[1]) + str(fn)) #Get path
            fp = fn  + '.obj'
           # some exporters only use the active object
            view_layer.objects.active = obj
            bpy.ops.export_scene.obj(filepath=fp, axis_forward='-Y', axis_up='Z', use_selection=True, check_existing=True)
            ICEScript.write('(:call Import-Geometry (:call ice-3d-pane [@] t t)' +" '" + 'building-body ' + '(0 0 0)' + ' 0 "' + fp + '")' +'\n')
            obj.select_set(False)

        ICEScript.close()

        view_layer.objects.active = obj_active

        for obj in selection:
            obj.select_set(True)

        #Ersätt  \ med \\
        # Read in the file
        with open(str(params[1]) + 'ImportBuildingBodies.txt', 'r') as file :
          filedata = file.read()

        # Replace the target string
        filedata = filedata.replace("\\", "\\\\")

        # Write the file out again
        with open(str(params[1]) + 'ImportBuildingBodies.txt', 'w') as file:
          file.write(filedata)
          
    if params[0] == "1": #Zones. This actually the same as building bodies and zones but deletes building bodies afterwards
        ICEScript=open(str(params[1]) + 'ImportZones.txt','w')
        view_layer = bpy.context.view_layer
        obj_active = view_layer.objects.active
        selection = bpy.context.selected_objects
        bpy.ops.object.select_all(action='DESELECT')

        for obj in selection:
            obj.select_set(True)
            #Get Speckle category, type and family
            #Check if a name exists. We should also check if name is valid and unique
            custompropertyexists = bpy.data.objects[str(obj.name)].get('name') is not None
            if custompropertyexists == True:
                fn = (str(bpy.data.objects[str(obj.name)]['name']))
            elif custompropertyexists == False:
                fn = str(obj.name)
                
            fnorg = fn.replace('/', '_') #IFC-names can be invalid file names
            fn = (str(params[1]) + str(fnorg)) #Get path
            fp = fn  + '.obj'
           # some exporters only use the active object
            view_layer.objects.active = obj
            bpy.ops.export_scene.obj(filepath=fp, axis_forward='-Y', axis_up='Z', use_selection=True, check_existing=True)
            ICEScript.write('(:call Import-Geometry (:call ice-3d-pane [@] t t)' +" '" + 'zone ' + '(0 0 0)' + ' 0 "' + fp + '")' +'\n' + '(:UPDATE [@](:REMOVE "' + str(fnorg) + '-s"))'+'\n')
            obj.select_set(False)

        ICEScript.close()

        view_layer.objects.active = obj_active

        for obj in selection:
            obj.select_set(True)

        #Ersätt  \ med \\
        # Read in the file
        with open(str(params[1]) + 'ImportZones.txt', 'r') as file :
          filedata = file.read()

        # Replace the target string
        filedata = filedata.replace("\\", "\\\\")

        # Write the file out again
        with open(str(params[1]) + 'ImportZones.txt', 'w') as file:
          file.write(filedata)
  
    if params[0] == "2": #Building bodies and zones
        ICEScript=open(str(params[1]) + '\\ImportBuildingBodiesAndZones.txt','w')
        view_layer = bpy.context.view_layer
        obj_active = view_layer.objects.active
        selection = bpy.context.selected_objects
        bpy.ops.object.select_all(action='DESELECT')
        #Insert point can be changed if needed, by default original point
        
        
        for obj in selection:
            obj.select_set(True)
            #Get Speckle category, type and family
            #Check if a name exists. We should also check if name is valid and unique
            custompropertyexists = bpy.data.objects[str(obj.name)].get('name') is not None
            if custompropertyexists == True:
                fn = (str(bpy.data.objects[str(obj.name)]['name']))
            elif custompropertyexists == False:
                fn = str(obj.name)
                
            fn = fn.replace('/', '_') #IFC-names can be invalid file names
            fn = (str(params[1]) + str(fn)) #Get path
            fp = fn  + '.obj'
           # some exporters only use the active object
            view_layer.objects.active = obj
            bpy.ops.export_scene.obj(filepath=fp, axis_forward='-Y', axis_up='Z', use_selection=True, check_existing=True)
            ICEScript.write('(:call Import-Geometry (:call ice-3d-pane [@] t t)' +" '" + 'zone ' + '(0 0 0)' + ' 0 "' + fp + '")' +'\n')
            obj.select_set(False)

        ICEScript.close()

        view_layer.objects.active = obj_active

        for obj in selection:
            obj.select_set(True)

        #Ersätt  \ med \\
        # Read in the file
        with open(str(params[1]) + '\\ImportBuildingBodiesAndZones.txt', 'r') as file :
          filedata = file.read()

        # Replace the target string
        filedata = filedata.replace("\\", "\\\\")

        # Write the file out again
        with open(str(params[1]) + '\\ImportBuildingBodiesAndZones.txt', 'w') as file:
          file.write(filedata)
  
    if params[0] == "3" or str(params[0]) == "4": #Window or door
        #Create Script file for IDA ICE
        if params[0] == "3":
            ICEScript=open(str(params[1]) + 'ImportWindows.txt','w')
        elif params[0] == "4":
            ICEScript=open(str(params[1]) + 'ImportDoors.txt','w')

        from bpy import context as C

        for ob in C.selected_objects:
            #print(ob.matrix_world.to_euler('XYZ'))
            #Ensure origin is centered on bounding box center
            bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
            centre = ob.location  # Does this work for all objects? All objects should be changed mnually manually by using Object-Set Origin-Origin to center of mass (surface) before export
            faces_up = (p for p in ob.data.polygons)# if p.normal.z > 0) #Not used right now
            normal = max(faces_up, key=lambda f: f.area).normal #Find largest area. Does not work if transformed (rotated). One way to fix this is to send/get windows to Speckle.
            #Find width and heigh. Probably depends on object type so I use two methods and use the largest
            dimensionwidth = (ob.dimensions[0])
            dimensiondepth = (ob.dimensions[1])
            dimensionheight = (ob.dimensions[2])
            largestdimensionwidth = (maximum(dimensionwidth, dimensiondepth))
            verts = ob.data.vertices #Get all corners
            calculatedwidth = max(v.co.x for v in verts) - min(v.co.x for v in verts) #Get largest value, this is only in x, not in the normal plane. One way would be to use the IFC/Speckle data.
            calculateddepth = max(v.co.y for v in verts) - min(v.co.y for v in verts) #Get smallest value
            largestcalculatedwidth = (maximum(calculatedwidth, calculateddepth)) #Make sure the largest of with and depth is choosen
            appwidth = (maximum(largestdimensionwidth, largestcalculatedwidth))
            #Possibility to rotate normal 90 degrees:
            #nx = (normal.x * math.cos(math.radians(90))) - (normal.y * math.sin(math.radians(90)))
            #ny = (normal.x * math.sin(math.radians(90))) + (normal.y * math.cos(math.radians(90)))
            calculatedheight = max(v.co.z for v in verts) - min(v.co.z for v in verts)
            height = (maximum(dimensionheight, calculatedheight))
            
             #Get Speckle category, type and family
            #Check if a name exists. We should also check if name is valid and unique
            custompropertyexists = bpy.data.objects[str(ob.name)].get('type') is not None
            if custompropertyexists == True:
                panetype = (str(bpy.data.objects[str(ob.name)]['type']))
            elif custompropertyexists == False:
                panetype = "Undefined"
            
            #Produce script
            if appwidth > 0.2: #Do not export very small windows and doors to avoid errors
                ICEScript.write("((")
                ICEScript.write(str(-centre.x)) #Change direction 
                ICEScript.write(" ")
                ICEScript.write(str(-centre.y)) #Change direction 
                ICEScript.write(" ")
                ICEScript.write(str(centre.z))
                ICEScript.write(") (")
                #ICEScript.write(str(-nx))
                ICEScript.write(str(-normal.x)) #Change direction 
                ICEScript.write(" ")
                ICEScript.write(str(-normal.y)) #Change direction 
                ICEScript.write(" ")
                #ICEScript.write(str(ny))
                ICEScript.write(str(normal.z))
                if params[0] == "3":
                    ICEScript.write(") (AGGREGATE :T IFCIM_WINDOW :N ")
                elif params[0] == "4":
                    ICEScript.write(") (AGGREGATE :T IFCIM_DOOR :N ")
                ICEScript.write('"')
                ICEScript.write(str(ob.name))
                ICEScript.write('"')
                ICEScript.write(") (:PAR :N DY :V ")
                ICEScript.write(str(height))
                ICEScript.write(") (:PAR :N DX :V ")
                ICEScript.write(str(appwidth))
                ICEScript.write(") (:PAR :N STYLE :V ")
                ICEScript.write('"')
                ICEScript.write(panetype)
                ICEScript.write('"))'+ '\n')
        ICEScript.close()

        #Justera namnet som ev är väldigt långt
        # Read in the file
        if params[0] == "3":
            with open(str(params[1]) + 'ImportWindows.txt', 'r') as file :
                filedata = file.read()
                # Replace the target string
                filedata = filedata.replace("Objects.Geometry.Mesh -- ", "")
                # Write the file out again
                with open(str(params[1]) + 'ImportWindows.txt', 'w') as file:
                    file.write(filedata)
        elif params[0] == "4":
            with open(str(params[1]) + 'ImportDoors.txt', 'r') as file :
                filedata = file.read()
                # Replace the target string
                filedata = filedata.replace("Objects.Geometry.Mesh -- ", "")
                # Write the file out again
                with open(str(params[1]) + 'ImportDoors.txt', 'w') as file:
                    file.write(filedata)
    if params[0] == "5": #External objects
        ICEScript=open(str(params[1]) + 'ImportExternalObjects.txt','w')
        view_layer = bpy.context.view_layer
        obj_active = view_layer.objects.active
        selection = bpy.context.selected_objects
        bpy.ops.object.select_all(action='DESELECT')
        ICEScript.write('(:UPDATE [@]' +'\n')
        ICEScript.write('(:ADD (AGGREGATE :N ARCDATA)' + '\n')
            
        for obj in selection:
            obj.select_set(True)
            #Get Speckle category, type and family
            #Check if a name exists. We should also check if name is valid and unique
            custompropertyexists = bpy.data.objects[str(obj.name)].get('name') is not None
            if custompropertyexists == True:
                fn = (str(bpy.data.objects[str(obj.name)]['name']))
            elif custompropertyexists == False:
                fn = str(obj.name)
                
            fn = fn.replace('/', '_') #IFC-names can be invalid file names
            fnorg = fn
            fn = (str(params[1]) + str(fn)) #Get path
            fp = fn  + '.obj'
            print (fnorg)
            bpy.ops.export_scene.obj(filepath=fp, axis_forward='-Y', axis_up='Z', use_selection=True, check_existing=True)
            ICEScript.write('((AGGREGATE :N "' + fnorg + '" :T PICT3D)(:PAR :N FILE :V "' + fp + '")(:PAR :N TRANSPARENCY :V ' + str(params[2]) + ')(:PAR :N SHADOWING :V :' + str(params[3]) + '))' +'\n')

        ICEScript.write('))')
        ICEScript.close()
            
        view_layer.objects.active = obj_active

        for obj in selection:
            obj.select_set(True)

        #Ersätt  \ med \\
        # Read in the file
        with open(str(params[1]) + 'ImportExternalObjects.txt', 'r') as file :
          filedata = file.read()

        # Replace the target string
        filedata = filedata.replace("\\", "\\\\")

        # Write the file out again
        with open(str(params[1]) + 'ImportExternalObjects.txt', 'w') as file:
          file.write(filedata)

# == OPERATORS

class ICEBriddgeOperator(bpy.types.Operator):
    
    bl_idname = 'opr.ice_bridge_operator'
    bl_label = 'ICE Bridge'
    
    def execute(self, context):
        params = (
            context.scene.object,
            #context.scene.source,
            #context.scene.name,
            context.scene.path,
            context.scene.transparency,
            context.scene.shading,
        )
        export_object(params) 
        return {'FINISHED'}

# == PANELS
class ICEBridgePanel(bpy.types.Panel):
    
    bl_idname = 'ICE Bridge'
    bl_label = 'Objects to Export'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ICE Bridge"
    
    def draw(self, context):
        col = self.layout.column()
        for (prop_name, _) in PROPS:
            row = col.row()
            row = row.row()
            if prop_name == 'shading': #Show shading option if shading objects is choosen
                if context.scene.object == "5":
                    row.enabled = True
                if context.scene.object !=  "5":
                    row.enabled = False
            if prop_name == 'transparency':
                if context.scene.object == "5":
                    row.enabled = True
                if context.scene.object !=  "5":
                    row.enabled = False
            row.prop(context.scene, prop_name)
        col.operator('opr.ice_bridge_operator', text='Export to IDA ICE')


# == MAIN ROUTINE
CLASSES = [
    ICEBriddgeOperator,
    ICEBridgePanel,
]

def register():
    for (prop_name, prop_value) in PROPS:
        setattr(bpy.types.Scene, prop_name, prop_value)
    
    for klass in CLASSES:
        bpy.utils.register_class(klass)

def unregister():
    for (prop_name, _) in PROPS:
        delattr(bpy.types.Scene, prop_name)

    for klass in CLASSES:
        bpy.utils.unregister_class(klass)
        

if __name__ == '__main__':
    register()