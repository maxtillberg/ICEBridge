"""
[Blender and Python] Sending data to IDA ICE
Max Tillberg - Summer 2022-
Email: max.tillberg@equa.se
--------
Copyright (c) 2022-2024 Equa Simulation AB

Bugs:
    - Roof windows from IFC files have wrong height. Not sure why, OverallHeight seems wrong when exported. Hopefully fixed manually
    - Some windows from Speckle is not possible to select for export.
    - Coordinate systems can differ from IFC
Limitations:
    - 3D zone import is slow
To do in IDA ICE:
    - Make sure that zones and building bodies stays in insert position
    - That Windows imports after errors
    - Windows should be imported even if they do not fit in walls
    - Greater tollerance in normal direction for windows
    - CSV-export for all tables and H5-files
0.9.5
    -

To do in ICE Bridge:
    - Create IfcSpace from floor plan
    - Create stories from IFC
    - Create windows and doors from IFC
    
    - Delete given custom property for all objects
    - Read rooms from CSV
    - Read Point UDI from CSV
    - Create room shapes with API including custom parameters in the right position
    - Run API from ICEBridge
    - Create ICE sensors from Blender sensors
(:UPDATE [@]  ((SIMULATION_DATA :N SIMULATION_DATA)(:PAR :N MODEL-TYPE :V CLIMATE :S '(:DEFAULT NIL 2))))

(:UPDATE [@]  ((CE-ZONE :N "Zone")((ENCLOSING-ELEMENT :N FLOOR)(:ADD (ENCLOS-FEATURE :N "Sensor 1" :T SENSOR)(:PAR :N X :V 1.07)(:PAR :N Y :V 3.01)(:PAR :N Z :V 0.8)(:PAR :N SIGNAL :V POINTILLU)))))
    - Log sensors:
    (:UPDATE [@]
  (:PAR :N CONTROLLER :V "Sensorlog" :S '(:DEFAULT NIL 2)))

    - Create Blender sensors from point CSVs, right now bug in API
    - Create CSV from H5 in ICE 5, initially climate based daylight in a sperate Pyton process
    - Keep exsisting color scales, just change colors, text and values
    - Kolla följande kod: #height = (maximum(dimensionheight, calculatedheight))
    - Read and animate time series on sensors
    - Option to send shading OBJ- and 3DS-files as separate objects
    - Fix interface so only valid options are visible
    - Check for bugs
    - Bounding boxes should inherit name after boundid objects and possibly properties
    - Possibility to delete selected custom properties

    - Add Random string to ICEName
    - Fix add Text to ICEName regarding input field and if data missing (code in export)
    - Fix Add Text to ICEGroup if data missing

    - Create zone areas based upon meassuring planes

    - Check if script are fast enough for hudreds of zones, othewise make a new option, separate files, to trick the scripts

    - Read Lat, Long, direction and create sun path
    - Color sun path with data

    - Strech/inflate box until wall or slab
    - Geometry nodes: Read meshes with given property (IFCWall), Create UI, Create object with button, Rotate and move object with buttons, learn raycast,
    - Create planar surfaces from bounding boxes based upon largest surfaces

    - Refresh 3D with (refresh-pane (:call find-view-pane [@] 'three-d t)) after import of 3D object
    - Zoom extent at end of import scripts
    - Minimal bounding boxes for multiple selected objects

    - Create internal measuring planes from surfaces
    - Create external measuring planes from surfaces
    - Create sensors
    - Try to generate script for setting window frame for windows
    - Select transparent parts in IFC
    - Figuring out coordinate systems in IFC vs IDA ICE and speckle
    - Convert windows to doors and vice versa
    - Convert windows to wall parts and vice versa
    - Add IFCWall selection and ICEsellection for walls
    - Flatten more then one object, strange bug since you need to click interface
    - Adding features for DOTBIM
        - Zone names using custom object
        - New filters
    - Fast delete by using
        for ob in bpy.context.selected_objects:
            bpy.context.scene.objects.unlink(ob)
            if ob.users==0: ob.user_clear()
    - Figure out how to extrude floor to roof in Blender
    - Script for simplify remove holes in floors and clean
    - Select objects with alpha or at least an instruction how to do it, involves P in edit mode
    - Center insert for windows by default before export (should be done allready??)
    - Buttons instead of drop down for common features (surprisingly hard)
    - Create rooms out of faces
        bpy.ops.object.mode_set(mode = 'EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.edge_split()
        bpy.ops.mesh.separate(type='LOOSE')
        bpy.ops.object.mode_set(mode = 'OBJECT')
        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY')
    - Add tollerance for flattening roofs
    - Possible features: Help buttons, Clear temp folder, Create zones and building bodies from floor plans,
    - Change insert point for windows in z as mean value between max and min. Not rectangular windows will be places wrongly.
"""

bl_info = {
    # required
    'name': 'ICE Bridge',
    'blender': (3, 0, 0),
    'category': "3D View",
    #'category': 'Object',
    # optional
    'version': (0, 9, 5),
    'author': 'Max Tillberg',
    "doc_url": "https://github.com/maxtillberg/ICEBridge",
    'description': 'Export and scripting tool for IDA ICE',
}

import bpy #Used all the time
import bmesh #To clean meshes
import os #Reading and writing scripts
import glob #Used for finding the latest idm-file in temp folder
#import shutil #Needed to delete all files in folder
import subprocess #Needed to rut BAT-files
import mathutils
import math
import string #Used to randomize grouped shading objects
import random #Used to randomize grouped shading objects
import csv #Used to read CSV-files with result data
from mathutils import Matrix
from colorsys import hsv_to_rgb #Used for color scale
import numpy as np #Used for one of the bounding box alternatives
from mathutils import Vector
#IFC stuff, It would be nice to check if this is available
import ifcopenshell
#import ifcopenshell.util
#from ifcopenshell.util.selector import Selector
#selector = Selector()
import blenderbim.bim.import_ifc
import blenderbim.tool as tool
from blenderbim.bim.ifc import IfcStore
from ifcopenshell.util.selector import Selector #Needed to select LongNames in IfcSpaces
#from bpy.types import Operator, AddonPreferences #Used to save settings
import blenderbim.bim.module.boundary.operator #Needed to load space boundaries

from bpy.props import (StringProperty,
                       BoolProperty,
                       IntProperty,
                       FloatProperty,
                       FloatVectorProperty,
                       EnumProperty,
                       PointerProperty,
                       )
from bpy.types import (Panel,
                       Menu,
                       Operator,
                       PropertyGroup,
                       )
#import h5py
#import pandas as pd
#import numpy as np
#from datetime import datetime
#import statistics


#Message function for warnings
def ShowMessageBox(message = "", title = "Message Box", icon = 'INFO'):
    def draw(self, context):
        self.layout.label(text=message)
    bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)


# ------------------------------------------------------------------------
#    Scene Properties
# ------------------------------------------------------------------------

class MyICEProperties(PropertyGroup):

    objecttext: StringProperty(
        name = "Unit",
        description="Text describing object. Supports linebreaks and custom properties",
        default="W/m2 C",
        maxlen=256,
        )
    groupname: StringProperty(
        name = "Name",
        description="Name added or filtered to objects",
        default="",
        maxlen=256,
        )
    filtername: StringProperty(
        name = "String",
        description="String to search for",
        default="",
        maxlen=256,
        )
    my_runIDAICE: BoolProperty(
        name="Run script",
        description="Create a BAT-file and run the created script in selected IDA ICE-model",
        default = False
        )
    my_shadingbool: BoolProperty(
        name="Shading",
        description="If the exported objects should shade or not",
        default = True
        )
    my_transparency: IntProperty(
        name = "Transparency",
        description="Transparency of exported external object",
        default = 0,
        min = 0,
        max = 100
        )
    my_colortransparency: IntProperty(
        name = "Transparency",
        description="Transparency of Selected Color",
        default = 0,
        min = 0,
        max = 100
        )
    my_height: FloatProperty(
        name = "Height",
        description = "Height for Move and Extrude Operations",
        default = 3, #För negativa värden, använd extude och move
        )
    my_prismaticheight: FloatProperty(
        name = "Height",
        description="Height of created zone or building body.",
        default = 3,
    )
    my_minvalue: FloatProperty(
        name = "Min",
        description="Min value of custom property.",
        default = 0,
    )
    my_maxvalue: FloatProperty(
        name = "Max",
        description="Max value of custom property.",
        default = 100,
    )
    custompropertyname: StringProperty(
        name = "Property",
        description="Custom property name",
        default="DF",
        maxlen=256,
        )
    my_colorscale: EnumProperty(
        name="Colorscale",
        description="Color Scale",
        items=[ ('BLUERED', "Blue-Red", "Blue to Red"),
                ('GREENRED', "Green-Red", "Green to Red"),
                ('REDGREEN', "Red-Green", "Red to Green"),
                ('MAGENTARED', "Magenta-Red", "Magenta to Red"),
               ]
        )
    scriptfolder_path: StringProperty(
        name = "Scripts",
        description="Choose a directory to store temporarily script and geometry files in",
        default="C:\Temp\\",
        maxlen=1024,
        subtype='DIR_PATH'
        )
    externalobjetcsfolder_path: StringProperty(
        name = "Objects",
        description="Choose a directory to store external objects",
        default="C:\Temp\\",
        maxlen=1024,
        subtype='DIR_PATH'
        )
    IDAICEfolder_path: StringProperty(
        name = "IDA ICE",
        description="Path to the directory where IDA ICE is or should be located. This is only needed if Run IDA ICE is selected, the API is used or you save to idm",
        default="C:\Program Files (x86)\IDAICE48SP2\\",
        maxlen=1024,
        subtype='DIR_PATH'
        )
    IDAICEAPIfolder_path: StringProperty(
        name = "API",
        description="Path to the directory where IDA ICE API is located. This is only needed if the API is used",
        default="C:\Program Files (x86)\idaapi64\\",
        maxlen=1024,
        subtype='DIR_PATH'
        )
    model_path: StringProperty(
        name = "Model",
        description="Choose an IDA ICE model. This is only needed if Run IDA ICE is selected or if you write to idm. If no file is selected a new file will be created",
        default="C:\Temp\\building1.idm",
        maxlen=1024,
        subtype='FILE_PATH'
        )
    CSV_path: StringProperty(
        name = "CSV",
        description="Choose a CSV-file. This is used for reading result",
        default="result.csv",
        maxlen=1024,
        subtype='FILE_PATH'
        )
    H5_path: StringProperty(
        name = "H5",
        description="Choose a H5-file, name should not be changes since it determines content. DAYLIGHT-DF.h5 FIELD-3D.h5",
        default="FIELD-3D.h5",
        maxlen=1024,
        subtype='FILE_PATH'
        )
    IDAICETempfolder_path: StringProperty(
        name = "IDA ICE Temporary Folder",
        description="Path to the directory where temporary IDA ICE files are located. This is only needed if read result back from IDA ICE simulations",
        default="",
        maxlen=1024,
        subtype='DIR_PATH'
        )
    my_version: EnumProperty(
        name="IDA ICE version:",
        description="Choose what IDA ICE version to export to.",
        items=[ ('ICE48', "IDA ICE 4.8 or earlier", ""),
                #('ICE50', "IDA ICE 5.0 or later", ""),
               ]
        )
    my_filterlist: EnumProperty(
        name="Filter Objects:",
        description="Select property to filter object by",
        items=[ ('IFCSpace', "IFCSpace", "IFCSpace", 'MOD_WIREFRAME', 0),
                ('IFCSpaceLongName', "IFCSpaceLongName", "Part of Longname in IfcSpace. Case sensitive", 'MOD_WIREFRAME', 1),
                ('IFCWindow', "IFCWindow", "IFCWindow", 'MOD_LATTICE', 2),
                ('IFCDoor', "IFCDoor", "IFCDoor", 'MATPLANE', 3),
                ('Glazed', "Glazed", "Glazed", 'IMAGE_DATA', 4),
                ('Glass', "Glass", "Glass", 'IMAGE_DATA', 5),
                ('Panel', "Panel", "Panel", 'VIEW_ORTHO', 6),
                ('IFCWall', "IFCWall", "IFCWall", 'MOD_BUILD', 7),
                ('IFCRoof', "IFCRoof", "IFCRoof", 'LINCURVE', 8),
                ('IFCSite', "IFCSite", "IFCSite", 'WORLD', 9),
                ('IFCSlab', "IFCSlab", "IFCSlab", 'UGLYPACKAGE', 10),
                ('IFCFurnishing', "IFCFurnishing", "IFCFurnishing", 'ASSET_MANAGER', 11),
                ('Proxy', "Proxy", "Proxy", 'QUESTION', 12),
                ('Glas as material', "Glas as material", "Glas as material", 'IMAGE_DATA', 13),
                ('Windows', "Windows", "Speckle Windows collection", 'MOD_LATTICE', 14),
                ('Rooms', "Rooms", "Speckle Rooms collection", 'MOD_WIREFRAME', 15),
                ('Doors', "Doors", "Speckle Doors collection", 'MATPLANE', 16),
                ('Curtain Panels', "Curtain Panels", "Speckle Curtain Panels collection", 'VIEW_ORTHO', 17),
                ('Curtain Systems', "Curtain Systems", "Speckle Curtain Systems collection", 'VIEW_ORTHO', 18),
                ('Walls', "Walls", "Speckle Walls collection", 'MOD_BUILD', 19),
                ('Floors', "Floors", "Speckle Floors collection", 'REMOVE', 20),
                ('Grids', "Grids", "Speckle Grids collection", 'MOD_MULTIRES', 21),
                ('Stairs', "Stairs", "Speckle Stairs collection", 'NLA_PUSHDOWN', 22),
                ('Cailings', "Ceilings", "Speckle Ceilings collection", 'NOCURVE', 23),
                ('Railings', "Railings", "Speckle Railings collection", 'IPO_LINEAR', 24),
                ('ICEFloors', "ICEFloors", "ICEFloors", 'REMOVE', 25),
                ('ICERoofs', "ICERoofs", "ICERoofs", 'LINCURVE', 26),
                ('ICEWindows', "ICEWindows", "ICEWindows", 'MOD_LATTICE', 27),
                ('ICEDoors', "ICEDoors", "ICEDoors", 'MATPLANE', 28),
                ('ICEBuildingBodies', "ICEBuildingBodies", "ICEBuildingBodies", 'MESH_CUBE', 29),
                ('ICEZones', "ICEZones", "ICEZones", 'MOD_WIREFRAME', 30),
                ('ICEExternalObjects', "ICEExternalObjects", "ICEExternalObjects", 'SCENE_DATA', 31),
                ('Transparent', "Transparent objects", "Transparent Objects", 'MOD_WIREFRAME', 32),
                ('WindowsCatagory', "Windows as category", "ICEExternalObjects", 'IMAGE_DATA', 33),
                ('WindowFamily', "Single Windows as family", "Window as family", 'IMAGE_DATA', 33),
                ('CustomProperty', "Custom Property", "Containing custom property", 'PRESET', 34),
                ('IceScale', "Color scale", "Color scale created with ICEBridge", 'COLORSET_02_VEC', 35),
                ('Font', "Texts", "Text (fonts)", 'OUTLINER_OB_FONT', 36),
                ('PropertyType', "Property type name", "The name of custom type ", 'PRESET', 37),
               ]
        )
    my_colorlist: EnumProperty(
        name="Color",
        description="Color",
        items=[ ('Red', "Red", "Red"),
                ('Blue', "Blue", "Blue"),
                ('Green', "Green", "Green"),
                ('Pink', "Pink", "Pink"),
                ('Yellow', "Yellow", "Yellow"),
                ('White', "White", "White"),
                ('Orange', "Orange", "Orange"),
                ('Black', "Black", "Black"),
               ]
        )
    my_fileformatlist: EnumProperty(
        name="Format",
        description="Export file format",
        items=[ ('OBJ', "OBJ", "OBJ"),
                ('3DS', "3DS", "3DS"),
                ('idm', "idm", "idm"),
                ('Text', "Text", "Text"),
               ]
        )
    my_shapelist: EnumProperty(
        name="Shape",
        description="Shape of created object",
        items=[ ('Plane', "Plane", "Plane"),
                ('Cube', "Cube", "Cube"),
                ('Sphere', "Sphere", "Sphere"),
                ('Cylinder', "Cylinder", "Cylinder"),
               ]
        )
    my_size: FloatProperty(
        name = "Size",
        description = "Size",
        default = 0.5,
        )
    my_objectoperationlist: EnumProperty(
        name="Object operation:",
        description="Choose what operation to perform on selected objects.",
        items=[ ('CenterOfMass', "Set Origin to Center of Mass", "This is important to get midpoint of windows and doors correct", 'PIVOT_BOUNDBOX', 0),
                ('Isolate', "Isolate Selected Objects (Shift+H)", "Isolate Selected Objects", 'LIGHT_SUN', 1),
                ('Hide', "Hide Selected Objects (H)", "Hide Selected Objects", 'HIDE_ON', 2),
                ('Unhide', "Unhide Objects (Alt+H)", "Unhide Objects (Alt+H)", 'HIDE_OFF', 3),
                #('Show', "Show all Objects", "Show all Objects", 'HIDE_OFF', 3),
                ('Join', "Join Selected Objects (Ctrl+J)", "Join objects into the selected. Useful for complex building bodies, zones and external objects", 'OUTLINER_DATA_CURVE', 4),
                ('ColorObject', "Color Selected Object*", "Set Base Color and Transparency", 'COLORSET_01_VEC', 5),
                ('Duplicate', "Duplicate Selected Objects (Shift+D)", "Duplicate Selected Objects", 'DUPLICATE', 6),
                ('MoveToFilteredCollection', "Move to Filtered ICE Collection (M)", "Move to Filtered ICE Collection", 'FORWARD', 7),
                ('FlattenBottom', "Flatten Single Selected Object to Bottom*", "Flatten and Simplify Selected Objects to Lowest Selected Point. Sloping objects gets hoizontal and position is random within the object", 'ALIGN_BOTTOM', 8),
                ('FlattenMiddle', "Flatten Single Selected Object to Middle*", "Flatten and Simplify Selected Objects to Middle of Selected Points. Sloping objects gets hoizontal and position is random within the object", 'ALIGN_MIDDLE', 9),
                ('FlattenTop', "Flatten Single Selected Object to Top*", "Flatten and Simplify Selected Objects to Highest Selected Point. Sloping objects gets hoizontal and position is random within the object", 'ALIGN_TOP', 10),
                ('ExtrudeGivenDistance', "Extrude Selected Objects Given Distance**", "Extrude Selcted Objects Given Distance Z", 'EXPORT', 11),
                ('ExtrudeToGivenZ', "Extrude Selected Objects to Given Z**", "Extrude Selcted Faces to Given Height in Z", 'IMPORT', 12),
                ('MoveGivenZ', "Move Selected Objects Given Distance in Z", "Move Selected Objects Given Distance in Z", 'SORT_DESC', 13),
                ('MoveToGivenZ', "Move Selected Objects to Given Z", "Move Selected Objects to Given Z", 'SORT_ASC', 14),
                ('RemoveGaps', "Remove Gaps between Selected Zones***", "Extend zones to center of wall", 'MOD_BOOLEAN',15),
                ('DeleteAllLow', "Delete all but Highest on Selected Objects*", "Delete all vertices exempt highest. Can be used to flatten planar objects.", 'ALIGN_TOP', 16),
                ('DeleteAllHigh', "Delete all but Lowest on Selected Objects* ", "Delete all vertices exempt lowest. Can be used to flatten planar objects.", 'ALIGN_BOTTOM', 17),
                ('CreateCollections', "Create ICE Collection", "Create Default IDA ICE Collections.", 'COLLECTION_NEW', 18),
                ('FlattenRoof', "Flatten Complex*", "This will select all faces with a normal positive z value and delete the top vertices.", 'ALIGN_BOTTOM', 19),
                ('Union', "Union two closed Objects", "Union two closed objects. Note that this will leave the second inacts", 'SELECT_EXTEND', 20),
                ('Intersect', "Intersection of two closed Objects", "Create the differance vlume volume of two closed objects. Note that this will leave the second inacts", 'SELECT_INTERSECT', 21),
                ('Difference', "Remove Difference between two closed Objects", "Create the intersecting volume of two closed objects. Note that this will leave the second inacts", 'SELECT_SUBTRACT', 22),
                ('IFCStorey', "Create Planes from IFCStorey", "Create Planes at the same height at IFCStorey", 'REMOVE', 23),
                ('SortClockwise', "Sort vertices clockwise in selected objects", "Sort vertices clockwise. Important for zones and building bodies created from planes", 'MESH_DATA', 24),
                ('CeateBoundingBox', "Create bounding boxes around selected objects", "Useful for making windows", 'MOD_WIREFRAME', 25),
                ('CreateSingleBoundingBox', "Create a single bounding box around selected objects", "Oriented after objects", 'MOD_WIREFRAME', 26),
                ('CreateSingleBoundingBox2', "Create a single bounding box around selected objects 2", "Oriented after last selected object", 'MOD_WIREFRAME', 27),
                ('CreatePlanes', "Convert selected boxes to midpoint planes ", "Useful for windows. Slow command", 'MATPLANE', 28),
                ('MakeNonSelectable', "Make Selected Objects non Selectable", "", 'RESTRICT_SELECT_ON', 29),
                ('MakeAllSelectable', "Make All Objects Selectable", "", 'RESTRICT_SELECT_OFF', 30),
                ('AlignObject', "Align selected object based upon surfaces", "Most be run in edit mode. Selct two faces", 'MOD_TRIANGULATE', 31),
                ('RandomColor', "Give selected objects random color", "Give selected objects random color", 'COLORSET_02_VEC', 32),
                ('LoadcRelSpaceboundary', "Load IfcRelSpaceboundary", "Load IfcRelSpaceboundary", 'SHADING_BBOX', 33),
                ('SetICENametoIFCName', "Set ICEName to IFCName", "Set ICEName to IFCName", 'OUTLINER_OB_FONT', 34),
                ('SetICENametoIFCLongName', "Set ICEName to IFCLongName", "Set ICEName to IFCLongName", 'OUTLINER_OB_FONT', 35),
                ('SetIFCNametoCustomProperty', "Set IFCName to Custom Property", "Set IFCName Custom Property", 'OUTLINER_OB_FONT', 36),
                #('SetIFCNametoSpeckleCategory', "Set IFCName to Speckle Category", "Set IFCName to Speckle Category", 'OUTLINER_OB_FONT', 37),
                ('SetICEGrouptoIFCLongName', "Set ICEGroup to IFCLongName", "Set ICEGroup to IFCLongName", 'OUTLINER_OB_FONT', 38),
                ('SetICEGrouptoCustomProperty', "Set ICEGroup to Custom Property", "Set ICEGroup to ustom Property", 'OUTLINER_OB_FONT', 39),
                #('AddRandomstringtoICECategory', "Add Random string to ICEName", "Add Random string to ICEName", 'OUTLINER_OB_FONT', 40),
                ('AddTexttoICEName', "Add Text to ICEName", "Add Text to ICEName", 'OUTLINER_OB_FONT', 41),
                ('AddTexttoICEGroup', "Add Text to ICEGroup", "Add Text to ICEGroup", 'FONT_DATA', 42),
                ('ConvertFontToMesh', "Convert text to Mesh", "Convert text to Mesh. Useful for exporting to Speckle", 'OUTLINER_OB_FONT', 43),
                #('ImportRoomName', "Import room name", "Import room name and create text using the IDA ICE API. DO not forget to select an .idm-model", 'OUTLINER_OB_FONT', 43),
                ('ClearMaterials', "Clear Materials of selected objects", "Clear Materials of selected objects. Useful for IFC", 'COLORSET_13_VEC', 44),
                ('SetCustomICEName', "Set Custom ICEName", "Set Custom ICEName for selected objects", 'OUTLINER_OB_FONT', 45),
                ('SetCustomICEGroup', "Set Custom ICEGroup", "Set Custom ICEGroup for selected objects", 'OUTLINER_OB_FONT', 46),
               ]
        )

    my_exportobjectlist: EnumProperty(
        name="IDA ICE Script:",
        description="Choose what object type to export selected abojects as.",
        items=[ ('BuildingBodies', "Create Building bodies from volumes", "Volumes must be closed and made of planar surfaces. Each selected object will create one building body", 'HOME', 0),
                ('Zones', "Create Zones from volumes", "Volumes must be closed and made of planar surfaces. Each selected object will create one zone", 'MOD_WIREFRAME', 1),
                ('PrismaticBuildingBodies', "Create Building bodies from floor planes", "Lowest points will create floor, height is determined by difference. Each selected object will create one building body", 'HOME', 2),
                ('BuildingBodiesFromRoof', "Create Building bodies from roof planes", "Building body with complex roof. Each selected object will create one building body", 'HOME', 3),
                ('PrismaticZones', "Create Zones from floor planes", "Each selected object will create one zone", 'MESH_PLANE', 4),
                ('IfcSpacesFromFloor', "Create IfcSpaces from floor planes", "Each selected object will create one IfcSpac", 'MESH_PLANE', 5),
                ('BuildingBodiesAndZones', "Create Building bodies and Zones from volumes", "Volumes must be closed and made of planar surfaces. Each selected object will create one building body and one zone", 'SNAP_VOLUME', 6),
                ('Windows', "Create Windows from large surfaces", "Windows should be as planar as possible", 'MOD_LATTICE', 7),
                #('Windows2', "Create Windows from IFCWindows (-Y)", "Windows without large surfaces created by IFC, probably vertical", 'MOD_LATTICE', 7),
                #('Windows3', "Create Windows from IFCWindows (+Z)", "Windows without large surfaces created by IFC, probably sloping or horizontal", 'MOD_LATTICE', 8),
                #('ConvertZonesToWindows', "Convert Zone Group to Windows", "Windows from  bounding boxes. No IFC data transfered and stray windows may be created. Warning! This script should not be run in models with zones. All imported zones will be deleted and windows will be created in excisting zones.", 'MOD_LATTICE', 9),
                ('FillWallsWithWindows', "Fill external Zone walls with Windows", "Useful if zones or building bodies represent windows", 'MOD_LATTICE', 8),
                ('Doors', "Create Doors from large surfaces", "Doors should be as planar as possible", 'MATPLANE', 9),
                ('ExternalObjects', "Create External objects", "External objects can be shading and semitransparent. Group objects with similar properties.", 'SCENE_DATA', 10),
                ('DeleteBuildingBodies', "Delete Building bodies", "Useful since building bodies are created automaticly when zones from OBJ volumes are created", 'TRASH', 11),
                ('DeleteZones', "Delete Zones", "Useful for temporary zones", 'TRASH', 12),
                ('HideObject', "Hide External Object", "This scales the named objects and affects result", 'HIDE_ON', 13),
                ('ShowObject', "Show External Obects", "This scales the named objects and affects result", 'HIDE_OFF', 14),
                ('MoveWindowsToBuildingbodies', "Move Windows from Zones to Building bodies", "", 'TRACKING_FORWARDS_SINGLE', 15),
                ('MoveWindowsToZones', "Move Windows from Buildingbodies to Zones", "", 'TRACKING_BACKWARDS_SINGLE', 16),
                #('CreateBoundingBox', "Creating Bounding Box Building body", "Useful to avoid created objects in origo", 'SNAP_FACE_CENTER', 16),
                ('MoveZonesZ', "Move Zones Given Distance in Z", "Move Zones Given Distance in Z", 'SORT_DESC', 17),
                ('MoveBuildingBodiesZ', "Move Buiding Bodies Given Distance in Z", "Move Buiding Bodies Given Distance in Z", 'SORT_DESC', 18),
                ('CreateICESensors', "Create Sensors", "Based upon objects with ICEname", 'LIGHTPROBE_GRID', 19),
                #('RunHeatingLoadSimulation', "Run Heating load simulation", "Require special agreement with Equa to use", 'PLAY', 15),
               ]
        )
    my_postprocesslist: EnumProperty(
        name="Command:",
        description="Commands for post processing",
        items=[ #('CreatePointCSV', "Create Point CSV ", "Fom idm or H5. DF, Point Illuminance. Tricky, needs to be flexible and support different formats", 'MESH_CUBE', 0),
                #('CreateUDICSV', "Create Room CSV UDI from H5", "Create Room UDI from radiosity planes. CSV saved in temp folder.", 'MOD_WIREFRAME', 1),
                #('CreatePointCSV', "Create Point CSV from H5 and idm", "Create Room UDI from radiosity planes. CSV saved in temp folder.", 'MOD_WIREFRAME', 2),
                #('CreteRoomShape', "Create Room Shape from idm",  "Uses API", 'MESH_CUBE', 3),
                ##('CreateBuildingModel', "Crete Building Model", "Illustration to log systems and energy result upon", 'MESH_CUBE', 3),
                #('CreatePointsFromCSV', "Create Points from CSV", "Should contain header rom and the first coumns should be x,y,z. Other values will be stored as custom property with name according to header", 'LIGHTPROBE_GRID', 4),
                ##('CreateColorScale', "Create Color Scale", "Containing values, unit", 'SNAP_VOLUME', 5),
                #('ReadCSVData', "Read Point or Room Data from CSV", "Read data to object containing ICEName", 'DISC', 6),
                ##('ReadBuildingData', "Read building data", "This is read directly from IDM", 'MOD_LATTICE', 7),
                #('ColorAccordingToProperty', "Color Selected Objects According To Property", "Color scale, max, min, type", 'COLORSET_02_VEC', 8),
                #('TextAccordingToProperty', "Text Selected Objects According To Property", "Text According To Property", 'FILE_TEXT', 9),
                ##('AutoScaleColorScale', "Autoscale color scale", "Set min and max according to selected objects", 'FILE_TEXT', 10),
                #('CreateShapes', "Create Shapes from Selected Objects", "Create shapes from selected objects", 'MESH_CYLINDER', 11),
                #('AggregatePoints', "Aggregate Selected Points to New Shape", "Creates a new shape at median point with aggregated values", 'STICKY_UVS_LOC', 12),
                #('AggregatePoints2Zones', "Aggregate Points to Zones", "Saved to zones with aggregated values", 'STICKY_UVS_LOC', 13),
               ]
        )
    my_resultlist: EnumProperty(
        name="IDA ICE Result:",
        description="Select what result to read",
        items=[ ('GetHeat', "Get Max Heat", "Volumes must be closed and made of planar surfaces. Each selected object will create one building body", 'MESH_CUBE', 0),
               ]
        )

#Define util.py
pythoncode = "import ctypes" + '\n'
pythoncode = pythoncode + "import json" + '\n'
pythoncode = pythoncode + "import time" + '\n'
pythoncode = pythoncode + "import json" + '\n'
pythoncode = pythoncode + "import sys" + '\n'
pythoncode = pythoncode + "import os" + '\n' + '\n'
pythoncode = pythoncode + 'path_to_ice = "C:\\Program Files (x86)\\IDAICE48SP2\\bin\\"' + '\n'
pythoncode = pythoncode + 'command = path_to_ice + "ida-ice.exe \"" + path_to_ice + "ida.img\" -G 1"' + '\n'
pythoncode = pythoncode + "startObj = win32process.STARTUPINFO()" + '\n'
pythoncode = pythoncode + "ret = win32process.CreateProcess(None,command,None,None,0,0,None,None,startObj)" + '\n'
pythoncode = pythoncode + "pid = str(ret[2])" + '\n'
pythoncode = pythoncode + "time.sleep(5)" + '\n'
pythoncode = pythoncode + "os.environ['PATH'] = path_to_ice + os.pathsep  + os.environ['PATH']" + '\n'
pythoncode = pythoncode + "ida_lib = ctypes.CDLL('C:\\Program Files (x86)\\idaapi64\\idaapi2.dll')" + '\n'
pythoncode = pythoncode + "ida_lib.connect_to_ida.restype = ctypes.c_bool" + '\n'
pythoncode = pythoncode + "ida_lib.connect_to_ida.argtypes = [ctypes.c_char_p, ctypes.c_char_p]" + '\n'
pythoncode = pythoncode + "ida_lib.switch_remote_connection.restype = ctypes.c_bool" + '\n'
pythoncode = pythoncode + "ida_lib.switch_remote_connection.argtypes = [ctypes.c_char_p]" + '\n'
pythoncode = pythoncode + "ida_lib.switch_api_version.restype = ctypes.c_bool" + '\n'
pythoncode = pythoncode + "ida_lib.switch_api_version.argtypes = [ctypes.c_long]" + '\n'
pythoncode = pythoncode + "ida_lib.call_ida_function.restype = ctypes.c_long" + '\n'
pythoncode = pythoncode + "ida_lib.call_ida_function.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]" + '\n'
pythoncode = pythoncode + "ida_lib.ida_disconnect.restype = ctypes.c_bool" + '\n'
pythoncode = pythoncode + "ida_lib.ida_disconnect.argtypes = []" + '\n'
pythoncode = pythoncode + "ida_lib.get_err.restype = ctypes.c_long" + '\n'
pythoncode = pythoncode + "ida_lib.get_err.argtypes = [ctypes.c_char_p, ctypes.c_int]" + '\n'
pythoncode = pythoncode + "ida_lib.childNodes.restype = ctypes.c_long" + '\n'
pythoncode = pythoncode + "ida_lib.childNodes.argtypes = [ctypes.c_long, ctypes.c_char_p, ctypes.c_int]" + '\n'
pythoncode = pythoncode + "ida_lib.parentNode.restype = ctypes.c_long" + '\n'
pythoncode = pythoncode + "ida_lib.parentNode.argtypes = [ctypes.c_long, ctypes.c_char_p, ctypes.c_int]" + '\n'
pythoncode = pythoncode + "ida_lib.setParentNode.restype = ctypes.c_long" + '\n'
pythoncode = pythoncode + "ida_lib.setParentNode.argtypes = [ctypes.c_long, ctypes.c_long, ctypes.c_char_p, ctypes.c_int]" + '\n'
pythoncode = pythoncode + "ida_lib.hasChildNodes.restype = ctypes.c_long" + '\n'
pythoncode = pythoncode + "ida_lib.hasChildNodes.argtypes = [ctypes.c_long, ctypes.c_char_p, ctypes.c_int]" + '\n'
pythoncode = pythoncode + "ida_lib.firstChild.restype = ctypes.c_long" + '\n'
pythoncode = pythoncode + "ida_lib.firstChild.argtypes = [ctypes.c_long, ctypes.c_char_p, ctypes.c_int]" + '\n'
pythoncode = pythoncode + "ida_lib.lastChild.restype = ctypes.c_long" + '\n'
pythoncode = pythoncode + "ida_lib.lastChild.argtypes = [ctypes.c_long, ctypes.c_char_p, ctypes.c_int]" + '\n'
pythoncode = pythoncode + "ida_lib.nextSibling.restype = ctypes.c_long" + '\n'
pythoncode = pythoncode + "ida_lib.nextSibling.argtypes = [ctypes.c_long, ctypes.c_char_p, ctypes.c_int]" + '\n'
pythoncode = pythoncode + "ida_lib.previousSibling.restype = ctypes.c_long" + '\n'
pythoncode = pythoncode + "ida_lib.previousSibling.argtypes = [ctypes.c_long, ctypes.c_char_p, ctypes.c_int]" + '\n'
pythoncode = pythoncode + "ida_lib.childNodesLength.restype = ctypes.c_long" + '\n'
pythoncode = pythoncode + "ida_lib.childNodesLength.argtypes = [ctypes.c_long, ctypes.c_char_p, ctypes.c_int]" + '\n'
pythoncode = pythoncode + "ida_lib.setNodeValue.restype = ctypes.c_long" + '\n'
pythoncode = pythoncode + "ida_lib.setNodeValue.argtypes = [ctypes.c_long, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]" + '\n'
pythoncode = pythoncode + "ida_lib.cloneNode.restype = ctypes.c_long" + '\n'
pythoncode = pythoncode + "ida_lib.cloneNode.argtypes = [ctypes.c_long, ctypes.c_char_p, ctypes.c_int]" + '\n'
pythoncode = pythoncode + "ida_lib.insertBefore.restype = ctypes.c_long" + '\n'
pythoncode = pythoncode + "ida_lib.insertBefore.argtypes = [ctypes.c_long, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]" + '\n'
pythoncode = pythoncode + "ida_lib.createNode.restype = ctypes.c_long" + '\n'
pythoncode = pythoncode + "ida_lib.createNode.argtypes = [ctypes.c_long, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]" + '\n'
pythoncode = pythoncode + "ida_lib.contains.restype = ctypes.c_long" + '\n'
pythoncode = pythoncode + "ida_lib.contains.argtypes = [ctypes.c_long, ctypes.c_long, ctypes.c_char_p, ctypes.c_int]" + '\n'
pythoncode = pythoncode + "ida_lib.domAncestor.restype = ctypes.c_long" + '\n'
pythoncode = pythoncode + "ida_lib.domAncestor.argtypes = [ctypes.c_long, ctypes.c_long, ctypes.c_char_p, ctypes.c_int]" + '\n'
pythoncode = pythoncode + "ida_lib.item.restype = ctypes.c_long" + '\n'
pythoncode = pythoncode + "ida_lib.item.argtypes = [ctypes.c_long, ctypes.c_long, ctypes.c_char_p, ctypes.c_int]" + '\n'
pythoncode = pythoncode + "ida_lib.appendChild.restype = ctypes.c_long" + '\n'
pythoncode = pythoncode + "ida_lib.appendChild.argtypes = [ctypes.c_long, ctypes.c_long, ctypes.c_char_p, ctypes.c_int]" + '\n'
pythoncode = pythoncode + "ida_lib.removeChild.restype = ctypes.c_long" + '\n'
pythoncode = pythoncode + "ida_lib.removeChild.argtypes = [ctypes.c_long, ctypes.c_long, ctypes.c_char_p, ctypes.c_int]" + '\n'
pythoncode = pythoncode + "ida_lib.replaceChild.restype = ctypes.c_long" + '\n'
pythoncode = pythoncode + "ida_lib.replaceChild.argtypes = [ctypes.c_long, ctypes.c_long, ctypes.c_char_p, ctypes.c_int]" + '\n'
pythoncode = pythoncode + "ida_lib.setAttribute.restype = ctypes.c_long" + '\n'
pythoncode = pythoncode + "ida_lib.setAttribute.argtypes = [ctypes.c_char_p, ctypes.c_long, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]" + '\n'
pythoncode = pythoncode + "ida_lib.getAttribute.restype = ctypes.c_long" + '\n'
pythoncode = pythoncode + "ida_lib.getAttribute.argtypes = [ctypes.c_char_p, ctypes.c_long, ctypes.c_char_p, ctypes.c_int]" + '\n'
pythoncode = pythoncode + "ida_lib.openDocument.restype = ctypes.c_long" + '\n'
pythoncode = pythoncode + "ida_lib.openDocument.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]" + '\n'
pythoncode = pythoncode + "ida_lib.openDocByTypeAndName.restype = ctypes.c_long" + '\n'
pythoncode = pythoncode + "ida_lib.openDocByTypeAndName.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]" + '\n'
pythoncode = pythoncode + "ida_lib.saveDocument.restype = ctypes.c_long" + '\n'
pythoncode = pythoncode + "ida_lib.saveDocument.argtypes = [ctypes.c_long, ctypes.c_char_p, ctypes.c_long, ctypes.c_char_p, ctypes.c_int]" + '\n'
pythoncode = pythoncode + "ida_lib.runSimulation.restype = ctypes.c_long" + '\n'
pythoncode = pythoncode + "ida_lib.runSimulation.argtypes = [ctypes.c_long, ctypes.c_long, ctypes.c_char_p, ctypes.c_int]" + '\n'
pythoncode = pythoncode + "ida_lib.pollForQueuedResults.restype = ctypes.c_long" + '\n'
pythoncode = pythoncode + "ida_lib.pollForQueuedResults.argtypes = [ctypes.c_char_p, ctypes.c_int]" + '\n'
pythoncode = pythoncode + "ida_lib.getZones.restype = ctypes.c_long" + '\n'
pythoncode = pythoncode + "ida_lib.getZones.argtypes = [ctypes.c_long, ctypes.c_char_p, ctypes.c_int]" + '\n'
pythoncode = pythoncode + "ida_lib.getWindows.restype = ctypes.c_long" + '\n'
pythoncode = pythoncode + "ida_lib.getWindows.argtypes = [ctypes.c_long, ctypes.c_char_p, ctypes.c_int]" + '\n'
pythoncode = pythoncode + "ida_lib.getChildrenOfType.restype = ctypes.c_long" + '\n'
pythoncode = pythoncode + "ida_lib.getChildrenOfType.argtypes = [ctypes.c_long, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]" + '\n'
pythoncode = pythoncode + "ida_lib.findNamedChild.restype = ctypes.c_long" + '\n'
pythoncode = pythoncode + "ida_lib.findNamedChild.argtypes = [ctypes.c_long, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]" + '\n'
pythoncode = pythoncode + "ida_lib.exitSession.restype = ctypes.c_long" + '\n'
pythoncode = pythoncode + "ida_lib.exitSession.argtypes = [ctypes.c_char_p, ctypes.c_int]" + '\n'
pythoncode = pythoncode + "ida_lib.getAllSubobjectsOfType.restype = ctypes.c_long" + '\n'
pythoncode = pythoncode + "ida_lib.getAllSubobjectsOfType.argtypes = [ctypes.c_long, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]" + '\n'
pythoncode = pythoncode + "ida_lib.runIDAScript.restype = ctypes.c_long" + '\n'
pythoncode = pythoncode + "ida_lib.runIDAScript.argtypes = [ctypes.c_long, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]" + '\n'
pythoncode = pythoncode + "ida_lib.copyObject.restype = ctypes.c_long" + '\n'
pythoncode = pythoncode + "ida_lib.copyObject.argtypes = [ctypes.c_long, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]" + '\n'
pythoncode = pythoncode + "ida_lib.findObjectsByCriterium.restype = ctypes.c_long" + '\n'
pythoncode = pythoncode + "ida_lib.findObjectsByCriterium.argtypes = [ctypes.c_long, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]" + '\n'
pythoncode = pythoncode + "ida_lib.findUseOfResource.restype = ctypes.c_long" + '\n'
pythoncode = pythoncode + "ida_lib.findUseOfResource.argtypes = [ctypes.c_long, ctypes.c_char_p, ctypes.c_int]" + '\n'
pythoncode = pythoncode + "ida_lib.printReport.restype = ctypes.c_long" + '\n'
pythoncode = pythoncode + "ida_lib.printReport.argtypes = [ctypes.c_long, ctypes.c_char_p, ctypes.c_long, ctypes.c_char_p, ctypes.c_int]" + '\n'
pythoncode = pythoncode + "def ida_poll_results_queue (time_interval):" + '\n'
pythoncode = pythoncode + "  size = 5000" + '\n'
pythoncode = pythoncode + "  doc_str = ctypes.create_string_buffer(size) " + '\n'
pythoncode = pythoncode + "  poll_result = False" + '\n'
pythoncode = pythoncode + "  while poll_result == False:" + '\n'
pythoncode = pythoncode + "    time.sleep(time_interval)" + '\n'
pythoncode = pythoncode + "    poll_res = ida_lib.pollForQueuedResults(doc_str, len(doc_str))" + '\n'
pythoncode = pythoncode + '    poll_result2 = json.loads(doc_str.value.decode("utf-8"))' + '\n'
pythoncode = pythoncode + "    if isinstance(poll_result2, list):" + '\n'
pythoncode = pythoncode + "      poll_result = poll_result2[0]['value']" + '\n'
pythoncode = pythoncode + "    else:" + '\n'
pythoncode = pythoncode + '      return ""' + '\n' + '\n'
pythoncode = pythoncode + "  return poll_result2[1]['value']" + '\n'
pythoncode = pythoncode + "def call_ida_api_function (fun, *args):" + '\n'
pythoncode = pythoncode + '  "Just send in the function name and its unique arguments (not out buffer and out buffer length)" ' + '\n'
pythoncode = pythoncode + "  p = ctypes.create_string_buffer(5000)    " + '\n'
pythoncode = pythoncode + "  args = args + (p,len(p))" + '\n'
pythoncode = pythoncode + "  res = fun(*args)" + '\n'
pythoncode = pythoncode + "  if res == 0:" + '\n'
pythoncode = pythoncode + "    return ida_poll_results_queue(0.1)" + '\n'
pythoncode = pythoncode + "  else:" + '\n'
pythoncode = pythoncode + "    p = ctypes.create_string_buffer(res) " + '\n'
pythoncode = pythoncode + "    res = fun(*args)" + '\n'
pythoncode = pythoncode + "    if res == 0:" + '\n'
pythoncode = pythoncode + "      return ida_poll_results_queue(0.1)" + '\n'
pythoncode = pythoncode + "    else:" + '\n'
pythoncode = pythoncode + '      return ""' + '\n' + '\n'
pythoncode = pythoncode + "def call_ida_api_function_j (fun, *args):" + '\n'
pythoncode = pythoncode + '  "Just send in the function name and its unique arguments (not out buffer and out buffer length)" ' + '\n'
pythoncode = pythoncode + "  p = ctypes.create_string_buffer(5000)   " + '\n'
pythoncode = pythoncode + "  args = args + (p,len(p))" + '\n'
pythoncode = pythoncode + "  res = fun(*args)" + '\n'
pythoncode = pythoncode + "  if res == 0:" + '\n'
pythoncode = pythoncode + "    return p" + '\n'
pythoncode = pythoncode + "  else:" + '\n'
pythoncode = pythoncode + "    p = ctypes.create_string_buffer(res) " + '\n'
pythoncode = pythoncode + "    res = fun(*args)" + '\n'
pythoncode = pythoncode + "    if res == 0:" + '\n'
pythoncode = pythoncode + "      return p" + '\n'
pythoncode = pythoncode + "    else:" + '\n'
pythoncode = pythoncode + '      return ""' + '\n' + '\n'
pythoncode = pythoncode + "def ida_poll_results_queue_j (time_interval):" + '\n'
pythoncode = pythoncode + "  size = 5000" + '\n'
pythoncode = pythoncode + "  doc_str = ctypes.create_string_buffer(size) " + '\n'
pythoncode = pythoncode + "  poll_result = False" + '\n'
pythoncode = pythoncode + "  while poll_result == False:" + '\n'
pythoncode = pythoncode + "    time.sleep(time_interval)" + '\n'
pythoncode = pythoncode + "    poll_res = ida_lib.pollForQueuedResults(doc_str, len(doc_str))" + '\n'
pythoncode = pythoncode + '    poll_result2 = json.loads(doc_str.value.decode("utf-8"))' + '\n'
pythoncode = pythoncode + "    if isinstance(poll_result2, list):" + '\n'
pythoncode = pythoncode + "      poll_result = poll_result2[0]['value']" + '\n'
pythoncode = pythoncode + "    else:" + '\n'
pythoncode = pythoncode + '      return ""' + '\n'
pythoncode = pythoncode + "  return json.dumps(poll_result2[1])" + '\n' + '\n'
pythoncode = pythoncode + "def ida_get_named_child(par,name):" + '\n'
pythoncode = pythoncode + "  site_res = call_ida_api_function(ida_lib.findNamedChild,par, name.encode())" + '\n'
pythoncode = pythoncode + "  return site_res" + '\n' + '\n'
pythoncode = pythoncode + "def ida_get_value(par):" + '\n'
pythoncode = pythoncode + '  val = call_ida_api_function(ida_lib.getAttribute,b"VALUE", par)' + '\n'
pythoncode = pythoncode + "  return val" + '\n' + '\n'
pythoncode = pythoncode + "def ida_get_name(par):" + '\n'
pythoncode = pythoncode + '  val = call_ida_api_function(ida_lib.getAttribute,b"NAME", par)' + '\n'
pythoncode = pythoncode + "  return val" + '\n'

## ------------------------------------------------------------------------
##    Operators /Buttons to perform actions
## ------------------------------------------------------------------------
##Class to save settings
#class ExampleAddonPreferences(AddonPreferences):
#    # this must match the add-on name, use '__package__'
#    # when defining this in a submodule of a python package.
#    bl_idname = __name__
#    filepath: StringProperty(
#        name="Example File Path",
#        subtype='FILE_PATH',
#    )
#    def draw(self, context):
#        layout = self.layout
#        layout.label(text="This is a preferences view for our add-on")
#        layout.prop(self, "filepath")


#class WM_OT_LoadSaveSettings(Operator):
#    """Display example preferences"""
#    bl_idname = "object.addon_prefs_example"
#    bl_label = "Add-on Preferences Example"
#    bl_options = {'REGISTER', 'UNDO'}

#    def execute(self, context):
#        scene = context.scene
#        mytool = scene.my_tool
#        preferences = context.preferences
#        addon_prefs = preferences.addons[__name__].preferences

#        info = ("Path: %s, Number: %d, Boolean %r" %
#                (addon_prefs.filepath, addon_prefs.number, addon_prefs.boolean))

#        self.report({'INFO'}, info)
#        print(info)

#        return {'FINISHED'}

#class WM_OT_ClearScriptFolder(Operator):
#    bl_label = "Clear Script Folder"
#    bl_idname = "wm.clear_script_folder"
#    bl_description = "Delete all files in selected script folder"

#    def execute(self, context):
#        scene = context.scene
#        mytool = scene.my_tool

#        folder = str(bpy.path.abspath(mytool.scriptfolder_path))
#        if folder != "":
#            for filename in os.listdir(folder):
#                file_path = os.path.join(folder, filename)
#                try:
#                    if os.path.isfile(file_path) or os.path.islink(file_path):
#                        os.unlink(file_path)
#                    elif os.path.isdir(file_path):
#                        shutil.rmtree(file_path)
#                except Exception as e:
#                    print('Failed to delete %s. Reason: %s' % (file_path, e))
#        else:
#            ShowMessageBox("No script path selected", "Warning", 'ERROR')
#        return {'FINISHED'}

class WM_OT_SelectFilteredObjects(Operator):
    bl_label = "Select Filtered Objects"
    bl_idname = "wm.select_filtered_objects"
    bl_description = "Add filtered objects to selection"

    def execute(self, context):
        scene = context.scene
        mytool = scene.my_tool

        if mytool.my_filterlist == "IFCSpace":
            bpy.ops.object.select_pattern(pattern='*IFCSpace*')
        if mytool.my_filterlist == "IFCSpaceLongName":
            ifc = IfcStore.get_file() #Read the current ifc-file
            selector = Selector()
            spaces = selector.parse(ifc, '.IfcSpace[LongName *= "'+ str(mytool.filtername) +'"]')
            #spaces = selector.parse(ifc, '.IfcSpace[Category *= "'+ str(mytool.filtername) +'"]')
            #spaces = selector.parse(ifc, '.IfcSpace[IfcBuildingStorey *= "'+ str(mytool.filtername) +'"]')
            for space in spaces:
                obj = tool.Ifc.get_object(space)
                if obj:
                    obj.select_set(True)
        if mytool.my_filterlist == "CustomProperty":
            for obj in bpy.context.visible_objects:
                if str(mytool.filtername) in obj:
                #if str(mytool.filtername) in obj:
                    #if obj["category"] == str(mytool.filtername):
                    obj.select_set(True)
        if mytool.my_filterlist == "PropertyType":
            for obj in bpy.context.visible_objects:
                if "type" in obj:
                    if obj["type"] == str(mytool.filtername):
                        obj.select_set(True)
        if mytool.my_filterlist == "IFCWindow":
            bpy.ops.object.select_pattern(pattern='*IFCWindow*')
        if mytool.my_filterlist == "IFCDoor":
            bpy.ops.object.select_pattern(pattern='*IFCDoor*')
        if mytool.my_filterlist == "Glazed":
            bpy.ops.object.select_pattern(pattern='*Glazed*')
        if mytool.my_filterlist == "Glass":
            bpy.ops.object.select_pattern(pattern='*Glass*')
        if mytool.my_filterlist == "Panel":
            bpy.ops.object.select_pattern(pattern='*Panel*')
        if mytool.my_filterlist == "IFCWall":
            bpy.ops.object.select_pattern(pattern='*IFCWall*')
        if mytool.my_filterlist == "IFCRoof":
            bpy.ops.object.select_pattern(pattern='*IFCRoof*')
        if mytool.my_filterlist == "IFCSite":
            bpy.ops.object.select_pattern(pattern='*IFCSite*')
        if mytool.my_filterlist == "IFCSlab":
            bpy.ops.object.select_pattern(pattern='*IFCSlab*')
        if mytool.my_filterlist == "IFCFurnishing":
            bpy.ops.object.select_pattern(pattern='*IFCFurnishing*')
        if mytool.my_filterlist == "Proxy":
            bpy.ops.object.select_pattern(pattern='*Proxy*')
        if mytool.my_filterlist == "Glas as material":
            for obj in bpy.context.visible_objects:
                for m in obj.material_slots:
                    if "Glas" in m.name:
                        obj.select_set(True)
#                if bpy.data.objects[str(obj.name)]["category"]=="Windows":
#                    obj.select_set(True)
        if mytool.my_filterlist == "Windows":
            for obj in bpy.data.collections["Windows"].all_objects:
                obj.select_set(True)
        if mytool.my_filterlist == "Rooms":
            for obj in bpy.data.collections["Rooms"].all_objects:
                obj.select_set(True)
        if mytool.my_filterlist == "Doors":
            for obj in bpy.data.collections["Doors"].all_objects:
                obj.select_set(True)
        if mytool.my_filterlist == "Curtain Panels":
            for obj in bpy.data.collections["Curtain Panels"].all_objects:
                obj.select_set(True)
        if mytool.my_filterlist == "Curtain Systems":
            for obj in bpy.data.collections["Curtain Systems"].all_objects:
                obj.select_set(True)
        if mytool.my_filterlist == "Walls":
            for obj in bpy.data.collections["Walls"].all_objects:
                obj.select_set(True)
        if mytool.my_filterlist == "Floors":
            for obj in bpy.data.collections["Floors"].all_objects:
                obj.select_set(True)
        if mytool.my_filterlist == "Curtain Panels":
            for obj in bpy.data.collections["Curtain Panels"].all_objects:
                obj.select_set(True)
        if mytool.my_filterlist == "Grids":
            for obj in bpy.data.collections["Grids"].all_objects:
                obj.select_set(True)
        if mytool.my_filterlist == "Stairs":
            for obj in bpy.data.collections["Stairs"].all_objects:
                obj.select_set(True)
        if mytool.my_filterlist == "Ceilings":
            for obj in bpy.data.collections["Ceilings"].all_objects:
                obj.select_set(True)
        if mytool.my_filterlist == "Railings":
            for obj in bpy.data.collections["Railings"].all_objects:
                obj.select_set(True)
        if mytool.my_filterlist == "Transparent":
            for obj in bpy.data.collections["Transparent"].all_objects:
                obj.select_set(True)
        if mytool.my_filterlist == "WindowsCatagory":
            for obj in bpy.context.visible_objects:
                if "category" in obj:
                    if obj["category"] == "Windows":
                        obj.select_set(True)
        if mytool.my_filterlist == "WindowFamily":
            for obj in bpy.context.visible_objects:
                if "family" in obj:
                    if obj["family"] == "Single Windows":
                        obj.select_set(True)
        if mytool.my_filterlist == "CurtainWallFamily":
            for obj in bpy.context.visible_objects:
                if "family" in obj:
                    if obj["family"] == "Curtain Wall":
                        obj.select_set(True)
        if mytool.my_filterlist == "IceScale":
            bpy.ops.object.select_pattern(pattern='*IceScale*')
        if mytool.my_filterlist == "Font":
            item='EMPTY'
            #bpy.ops.object.select_all(action='DESELECT')
            bpy.ops.object.select_by_type(type="FONT")

        return {'FINISHED'}

class WM_OT_PerformOperation(Operator):
    bl_label = "Perform Operation"
    bl_idname = "wm.perform_operation"
    bl_description = "Perform selected operation on selected objects"

    def execute(self, context):
        scene = context.scene
        mytool = scene.my_tool
        if mytool.my_objectoperationlist == "CenterOfMass":
            selection = bpy.context.selected_objects
            for obj in selection:
               if obj.type=="MESH":
                    bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS')
        if mytool.my_objectoperationlist == "Isolate":
            bpy.ops.object.hide_view_set(unselected=True)
        if mytool.my_objectoperationlist == "Unhide":
            bpy.ops.object.hide_view_clear()
        if mytool.my_objectoperationlist == "Hide":
            selection = bpy.context.selected_objects
            for obj in selection:
                obj.hide_set(True)
        if mytool.my_objectoperationlist == "Join":
            selection = bpy.context.selected_objects
            obs = []
            for obj in selection:
                if obj.type == 'MESH':
                    obs.append(obj)
            ctx = bpy.context.copy()
            # one of the objects to join
            ctx['active_object'] = obs[0]
            ctx['selected_editable_objects'] = obs
            # We need the scene bases as well for joining.
            bpy.ops.object.join(ctx)

        if mytool.my_objectoperationlist == "RemoveGaps":
            #Code from https://github.com/IfcOpenShell/IfcOpenShell/commit/eb0f2de197c94e18d6eed83e56351e1c189e07ed#diff-7a3448a810418b98f5db644b11c1bf9ad0452c88545991ecc1eda3f65c929895
            threshold = 0.5
            processed_polygons = set()

            for obj in bpy.context.selected_objects:
                if obj.type != "MESH":
                    continue
                for polygon in obj.data.polygons:
                    center = obj.matrix_world @ polygon.center
                    distance = None
                    for obj2 in bpy.context.selected_objects:
                        if obj2 == obj or obj.type != "MESH":
                            continue
                        result = obj2.ray_cast(
                            obj2.matrix_world.inverted() @ center,
                            polygon.normal,
                            distance=threshold
                        )
                        if not result[0]:
                            continue
                        hit = obj2.matrix_world @ result[1]
                        distance = (hit - center).length / 2
                        if distance < 0.01:
                            distance = None
                            break

                        if (obj2.name, result[3]) in processed_polygons:
                            distance *= 2
                            continue

                        offset = polygon.normal * distance * -1
                        processed_polygons.add((obj2.name, result[3]))
                        for v in obj2.data.polygons[result[3]].vertices:
                            obj2.data.vertices[v].co += offset
                        break
                    if distance:
                        offset = polygon.normal * distance
                        processed_polygons.add((obj.name, polygon.index))
                        for v in polygon.vertices:
                            obj.data.vertices[v].co += offset
        if mytool.my_objectoperationlist == "CreateCollections":
            #Create standard IDA ICE collections
            if bpy.data.collections.get("ICEFloors") is None:
                collection = bpy.data.collections.new("ICEFloors")
                bpy.context.scene.collection.children.link(collection)
            if bpy.data.collections.get("ICERoofs") is None:
                collection = bpy.data.collections.new("ICERoofs")
                bpy.context.scene.collection.children.link(collection)
            if bpy.data.collections.get("ICEWindows") is None:
                collection = bpy.data.collections.new("ICEWindows")
                bpy.context.scene.collection.children.link(collection)
            if bpy.data.collections.get("ICEDoors") is None:
                collection = bpy.data.collections.new("ICEDoors")
                bpy.context.scene.collection.children.link(collection)
            if bpy.data.collections.get("ICEBuildingBodies") is None:
                collection = bpy.data.collections.new("ICEBuildingBodies")
                bpy.context.scene.collection.children.link(collection)
            if bpy.data.collections.get("ICEZones") is None:
                collection = bpy.data.collections.new("ICEZones")
                bpy.context.scene.collection.children.link(collection)
            if bpy.data.collections.get("ICEExternalObjects") is None:
                collection = bpy.data.collections.new("ICEExternalObjects")
                bpy.context.scene.collection.children.link(collection)
        if mytool.my_objectoperationlist == "ColorObject":
            transname = str(mytool.my_colortransparency/100)
            transvalue = 1 - (mytool.my_colortransparency/100)
            if str(mytool.my_colorlist) == "Red":
                tempname =  'Red' + transname
                matred = bpy.data.materials.new('Red' + transname)
                matred.diffuse_color = (1,0,0,transvalue)
                matred.specular_intensity = 0
                matred.roughness = 1
                for o in bpy.context.selected_objects:
                    # Set the active materials diffuse color to the specified RGB
                    o.active_material = matred
            if str(mytool.my_colorlist) == "Blue":
                # create the material
                matblue = bpy.data.materials.new('Blue' + transname)
                matblue.diffuse_color = (0,0,1,transvalue)
                matblue.specular_intensity = 0
                matblue.roughness = 1
                for o in bpy.context.selected_objects:
                    # Set the active materials diffuse color to the specified RGB
                    o.active_material = matblue
            if str(mytool.my_colorlist) == "Green":
                # create the material
                matgreen = bpy.data.materials.new('Green' + transname)
                matgreen.diffuse_color = (0,1,0,transvalue)
                matgreen.specular_intensity = 0
                matgreen.roughness = 1
                for o in bpy.context.selected_objects:
                    # Set the active materials diffuse color to the specified RGB
                    o.active_material = matgreen
            if str(mytool.my_colorlist) == "Pink":
                # create the material
                matpink = bpy.data.materials.new('Pink' + transname)
                matpink.diffuse_color = (1,0,0.7,transvalue)
                matpink.specular_intensity = 0
                matpink.roughness = 1
                for o in bpy.context.selected_objects:
                    # Set the active materials diffuse color to the specified RGB
                    o.active_material = matpink
            if str(mytool.my_colorlist) == "Yellow":
                # create the material
                matyellow = bpy.data.materials.new('Yellow' + transname)
                matyellow.diffuse_color = (1,1,0,transvalue)
                matyellow.specular_intensity = 0
                matyellow.roughness = 1
                for o in bpy.context.selected_objects:
                    # Set the active materials diffuse color to the specified RGB
                    o.active_material = matyellow
            if str(mytool.my_colorlist) == "White":
                # create the material
                matwhite = bpy.data.materials.new('White' + transname)
                matwhite.diffuse_color = (1,1,1,transvalue)
                matwhite.specular_intensity = 0
                matwhite.roughness = 1
                for o in bpy.context.selected_objects:
                    # Set the active materials diffuse color to the specified RGB
                    o.active_material = matwhite
            if str(mytool.my_colorlist) == "Orange":
                # create the material
                matorange = bpy.data.materials.new('Orange' + transname)
                matorange.diffuse_color = (1,0.3,0,transvalue)
                matorange.specular_intensity = 0
                matorange.roughness = 1
                for o in bpy.context.selected_objects:
                    # Set the active materials diffuse color to the specified RGB
                    o.active_material = matorange
            if str(mytool.my_colorlist) == "Black":
                # create the material
                matorange = bpy.data.materials.new('Black' + transname)
                matorange.diffuse_color = (0,0,0,transvalue)
                matorange.specular_intensity = 0
                matorange.roughness = 1
                for o in bpy.context.selected_objects:
                    # Set the active materials diffuse color to the specified RGB
                    o.active_material = matorange
        if mytool.my_objectoperationlist == "MoveToFilteredCollection":
            print(str(mytool.my_filterlist))
            #move duplicated objects to selected Collection
            C = bpy.context
            # List of object references
            objs = C.selected_objects
            # Set target collection to a known collection
            coll_target = C.scene.collection.children.get(str(mytool.my_filterlist))
            # If target found and object list not empty
            if coll_target and objs:
                # Loop through all objects
                for ob in objs:
                    # Loop through all collections the obj is linked to
                    for coll in ob.users_collection:
                        # Unlink the object
                        coll.objects.unlink(ob)
                    # Link each object to the target collection
                    coll_target.objects.link(ob)
        if mytool.my_objectoperationlist == "Duplicate":
            #Duplicate selected objects
            bpy.ops.object.duplicate()
            dupli_obj = bpy.context.object
        if mytool.my_objectoperationlist == "DeleteAllHigh" or mytool.my_objectoperationlist == "DeleteAllLow":
            C = bpy.context
            objs = C.selected_objects
            for ob in objs:
                print(ob.name)
                msh = bmesh.new()
                msh.from_mesh( ob.data )  # access the object mesh data
                msh.verts.ensure_lookup_table() # for coherency
                loc_vertex_coordinates = [ v.co for v in msh.verts ] # local coordinates of vertices
                # Find the lowest Z value amongst the object's verts
                minZ = min( [ co.z for co in loc_vertex_coordinates ] )
                maxZ = max( [ co.z for co in loc_vertex_coordinates ] )
                # Delete all vertices below maxZ (or above low)
                for v in msh.verts:
                    if mytool.my_objectoperationlist == "DeleteAllHigh":
                        if v.co.z > minZ:
                            print('remove',v,'at',v.co)
                            msh.verts.remove(v)
                    if mytool.my_objectoperationlist == "DeleteAllLow":
                        if v.co.z < maxZ:
                            print('remove',v,'at',v.co)
                            msh.verts.remove(v)
                msh.to_mesh(ob.data) # write the bmesh back to the mesh
                msh.free()  # free and prevent further access
                #Clean up
#                bpy.ops.mesh.delete(type='VERT')
#                bpy.ops.mesh.remove_doubles()
#                bpy.ops.mesh.dissolve_degenerate() #Clean som more
#                bpy.ops.mesh.edge_face_add() #Merge
        if mytool.my_objectoperationlist == "FlattenBottom" or mytool.my_objectoperationlist == "FlattenMiddle" or mytool.my_objectoperationlist == "FlattenTop":
            C = bpy.context
            objs = C.selected_objects
            for ob in objs:
                #mw = ob.matrix_world # Active object's world matrix
                loc_vertex_coordinates = [ v.co for v in ob.data.vertices ] # local coordinates of vertices
                # Find the lowest Z value amongst the object's verts
                minZ = min( [ co.z for co in loc_vertex_coordinates ] )
                maxZ = max( [ co.z for co in loc_vertex_coordinates ] )
                meanZ = (minZ + maxZ)/2
                if mytool.my_objectoperationlist == "FlattenBottom":
                    # Set Z for all vertices
                    for v in ob.data.vertices:
                        v.co.z = minZ
                if mytool.my_objectoperationlist == "FlattenMiddle":
                    # Set Z for all vertices
                    for v in ob.data.vertices:
                        v.co.z = meanZ
                if mytool.my_objectoperationlist == "FlattenTop":
                    # Set Z for all vertices
                    for v in ob.data.vertices:
                        v.co.z = maxZ
                if mytool.my_objectoperationlist == "FlattenBottom" or mytool.my_objectoperationlist == "FlattenMiddle" or mytool.my_objectoperationlist == "FlattenTop":
                    #Clean
                    if bpy.context.selected_objects != []:
                        if ob.type == 'MESH':
                            bpy.context.view_layer.objects.active = ob # obj is the active object now
                            bpy.ops.object.editmode_toggle()
                            bpy.ops.mesh.select_all(action='SELECT')
                            bpy.ops.mesh.remove_doubles()
                            bpy.ops.mesh.dissolve_degenerate() #Clean som more
                            bpy.ops.mesh.edge_face_add() #Merge
                            bpy.ops.object.editmode_toggle()
        if mytool.my_objectoperationlist == "ExtrudeGivenDistance":
            #Two alternative methods, move and solidify. Move edit out since it doeas not work very well
            bpy.ops.object.mode_set( mode   = 'EDIT'   )
            bpy.ops.mesh.select_mode( type  = 'FACE'   )
            bpy.ops.mesh.extrude_region_move(
                TRANSFORM_OT_translate={"value":(0, 0, mytool.my_height)} #Extrude in Z.
            )
            bpy.ops.object.editmode_toggle()

#            bpy.ops.object.modifier_add(type='SOLIDIFY')
#            bpy.context.object.modifiers["Solidify"].thickness = mytool.my_height
#            bpy.context.object.modifiers["Solidify"].offset = 1
#            bpy.ops.object.modifier_apply(modifier="Solidify")

        if mytool.my_objectoperationlist == "ExtrudeToGivenZ":
            ob = bpy.context.object
            ob.update_from_editmode()
            me = ob.data
            verts_sel = [v.co for v in me.vertices if v.select]
            pivot = sum(verts_sel, Vector()) / len(verts_sel)

            #print("Local:", pivot)
            Global = ob.matrix_world @ pivot
            #print("Global:", Global[2])

            bpy.ops.object.mode_set( mode   = 'EDIT'   )
            bpy.ops.mesh.select_mode( type  = 'FACE'   )
            bpy.ops.mesh.extrude_region_move(
                TRANSFORM_OT_translate={"value":(0, 0, Global[2] + mytool.my_height)} #Extrude in Z.
            )
            bpy.ops.object.editmode_toggle()

        if mytool.my_objectoperationlist == "MoveToGivenZ":
            obj = bpy.context.object
            # get the minimum z-value of all vertices after converting to global transform
            #lowest_pt = min([(obj.matrix_world @ v.co).z for v in obj.data.vertices])
            # transform the object
            obj.location.z = mytool.my_height
        if mytool.my_objectoperationlist == "MoveGivenZ":
            bpy.ops.transform.translate(value=(-0, -0, mytool.my_height), orient_axis_ortho='X', orient_type='GLOBAL', orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)), orient_matrix_type='GLOBAL', constraint_axis=(False, False, True), mirror=False, use_proportional_edit=False, proportional_edit_falloff='SMOOTH', proportional_size=1, use_proportional_connected=False, use_proportional_projected=False, release_confirm=True)

        if mytool.my_objectoperationlist == "Union" or mytool.my_objectoperationlist == "Difference" or mytool.my_objectoperationlist == "Intersect":
            # initialize the variables to work with, in this case two selected objects, in yours c1mesh and c2mesh
            first_object = bpy.context.selected_objects[0]
            second_object = bpy.context.selected_objects[1]

            # add the modifier and change settings
            first_object.modifiers.new(name = "Boolean", type = 'BOOLEAN')
            if mytool.my_objectoperationlist == "Union":
                first_object.modifiers.get("Boolean").operation = "UNION"
            if mytool.my_objectoperationlist == "Difference":
                first_object.modifiers.get("Boolean").operation = "DIFFERENCE"
            if mytool.my_objectoperationlist == "Intersect":
                first_object.modifiers.get("Boolean").operation = "INTERSECT"
            first_object.modifiers.get("Boolean").object = second_object

            # just cosmetic hiding of second object so you can instantly see the result
            second_object.hide_viewport = True
            #bpy.ops.bim.override_object_delete(confirm=True)
        if mytool.my_objectoperationlist == "IFCStorey":
            #Create store from IFC https://community.osarch.org/discussion/1047/blenderbim-create-faces-for-ifcbuildingstorey#latest
            ifc_file = ifcopenshell.open(IfcStore.path)
            products = ifc_file.by_type('IfcProduct')
            for ifcproduct in products:
                if ifcproduct:
                    if ifcproduct.is_a() == "IfcBuildingStorey":
                        x = (ifcproduct.ObjectPlacement.RelativePlacement.Location.Coordinates[0])
                        y = (ifcproduct.ObjectPlacement.RelativePlacement.Location.Coordinates[1])
                        z = (ifcproduct.ObjectPlacement.RelativePlacement.Location.Coordinates[2])
                        #print (x, y, z, ifcproduct.Elevation)
                        #print (ifcproduct.ObjectPlacement)
                        bpy.ops.mesh.primitive_plane_add(size=100, enter_editmode=False, align='WORLD', location=(x, y, (ifcproduct.Elevation)/1000), scale=(1, 1, 1))
                        bpy.context.active_object.name = str(ifcproduct.Name)
                        bpy.ops.bim.assign_class(ifc_class="IfcBuildingElementProxy", predefined_type="", userdefined_type="")
        if mytool.my_objectoperationlist == "SortClockwise":
            #This is a highly destructive operation that converts meshes to curves and back again. All faces will be lost
            # save and reset state of selection
            selected_objects = bpy.context.selected_objects
            #active_object = bpy.context.active_object
            for obj in selected_objects:
                #obj.select_set(False)
                if obj.type=="MESH":
                    bpy.ops.object.convert(target='CURVE', keep_original= False)
                    bpy.ops.object.convert(target='MESH', keep_original= False)
                    #print ('Kaele')
                    #obj.convert(target='CURVE', keep_original= False)
                    #obj.convert(target='MESH', keep_original= False)
#                context = bpy.context
#                distance = 0.01 # remove doubles tolerance.
#                if True: #def execute(self, context):
#                    meshes = set(o.data for o in context.selected_objects
#                                      if o.type == 'MESH')
#                    bm = bmesh.new()
#                    for m in meshes:
#                        bm.from_mesh(m)
#                        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=distance)
#                        bm.to_mesh(m)
#                        m.update()
#                        bm.clear()
#                    bm.free()
#                #Run this once again
#                bpy.ops.object.convert(target='CURVE', keep_original= False)
#                bpy.ops.object.convert(target='MESH', keep_original= False)
        if mytool.my_objectoperationlist == "RandomColor":
            selected = bpy.context.selected_objects
            for obj in selected:
                if obj.type=="MESH":
                    obj.data.materials.clear()
                    mat = bpy.data.materials.new('RandomColor')
                    randomred = random.uniform(0, 1)
                    randomgreen = random.uniform(0, 1)
                    randomblue = random.uniform(0, 1)
                    mat.diffuse_color = (randomred, randomgreen, randomblue, 1) # Or random colour, or cycled colours, etc
                    obj.data.materials.append(mat)
        if mytool.my_objectoperationlist == "LoadcRelSpaceboundary":
            loader = blenderbim.bim.module.boundary.operator.Loader() #Needed to load space boundaries
            for rel in tool.Ifc.get().by_type("IfcRelSpaceBoundary"):
                loader.load_boundary(rel, tool.Ifc.get_object(rel.RelatingSpace))
        if mytool.my_objectoperationlist == "ColorByIfcRelSpaceboundary":
            f = blenderbim.tool.Ifc.get()
            boundaries = f.by_type("IfcRelSpaceBoundary")
            for boundary in boundaries:
                obj = blenderbim.tool.Ifc.get_object(boundary)
                if not obj:
                    pass # load it in, or ignore? What's your usecase?
                obj.data.materials.clear()
                mat = bpy.data.materials.new('SpaceBoundaryColor')
                print (boundary)
                mat.diffuse_color = (1,0,0,1) # Or random colour, or cycled colours, etc
                obj.data.materials.append(mat)
        if mytool.my_objectoperationlist == "MakeNonSelectable":
            selected = bpy.context.selected_objects
            for obj in selected:
                if obj.type=="MESH":
                    obj.hide_select = True
        if mytool.my_objectoperationlist == "MakeAllSelectable":
            for obj in bpy.context.scene.collection.all_objects:
                obj.hide_select = False
        if mytool.my_objectoperationlist == "CeateBoundingBox":
            selected = bpy.context.selected_objects
            for obj in selected:
                #ensure origin is centered on bounding box center
                bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
                #create a cube for the bounding box
                bpy.ops.mesh.primitive_cube_add()
                #our new cube is now the active object, so we can keep track of it in a variable:
                bound_box = bpy.context.active_object
                #copy transforms
                bound_box.dimensions = obj.dimensions
                bound_box.location = obj.location
                bound_box.rotation_euler = obj.rotation_euler
                #Copy name and IFC info from windows and doors
        if mytool.my_objectoperationlist == "CreateSingleBoundingBox":
            #Source: https://blender.stackexchange.com/questions/274134/how-to-calculate-bounds-of-all-selected-objects-but-follow-the-active-objects-r?rq=1
            obj = bpy.context.object
            cube = get_cube_by_selected_objects()
            if cube is None:
                print("fail")
            else:
                copy_rot(cube, obj)
                create_lattice_by_cube(cube)
        if mytool.my_objectoperationlist == "CreateSingleBoundingBox2":
            #Source: https://blender.stackexchange.com/questions/274134/how-to-calculate-bounds-of-all-selected-objects-but-follow-the-active-objects-r?rq=1
            act_obj = bpy.context.object
            old_mode = act_obj.rotation_mode
            act_obj.rotation_mode = "QUATERNION"
            cube = get_box_by_selected_objects_with_vec_quaternion(bpy.context.object.rotation_quaternion)
            if cube is not None:
                copy_rot(cube, act_obj)
            act_obj.rotation_mode = old_mode
        if mytool.my_objectoperationlist == "SetICENametoIFCName":
            selected = bpy.context.selected_objects
            #We might need to check for contant
            for obj in selected:
                ifc_entity = tool.Ifc.get_entity(obj)
                obj["ICEName"] = str(ifc_entity.Name)
        if mytool.my_objectoperationlist == "SetICENametoIFCLongName":
            selected = bpy.context.selected_objects
            #We might need to check for contant
            for obj in selected:
                ifc_entity = tool.Ifc.get_entity(obj)
                obj["ICEName"] = str(ifc_entity.LongName)
        if mytool.my_objectoperationlist == "SetIFCNametoCustomProperty":
            selected = bpy.context.selected_objects
            #We might need to check for contant
            for obj in selected:
                obj["ICEName"] = str(obj[str(mytool.groupname)])
        if mytool.my_objectoperationlist == "SetICEGrouptoIFCLongName":
            selected = bpy.context.selected_objects
            #We might need to check for contant
            for obj in selected:
                ifc_entity = tool.Ifc.get_entity(obj)
                obj["ICEGroup"] = str(ifc_entity.LongName)
        if mytool.my_objectoperationlist == "SetICEGrouptoCustomProperty":
            #We might need to check for content
            selected = bpy.context.selected_objects
            for obj in selected:
                obj["ICEGroup"] = str(obj[str(mytool.groupname)])
        if mytool.my_objectoperationlist == "AddTexttoICEName":
            #We might need to check for content
            selected = bpy.context.selected_objects
            for obj in selected:
                obj["ICEName"] = str(obj["ICEName"]) + "_" + str(mytool.groupname)
        if mytool.my_objectoperationlist == "AddTexttoICEGroup":
            #We might need to check for content
            selected = bpy.context.selected_objects
            for obj in selected:
                obj["ICEGroup"] = str(obj["ICEGroup"]) + "_" + str(mytool.groupname)
        if mytool.my_objectoperationlist == "ConvertFontToMesh":
            selected = bpy.context.selected_objects
            for obj in selected:
                if obj.type == 'FONT':
                    bpy.ops.object.convert(target='MESH', keep_original=False)
        if mytool.my_objectoperationlist == "ClearMaterials":
            for obj in bpy.context.selected_editable_objects:
                obj.active_material_index = 0
                for i in range(len(obj.material_slots)):
                    bpy.ops.object.material_slot_remove({'object': obj})
        if mytool.my_objectoperationlist == "SetCustomICEName":
            selected = bpy.context.selected_objects
            for obj in selected:
                obj["ICEName"] = str(mytool.groupname)
        if mytool.my_objectoperationlist == "SetCustomICEGroup":
            selected = bpy.context.selected_objects
            for obj in selected:
                obj["ICEGroup"] = str(mytool.groupname)
        if mytool.my_objectoperationlist == "AlignObject":
            bpy.ops.object.mode_set(mode='EDIT')

            context = bpy.context
            scene = context.scene
            A = context.object

            A.select_set(state=False)
            B = bpy.context.selected_objects[0]
            A.select_set(state=True)

            #obj = context.edit_object (!) equal to A
            src_mw = A.matrix_world.copy()
            src_bm = bmesh.from_edit_mesh(A.data)
            src_face = src_bm.select_history.active
            src_o = src_face.calc_center_median()
            src_normal = src_face.normal
            src_tan = src_face.calc_tangent_edge()

            # This is the target, we change the sign of normal to stick face to face
            dst_mw = B.matrix_world.copy()
            dst_bm = bmesh.from_edit_mesh(B.data)
            dst_face = dst_bm.select_history.active
            dst_o = dst_face.calc_center_median()
            dst_normal = -(dst_face.normal)
            dst_tan = (dst_face.calc_tangent_edge())

            vec2 = src_normal @ src_mw.inverted()
            matrix_rotate = dst_normal.rotation_difference(vec2).to_matrix().to_4x4()

            vec1 = src_tan @ src_mw.inverted()
            dst_tan = dst_tan @ matrix_rotate.inverted()
            mat_tmp = dst_tan.rotation_difference(vec1).to_matrix().to_4x4()
            matrix_rotate = mat_tmp @ matrix_rotate
            matrix_translation = Matrix.Translation(src_mw @ src_o)

            # This line applied the matrix_translation and matrix_rotate
            B.matrix_world = matrix_translation @ matrix_rotate.to_4x4()

            # We need to recalculate these value since we change the matrix_world
            dst_mw = B.matrix_world.copy()
            dst_bm = bmesh.from_edit_mesh(B.data)
            dst_face = dst_bm.select_history.active
            dst_o = dst_face.calc_center_median()

            # The following is telling blender to find a translation from face center to origin,
            # And than apply it on world matrix
            # Be Careful, the order of the matrix multiplication change the result,
            # We always put the transform matrix on "Left Hand Side" to perform the task
            dif_mat = Matrix.Translation(B.location - dst_mw @ dst_o)
            B.matrix_world = dif_mat @ B.matrix_world
        if mytool.my_objectoperationlist == "CreatePlanes":
            selected = bpy.context.selected_objects
            for obj in selected:
                if obj.type=='MESH':
                    o = bpy.ops.object
                    m = bpy.ops.mesh
                    box = obj
                    box.select_set(True)
                    bpy.context.view_layer.objects.active = box
                    o.duplicate()
                    # plane at following line is actually the duplicated box
                    plane = bpy.context.active_object
                    faces = plane.data.polygons
                    # select all faces
                    o.mode_set(mode = 'EDIT')
                    m.select_mode(type='FACE')
                    m.select_all(action = 'SELECT')
                    o.mode_set(mode = 'OBJECT')
                    (x, y, z) = box.scale
                    # deselect the face you want to keep by largest area, xy = 0th face, xz = 1st face, yz = 2nd face
                    areas = [x*y, x*z, y*z]
                    faces[areas.index(max(areas))].select = False
                    # delete unwanted faces and set geometry to origin
                    o.mode_set(mode = 'EDIT')
                    m.delete(type='FACE')
                    o.mode_set(mode = 'OBJECT')
                    o.origin_set(type='GEOMETRY_ORIGIN', center='MEDIAN')
                    #box.select_set(True)
                    # give plane similar name
                    plane.name = box.name + '_Window'
                    objs = bpy.data.objects
                    objs.remove(box, do_unlink=True)
            #Delete stray empty meshes. not sure why these are created
            scene = bpy.context.scene
            empty_meshobs = [o for o in scene.objects
                if o.type == 'MESH'
                and not o.data.vertices]
            while empty_meshobs:
                bpy.data.objects.remove(empty_meshobs.pop())
        if mytool.my_objectoperationlist == "FlattenRoof":
            #Faltten roof, rather complex model, https://blender.stackexchange.com/questions/269822/flatten-roofs-into-inner-ceiling

            NORMAL_Z_THRESHOLD = 0.1
            MERGE_BY_DISTANCE_THRESHOLD = 0.025

            objects = bpy.context.view_layer.objects
            selected_objects = bpy.context.selected_objects

            if not objects.active.select_get() and len(selected_objects) > 0:
                objects.active = selected_objects[0]

            # ========================================================================================
            #
            # Starting in 3.2 context overrides are deprecated in favor of temp_override
            # https://docs.blender.org/api/3.2/bpy.types.Context.html#bpy.types.Context.temp_override
            #
            # They are scheduled to be removed in 3.3
            #
            # ========================================================================================

            def use_temp_override():
                ''' Determine whether Blender is 3.2 or newer and requires
                    the temp_override function, or is older and requires
                    the context override dictionary
                '''
                version = bpy.app.version
                major = version[0]
                minor = version[1]

                return not (major < 3 or (major == 3 and minor < 2))

            win = bpy.context.window
            scr = win.screen

            def get_areas(type):
                return [area for area in scr.areas if area.type == type]

            def get_regions(areas):
                return [region for region in areas[0].regions if region.type == 'WINDOW']

            def select_outer_edges():
                o = bpy.context.edit_object
                m = o.data
                bm = bmesh.from_edit_mesh(m)
                bm.select_mode |= {'EDGE'}
                for e in bm.edges:
                    e.select = e.is_boundary
                bm.select_flush_mode()
                m.update()

            def unselect_isolated_faces(bm):
                bm = bmesh.from_edit_mesh(o.data)

                for face in bm.faces:
                    if not face.select:
                        continue
                    no_selected_adj_faces = True
                    for e in face.edges:
                        for f in e.link_faces:
                            if not f is face:
                                no_selected_adj_faces = no_selected_adj_faces and not f.select

                    face.select = not no_selected_adj_faces

            def select_top_faces(o):
                bm = bmesh.from_edit_mesh(o.data)
                t = NORMAL_Z_THRESHOLD
                face_indices = []

                for f in bm.faces:
                    f.select = f.normal.z > t and ((f.normal.x + f.normal.y)*0.5 < 0)

                unselect_isolated_faces(bm)

                face_indices = [f.index for f in bm.faces if f.select]

                for f in bm.faces:
                    f.select = False

                for f in bm.faces:
                    f.select = f.index in face_indices

                for f in bm.faces:
                    f.select = f.normal.z > t and (-(f.normal.x + f.normal.y)*0.5 < 0)

                unselect_isolated_faces(bm)

                for f in bm.faces:
                    if f.index in face_indices:
                        f.select = True

            def process_object(o):

                areas  = get_areas('VIEW_3D')

                # ========================================================================================
                # (if) execute using temp override
                # ========================================================================================

                if use_temp_override():

                    with bpy.context.temp_override(window=win, area=areas[0], regions=get_regions(areas)[0], screen=scr):

                        bpy.ops.object.select_all(action='DESELECT')

                        o.select_set(True)
                        bpy.context.view_layer.objects.active = o

                        bpy.ops.object.editmode_toggle()
                        bpy.ops.mesh.select_all(action='SELECT')
                        bpy.ops.mesh.remove_doubles(threshold=MERGE_BY_DISTANCE_THRESHOLD)
                        bpy.ops.mesh.select_all(action='DESELECT')

                        select_top_faces(o)

                        bpy.ops.mesh.delete(type='VERT')
                        bpy.ops.mesh.select_all(action='SELECT')
                        bpy.ops.mesh.normals_make_consistent(inside=False)
                        bpy.ops.mesh.select_mode(type="EDGE")

                        select_outer_edges()

                        bpy.ops.mesh.select_mode(type="VERT")
                        bpy.ops.mesh.select_all(action='INVERT')
                        bpy.ops.mesh.dissolve_verts()
                        bpy.ops.object.editmode_toggle()

                # ========================================================================================
                # (else) execute using legacy override
                # ========================================================================================

                else:
                    override = {
                        'window': win,
                        'screen': scr,
                        'area': areas[0],
                        'region': get_regions(areas)[0],
                    }

                    bpy.ops.object.select_all(override, action='DESELECT')

                    o.select_set(True)
                    bpy.context.view_layer.objects.active = o

                    bpy.ops.object.editmode_toggle(override)
                    bpy.ops.mesh.select_all(override, action='SELECT')
                    bpy.ops.mesh.remove_doubles(override, threshold=MERGE_BY_DISTANCE_THRESHOLD)
                    bpy.ops.mesh.select_all(override, action='DESELECT')

                    select_top_faces(o)

                    bpy.ops.mesh.delete(override, type='VERT')
                    bpy.ops.mesh.select_all(override, action='SELECT')
                    bpy.ops.mesh.normals_make_consistent(override, inside=False)
                    bpy.ops.mesh.select_mode(override, type="EDGE")

                    select_outer_edges()

                    bpy.ops.mesh.select_mode(override, type="VERT")
                    bpy.ops.mesh.select_all(override, action='INVERT')
                    bpy.ops.mesh.dissolve_verts(override)
                    bpy.ops.object.editmode_toggle(override)

            # ========================================================================================
            # execute script
            # ========================================================================================

            list = [o for o in selected_objects]

            for o in list:
                if not o.type == 'MESH':
                    continue

                process_object(o)

            for o in list:
                o.select_set(True)

        return {'FINISHED'}

class WM_OT_Export(Operator):
    bl_label = "Create Script"
    bl_idname = "wm.ice_export_script"
    bl_description = "Create script and optional OBJ and BAT-files"

    def execute(self, context):
        ifc_data = IfcStore.get_file()
        scene = context.scene
        mytool = scene.my_tool
        objectlist = []
        #Use fixed script names based upon object type
        if mytool.my_exportobjectlist == "BuildingBodies":
            scriptname = "ImportBuildingBodies"
        if mytool.my_exportobjectlist == "Zones":
            scriptname = "ImportZones"
        if mytool.my_exportobjectlist == "PrismaticBuildingBodies":
            scriptname = "ImportBuildingBodies"
        if mytool.my_exportobjectlist == "PrismaticZones":
            scriptname = "ImportZones"
        if mytool.my_exportobjectlist == "IfcSpacesFromFloor":
            scriptname = "ImportZones"
        if mytool.my_exportobjectlist == "BuildingBodiesFromRoof":
            scriptname = "ImportBuildingBodies"
        if mytool.my_exportobjectlist == "BuildingBodiesAndZones":
            scriptname = "ImportBuildingBodiesAndZones"
        if mytool.my_exportobjectlist == "Windows":
            scriptname = "ImportWindows"
#        if mytool.my_exportobjectlist == "Windows2":
#            scriptname = "ImportWindows"
#        if mytool.my_exportobjectlist == "Windows3":
#            scriptname = "ImportWindows"
#        if mytool.my_exportobjectlist == "ConvertZonesToWindows":
#            scriptname = "ImportWindows"
        if mytool.my_exportobjectlist == "Doors":
            scriptname = "ImportDoors"
        if mytool.my_exportobjectlist == "ExternalObjects":
            scriptname = "ImportExternalObjects"
        if mytool.my_exportobjectlist == "MoveWindowsToBuildingbodies":
            scriptname = "ICEScript"
        if mytool.my_exportobjectlist == "MoveWindowsToZones":
            scriptname = "ICEScript"
        #if mytool.my_exportobjectlist == "CreateBoundingBox":
        #    scriptname = "ICEScript"
        if mytool.my_exportobjectlist == "FillWallsWithWindows":
            scriptname = "ICEScript"
        if mytool.my_exportobjectlist == "DeleteBuildingBodies":
            scriptname = "ICEScript"
        if mytool.my_exportobjectlist == "DeleteZones":
            scriptname = "ICEScript"
        if mytool.my_exportobjectlist == "HideObject":
            scriptname = "ICEScript"
        if mytool.my_exportobjectlist == "ShowObject":
            scriptname = "ICEScript"
        if mytool.my_exportobjectlist == "RunHeatingLoadSimulation":
            scriptname = "ICEScript"
        if mytool.my_exportobjectlist == "MoveBuildingBodiesZ":
            scriptname = "ICEScript"
        if mytool.my_exportobjectlist == "MoveZonesZ":
            scriptname = "ICEScript"
        #Open a script file to write to, make sure that there are a path selected
        if mytool.scriptfolder_path == "":
            ShowMessageBox("Script folder path is missing", "Warning", 'ERROR')
            return {'FINISHED'}
        if mytool.externalobjetcsfolder_path == "" and mytool.my_exportobjectlist == "ExternalObjects":
            ShowMessageBox("External objects folder path is missing", "Warning", 'ERROR')
            return {'FINISHED'}
            #ShowMessageBox("Script folder path is missing")
            #ShowMessageBox("This is a message", "This is a custom title")
        ICEScript = open(str(bpy.path.abspath(mytool.scriptfolder_path)) + '\\' + scriptname + '.txt','w')
        #Pure IDA ICE Scripts
        if mytool.my_exportobjectlist == "MoveWindowsToBuildingbodies":
            ICEScript.write('(:UPDATE [@]' + '\n' + "(:call mapcar 'zone-windows-to-face [@ :zones]))")
            ICEScript.close()
        if mytool.my_exportobjectlist == "MoveWindowsToZones":
            ICEScript.write('(:UPDATE [@]' + '\n' + "(:call mapcar 'face-windows-to-zone [@ :zones]))")
            ICEScript.close()
        #if mytool.my_exportobjectlist == "CreateBoundingBox":
        #    #Create building body 1000*1000*100 m
        #    ICEScript.write('(:UPDATE [@]' + '\n' + '(:ADD (CE-SECTION :N "Bounding box' + str(mytool.groupname) + '" :T BUILDING-SECTION :D "Building body")(:PAR :N NCORN :V 4)(:PAR :N CORNERS :DIM (4 2) :V #2A((-1000 1000) (1000 1000) (1000 -1000) (-1000 -1000)))(:PAR :N HEIGHT :V 100)))')
        #    ICEScript.close()
        if mytool.my_exportobjectlist == "FillWallsWithWindows":
            #Right no 100%, could be impoved with variable area
            ICEScript.write('(:for (w [@ :ice-all-enclosing] :when (<= 90 [w geometry slope] 179) ) (add-band-feature w 1 0 window) )')
            ICEScript.close()
        if mytool.my_exportobjectlist == "DeleteZones":
            ICEScript.write('(:UPDATE [@ :BUILDING](:FOR (Z_ [@ :ZONES] :WHEN (:CALL SEARCH "' + str(mytool.groupname) + '" (:CALL NAME Z_)))(:REMOVE (:CALL NAME Z_))))')
            ICEScript.close()
        if mytool.my_exportobjectlist == "DeleteBuildingBodies":
            ICEScript.write('(:UPDATE [@ :BUILDING](:FOR (B_ [@ :SECTIONS] :WHEN (:CALL SEARCH "' + str(mytool.groupname) + '" (:CALL NAME B_)))(:REMOVE (:CALL NAME B_))))')
            ICEScript.close()
        if mytool.my_exportobjectlist == "MoveBuildingBodiesZ":
            ICEScript.write('(:FOR (B_ (:CALL :SECTIONS [@ :BUILDING]) :WHEN (:CALL SEARCH "' + str(mytool.groupname) + '"' + " (:CALL NAME B_)))(:SET dz_ " + str(mytool.my_prismaticheight) + ")(:SET h_old [B_ 'HEIGHT])(:SET b_old [B_ 'BOTTOM])(:CALL SET-VALUE B_ 'HEIGHT (+ dz_ h_old))(:CALL SET-VALUE B_ 'BOTTOM (+ dz_ b_old)))")
            ICEScript.close()
        if mytool.my_exportobjectlist == "MoveZonesZ":
            ICEScript.write('(:FOR (Z_ [@ :ZONES] :WHEN (:CALL SEARCH "' + str(mytool.groupname) + '" (:CALL NAME Z_)))(:SET dz_ ' + str(mytool.my_prismaticheight) + ')(:SET h_old [z_ Geometry FLOOR_HEIGHT_FROM_GROUND])(:UPDATE Z_((AGGREGATE :N GEOMETRY)(:PAR :N FLOOR_HEIGHT_FROM_GROUND :V (+ dz_ h_old)))))')
            ICEScript.close()
        if mytool.my_exportobjectlist == "HideObject":
            ICEScript.write('(:FOR (A_ (:CALL CONTENTS [[@ :BUILDING] ARCDATA]) :WHEN (:CALL SEARCH "' + str(mytool.groupname) + '" (:CALL NAME A_)))(:UPDATE [@ :BUILDING]((AGGREGATE :N ARCDATA)((AGGREGATE :N (:CALL NAME A_))(:PAR :N SCALE :V 0)))))')
            ICEScript.close()
        if mytool.my_exportobjectlist == "ShowObject":
            ICEScript.write('(:FOR (A_ (:CALL CONTENTS [[@ :BUILDING] ARCDATA]) :WHEN (:CALL SEARCH "' + str(mytool.groupname) + '" (:CALL NAME A_)))(:UPDATE [@ :BUILDING]((AGGREGATE :N ARCDATA)((AGGREGATE :N (:CALL NAME A_))(:PAR :N SCALE :V 1)))))')
            ICEScript.close()
        if mytool.my_exportobjectlist == "PrismaticBuildingBodies" or mytool.my_exportobjectlist == "PrismaticZones" or mytool.my_exportobjectlist == "IfcSpacesFromFloor":
            #Depending on format, write diffrent file or give warnning, none is not valid
            if str(mytool.my_fileformatlist) == "OBJ" or str(mytool.my_fileformatlist) == "3DS":
                ShowMessageBox("Not valid export format", "Warning", 'ERROR')
                ICEScript.close()
                return {'FINISHED'}
            if str(mytool.my_fileformatlist) == "idm":
                ICEScript.close() #Close and replace script file with idm-file
                #Check if there are an exsisting idm-file, otherwise create one.
                ICEScript = str(bpy.path.abspath(mytool.model_path))
                filepath = os.path.dirname(str(mytool.model_path))
                print (filepath)
                filename = os.path.splitext(os.path.basename(str(mytool.model_path)))[0]
                tempheader = ";IDA 4.80002 Data UTF-8"  + '\n'
                tempheader = tempheader + "(DOCUMENT-HEADER :TYPE BUILDING :N " + '"' + filename + '"' + " :PARENT ICE :APP (ICE :VER 4.802))" + '\n'
                if os.path.exists(ICEScript): #File exsists
                    if os.path.getsize(ICEScript) > 0: #File contains data
                        textchars = bytearray([7,8,9,10,12,13,27]) + bytearray(range(0x20, 0x7f)) + bytearray(range(0x80, 0x100))
                        is_binary_string = lambda bytes: bool(bytes.translate(None, textchars))
                        if is_binary_string(open(ICEScript, 'rb').read(1024)): #File is packed (binry)
                            ShowMessageBox("Selected idm-file must be unpacked", "Warning", 'ERROR')
                            #ICEScript.close()
                            return {'FINISHED'}
                        else:
                            ICEScript = open(str(ICEScript), 'a')
                    else: #File contains no data
                        #Write header
                        ICEScript = open(str(ICEScript), 'a') #Apend code
                        ICEScript.write(tempheader)
                else:
                    #Create file and write header
                    ICEScript = open(str(ICEScript), 'a') #Apend code
                    ICEScript.write(tempheader)
            if str(mytool.my_fileformatlist) == "Text" or str(mytool.my_fileformatlist) == "idm":
                if str(mytool.my_fileformatlist) == "Text":
                    ICEScript.write('(:UPDATE [@]' +'\n')
                #If IFCSpaces are created, crate IFC
                if mytool.my_exportobjectlist == "IfcSpacesFromFloor":
                    ICEScript.write('  ((AGGREGATE :N ARCDATA)' +'\n')
                    ICEScript.write('   (AGGREGATE :N MAPPING :T IFCIM_MAPPING)' +'\n')
                    ICEScript.write('   ((IFCIM_STOREY :N "IFCtemplate" :T IFCIM_STOREY)' +'\n')
                    ICEScript.write("    (:PAR :N HMIN :T LENGTH :U |m| :V -1000 :KV FREAL :S '(:DEFAULT NIL 2))" +'\n')
                    ICEScript.write("    (:PAR :N HMAX :T LENGTH :U |m| :V 1000 :KV FREAL :S '(:DEFAULT NIL 2))" +'\n')
                    ICEScript.write("    (:PAR :N LEVELS :T LENGTH :U |m| :V (0 ") #Allways add one floor on z=0
                    #Create store from IFC https://community.osarch.org/discussion/1047/blenderbim-create-faces-for-ifcbuildingstorey#latest
                    #Add floors according to IFC, hopefully this will be the same as zones
                    ifc_file = ifcopenshell.open(IfcStore.path)
                    products = ifc_file.by_type('IfcProduct')
                    for ifcproduct in products:
                        if ifcproduct:
                            if ifcproduct.is_a() == "IfcBuildingStorey":
                                ICEScript.write(str((ifcproduct.Elevation / 1000)) + " ")
                    ICEScript.write(") :S '(:DEFAULT NIL 2))" +'\n')
                #Create zones or building bodies based upon a series of points at lowest
                C = bpy.context
                objs = C.selected_objects
                if mytool.my_exportobjectlist == "PrismaticZones" and str(mytool.my_fileformatlist) == "idm":
                    #Create subfolder if not existing
                    print (filepath + "//" + filename)
                    if not os.path.exists(filepath + "//" + filename):
                        os.makedirs(filepath + "//" + filename)
                for ob in objs:
                    if ob.type!="MESH":
                        ShowMessageBox("Selected idm-file must be unpacked", "Warning", 'ERROR')
                        #ICEScript.close()
                        return {'FINISHED'}
                    fn = str(ob.name)
                    #Replace long Speckle names
                    fn = fn.replace("Objects.Geometry.Mesh -- ", "")
                    fn = fn.replace('/', '_') #Speckle-names can be invalid file names
                    fn = fn.replace(':', '_') #Speckle-names can be invalid file names
                    fn = fn.replace('.', '_') #Speckle-names can be invalid file names
                    #If ICEName Exsists, use that instead. We asume that it is valid
                    custompropertyexists = bpy.data.objects[str(ob.name)].get('ICEName') is not None
                    if custompropertyexists == True:
                        fn = (str(bpy.data.objects[str(ob.name)]['ICEName']))
                    if mytool.my_exportobjectlist == "IfcSpacesFromFloor":
                        ICEScript.write('    ((AGGREGATE :N "')
                        ICEScript.write(fn + str(mytool.groupname))
                        ICEScript.write('" :T IFCIM_SPACE :D NIL)' +'\n')
                        ICEScript.write('     (:PAR :N ID :V "')
                        ICEScript.write(fn + str(mytool.groupname))
                        ICEScript.write('")' +'\n')
                        ICEScript.write("     (:PAR :N GROUP :S '(:DEFAULT NIL 2))" +'\n')
                    if mytool.my_exportobjectlist == "PrismaticZones":
                        if str(mytool.my_fileformatlist) == "Text":
                            ICEScript.write('(:ADD (CE-ZONE :N "')
                            ICEScript.write(fn + str(mytool.groupname))
                        if str(mytool.my_fileformatlist) == "idm":
                            #Create  file or overwrite exsisting
                            #Write header
                            TempZoneFolder = open(filepath + '\\' + filename + "\\" + fn + ".idm", 'w') #Overwrite
                            TempZoneFolder.write(';IDA 4.80002 Data UTF-8' + '\n')
                            TempZoneFolder.write('(DOCUMENT-HEADER :TYPE ZONE :APP (ICE :VER 4.802)) ' + '\n')
                            #TempZoneFolder.write('((CE-ZONE :N "')
                            #TempZoneFolder.write(fn + str(mytool.groupname))
                            ICEScript.write('((CE-ZONE :N "')
                            ICEScript.write(fn + str(mytool.groupname))
                    if mytool.my_exportobjectlist == "PrismaticBuildingBodies":
                        if str(mytool.my_fileformatlist) == "Text":
                            ICEScript.write('(:ADD ')
                        if str(mytool.my_fileformatlist) == "idm":
                            ICEScript.write('(')
                        ICEScript.write('(CE-SECTION :N "')
                        ICEScript.write(fn  + str(mytool.groupname) + "bb") #Add bb to name to avoid colliding names
                    if mytool.my_exportobjectlist == "PrismaticZones":
                        if str(mytool.my_fileformatlist) == "Text":
                            ICEScript.write('" :T ZONE)' +'\n')
                        if str(mytool.my_fileformatlist) == "idm":
                            #TempZoneFolder.write('" :T ZONE)' +'\n')
                            ICEScript.write('" :T ZONE))' +'\n')
                    if mytool.my_exportobjectlist == "PrismaticBuildingBodies":
                        ICEScript.write('" :T BUILDING-SECTION)' +'\n')
                    if mytool.my_exportobjectlist == "PrismaticZones":
                        if str(mytool.my_fileformatlist) == "Text":
                            ICEScript.write('((AGGREGATE :N GEOMETRY :X ZONE)' +'\n')
                            ICEScript.write("(:PAR :N ORIGIN :V #(0.0 0.0) :S '(:DEFAULT NIL 2))" +'\n')
                        if str(mytool.my_fileformatlist) == "idm":
                            TempZoneFolder.write('((AGGREGATE :N GEOMETRY :X ZONE)' +'\n')
                            TempZoneFolder.write("(:PAR :N ORIGIN :V #(0.0 0.0) :S '(:DEFAULT NIL 2))" +'\n')
                    if mytool.my_exportobjectlist == "PrismaticZones":
                        if str(mytool.my_fileformatlist) == "idm":
                            TempZoneFolder.write('(:PAR :N NCORN :V ')
                        if str(mytool.my_fileformatlist) == "Text":
                             ICEScript.write('(:PAR :N NCORN :V ')
                    if mytool.my_exportobjectlist == "IfcSpacesFromFloor":
                        ICEScript.write('     (:PAR :N CORNERS :DIM (')
                    if mytool.my_exportobjectlist == "PrismaticBuildingBodies":
                        ICEScript.write('(:PAR :N NCORN :V ')
                    mw = ob.matrix_world # Active object's world matrix
                    #loc_vertex_coordinates = [ v.co for v in ob.data.vertices ] # local coordinates of vertices
                    glob_vertex_coordinates = [ mw @ v.co for v in ob.data.vertices ] # Global coordinates of vertices
                    # Find the lowest Z and higest value amongst the object's verts
                    minZ = min( [ co.z for co in glob_vertex_coordinates  ] )
                    maxZ = max( [ co.z for co in glob_vertex_coordinates  ] )
                    #ceilingheight = maxZ - minZ
                    ceilingheight = mytool.my_prismaticheight
                    #determine how many points there are, right now this is quite crude and I make the same check twice
                    temppoints = 0
                    for v in ob.data.vertices:
                        if (mw @ v.co).z == minZ:
                            temppoints = temppoints + 1
                    if mytool.my_exportobjectlist == "PrismaticBuildingBodies":
                        ICEScript.write(str(temppoints))
                        ICEScript.write(")" +'\n')
                    if mytool.my_exportobjectlist == "PrismaticZones":
                        if str(mytool.my_fileformatlist) == "Text":
                            ICEScript.write(str(temppoints))
                            ICEScript.write(" :S '(:DEFAULT NIL 2))" +'\n')
                        if str(mytool.my_fileformatlist) == "idm":
                            TempZoneFolder.write(str(temppoints))
                            TempZoneFolder.write(" :S '(:DEFAULT NIL 2))" +'\n')
                    if mytool.my_exportobjectlist == "IfcSpacesFromFloor":
                        ICEScript.write(str(temppoints))
                        ICEScript.write(" 2) :SP (")
                        ICEScript.write(str(temppoints))
                        ICEScript.write(" 2) :V #2A(")
                    if mytool.my_exportobjectlist == "PrismaticZones":
                        if str(mytool.my_fileformatlist) == "idm":
                            TempZoneFolder.write("(:PAR :N CEILING-HEIGHT :V ")
                            TempZoneFolder.write(str(ceilingheight))
                            TempZoneFolder.write(")" +'\n')
                            TempZoneFolder.write("(:PAR :N FLOOR_HEIGHT_FROM_GROUND :V ")
                            TempZoneFolder.write(str(minZ))
                            TempZoneFolder.write(")" +'\n')
                        if str(mytool.my_fileformatlist) == "Text":
                            ICEScript.write("(:PAR :N CEILING-HEIGHT :V ")
                            ICEScript.write(str(ceilingheight))
                            ICEScript.write(")" +'\n')
                            ICEScript.write("(:PAR :N FLOOR_HEIGHT_FROM_GROUND :V ")
                            ICEScript.write(str(minZ))
                            ICEScript.write(")" +'\n')
                    #if mytool.my_exportobjectlist == "PrismaticBuildingBodies":
                        #ICEScript.write("(:PAR :N CEILING-HEIGHT :V ")
                        #ICEScript.write(str(ceilingheight))
                        #ICEScript.write(")" +'\n')
                        #ICEScript.write("(:PAR :N FLOOR_HEIGHT_FROM_GROUND :V ")
                        #ICEScript.write(str(minZ))
                        #ICEScript.write(")" +'\n')
                    if mytool.my_exportobjectlist == "PrismaticZones":
                        if str(mytool.my_fileformatlist) == "idm":
                            TempZoneFolder.write("(:PAR :N CORNERS :DIM (")
                            TempZoneFolder.write(str(temppoints))
                            TempZoneFolder.write(" 2) :V #2A(")
                        if str(mytool.my_fileformatlist) == "Text":
                            ICEScript.write("(:PAR :N CORNERS :DIM (")
                            ICEScript.write(str(temppoints))
                            ICEScript.write(" 2) :V #2A(")
                    if mytool.my_exportobjectlist == "PrismaticBuildingBodies":
                        ICEScript.write("(:PAR :N CORNERS :DIM (")
                        ICEScript.write(str(temppoints))
                        ICEScript.write(" 2) :V #2A(")
                    #bpy.ops.object.editmode_toggle()
                    for v in ob.data.vertices:
                        if (mw @ v.co).z == minZ:
                            if mytool.my_exportobjectlist == "PrismaticZones":
                                if str(mytool.my_fileformatlist) == "idm":
                                    TempZoneFolder.write("(")
                                    TempZoneFolder.write(str(1*(mw @ v.co).x))
                                    TempZoneFolder.write(" ")
                                    TempZoneFolder.write(str(1*(mw @ v.co).y)) #check! ICEScript.write(str(-1*(mw @ v.co).y))
                                    TempZoneFolder.write(") ")
                                if str(mytool.my_fileformatlist) == "Text":
                                    ICEScript.write("(")
                                    ICEScript.write(str(1*(mw @ v.co).x))
                                    ICEScript.write(" ")
                                    ICEScript.write(str(1*(mw @ v.co).y)) #check! ICEScript.write(str(-1*(mw @ v.co).y))
                                    ICEScript.write(") ")
                            if mytool.my_exportobjectlist == "IfcSpacesFromFloor":
                                ICEScript.write("(")
                                ICEScript.write(str(1*(mw @ v.co).x))
                                ICEScript.write(" ")
                                ICEScript.write(str(1*(mw @ v.co).y)) #check! ICEScript.write(str(-1*(mw @ v.co).y))
                                ICEScript.write(") ")
                            if mytool.my_exportobjectlist == "PrismaticBuildingBodies":
                                ICEScript.write("(")
                                ICEScript.write(str(1*(mw @ v.co).x))
                                ICEScript.write(" ")
                                ICEScript.write(str(1*(mw @ v.co).y)) #check! ICEScript.write(str(-1*(mw @ v.co).y))
                                ICEScript.write(") ")
                    if mytool.my_exportobjectlist == "PrismaticZones":
                        if str(mytool.my_fileformatlist) == "idm":
                            TempZoneFolder.write(")))" + '\n')
                            TempZoneFolder.close()
                        if str(mytool.my_fileformatlist) == "Text":
                            ICEScript.write(")))))" +'\n')
                    if mytool.my_exportobjectlist == "IfcSpacesFromFloor":
                         ICEScript.write("))" +'\n')
                         ICEScript.write("     (:PAR :N HEIGHT :V " + str(ceilingheight) + ")" +'\n')
                         ICEScript.write("     (:PAR :N LEVEL :V " + str(minZ) + ")" +'\n')
                         ICEScript.write("     (:PAR :N ADJ_WALLS :DIM (0) :SP (0) :V #() :S '(:DEFAULT NIL 2)))" + '\n')
                    #if mytool.my_exportobjectlist == "PrismaticBuildingBodies":
                    #    ICEScript.write("))))" +'\n')
                    if mytool.my_exportobjectlist == "PrismaticBuildingBodies":
                        ICEScript.write("))" +'\n')
                        ICEScript.write("(:PAR :N HEIGHT :V ")
                        ICEScript.write(str(minZ + ceilingheight))
                        ICEScript.write(")" +'\n')
                        ICEScript.write("(:PAR :N BOTTOM :V ")
                        ICEScript.write(str(minZ))
                        ICEScript.write("))" +'\n')
                    #bpy.ops.object.editmode_toggle()
                if mytool.my_exportobjectlist == "PrismaticBuildingBodies":
                    if str(mytool.my_fileformatlist) == "Text":
                        ICEScript.write(")" +'\n')
                    ICEScript.close()
                if mytool.my_exportobjectlist == "PrismaticZones":
                    ICEScript.write('\n')
                    ICEScript.close()
                if mytool.my_exportobjectlist == "IfcSpacesFromFloor":
                    ICEScript.write(')))' + '\n')
                    ICEScript.close()
                #Replace  \ with \\
                # Read in the file
                with open(str(bpy.path.abspath(mytool.scriptfolder_path)) + '\\' + scriptname + '.txt', 'r') as file :
                  filedata = file.read()
                # Replace the target string
                filedata = filedata.replace("\\", "\\\\")
                # Write the file out again
                with open(str(bpy.path.abspath(mytool.scriptfolder_path)) + '\\' + scriptname + '.txt', 'w') as file:
                  file.write(filedata)
        if mytool.my_exportobjectlist == "BuildingBodiesFromRoof":
            ICEScript.write('(:UPDATE [@]' +'\n')
           #Create building bodies based upon a series of points describing roof. Floor is at given absoute height
            C = bpy.context
            objs = C.selected_objects
            for ob in objs:
                #Write the script
                ICEScript.write('(:ADD (CE-SECTION :N "')
                ICEScript.write(str(ob.name) + str(mytool.groupname))
                ICEScript.write('" :T BUILDING-SECTION :D "Building body")' +'\n')
                ICEScript.write('(:PAR :N NCORN :V ')
                mw = ob.matrix_world # Active object's world matrix
                glob_vertex_coordinates = [ mw @ v.co for v in ob.data.vertices ] # Global coordinates of vertices
                #determine how many points there are, right now this is quite crude and I make the same check twice
                temppoints = 0
                for v in ob.data.vertices:
                    temppoints = temppoints + 1
                ICEScript.write(str(temppoints))
                ICEScript.write(')' +'\n')
                ICEScript.write('(:PAR :N CORNERS :DIM (' + str(temppoints) +' 2) :V #2A(')
                for v in reversed(ob.data.vertices):
                    ICEScript.write("(")
                    ICEScript.write(str(1*(mw @ v.co).x))
                    ICEScript.write(" ")
                    ICEScript.write(str(1*(mw @ v.co).y)) #check! ICEScript.write(str(-1*(mw @ v.co).y))
                    ICEScript.write(") ")
                ICEScript.write("))" +'\n')
                ICEScript.write('((FACE :N "Crawl space" :T CRAWL-FACE :INDEX -2000)' +'\n')
                ICEScript.write('(:PAR :N NCORN :V 0)' +'\n')
                ICEScript.write('(:PAR :N CORNERS :DIM (0 3) :V #2A())' +'\n')
                ICEScript.write('((FACE :N GROUND-FACE)' +'\n')
                ICEScript.write('(:PAR :N NCORN :V ' + str(temppoints) + ")" +'\n')
                ICEScript.write('(:PAR :N CORNERS :DIM (' + str(temppoints) +' 3) :V #2A(')
                for v in reversed(ob.data.vertices):
                    ICEScript.write("(")
                    ICEScript.write(str(1*(mw @ v.co).x))
                    ICEScript.write(" ")
                    ICEScript.write(str(1*(mw @ v.co).y)) #check! ICEScript.write(str(-1*(mw @ v.co).y))
                    ICEScript.write(" ")
                    ICEScript.write(str(mytool.my_prismaticheight)) #Here the height is the z0 for the building body
                    ICEScript.write(") ")
                ICEScript.write("))))" +'\n')
                ICEScript.write('((ROOF-FACE :N "Roof" :T ROOF-FACE :INDEX -1000)' +'\n')
                ICEScript.write("(:PAR :N NCORN :V " + str(temppoints)+ ")" +'\n')
                ICEScript.write("(:PAR :N CORNERS :DIM (" + str(temppoints) + " 3) :V #2A(")
                for v in ob.data.vertices: #I guess the height needs to be reversed since in is defined from the inside
                    ICEScript.write("(")
                    ICEScript.write(str(1*(mw @ v.co).x))
                    ICEScript.write(" ")
                    ICEScript.write(str(1*(mw @ v.co).y)) #check! ICEScript.write(str(-1*(mw @ v.co).y))
                    ICEScript.write(" ")
                    ICEScript.write(str((mw @ v.co).z))
                    ICEScript.write(") ")
                ICEScript.write("))))" +'\n')
                #Write the inverted script
                ICEScript.write('(:ADD (CE-SECTION :N "')
                ICEScript.write(str(ob.name) + str(mytool.groupname) + "inv")
                ICEScript.write('" :T BUILDING-SECTION :D "Building body")' +'\n')
                ICEScript.write('(:PAR :N NCORN :V ')
                mw = ob.matrix_world # Active object's world matrix
                glob_vertex_coordinates = [ mw @ v.co for v in ob.data.vertices ] # Global coordinates of vertices
                #determine how many points there are, right now this is quite crude and I make the same check twice
                temppoints = 0
                for v in ob.data.vertices:
                    temppoints = temppoints + 1
                ICEScript.write(str(temppoints))
                ICEScript.write(')' +'\n')
                ICEScript.write('(:PAR :N CORNERS :DIM (' + str(temppoints) +' 2) :V #2A(')
                for v in ob.data.vertices:
                    ICEScript.write("(")
                    ICEScript.write(str(1*(mw @ v.co).x))
                    ICEScript.write(" ")
                    ICEScript.write(str(1*(mw @ v.co).y))  #check! ICEScript.write(str(-1*(mw @ v.co).y))
                    ICEScript.write(") ")
                ICEScript.write("))" +'\n')
                ICEScript.write('((FACE :N "Crawl space" :T CRAWL-FACE :INDEX -2000)' +'\n')
                ICEScript.write('(:PAR :N NCORN :V 0)' +'\n')
                ICEScript.write('(:PAR :N CORNERS :DIM (0 3) :V #2A())' +'\n')
                ICEScript.write('((FACE :N GROUND-FACE)' +'\n')
                ICEScript.write('(:PAR :N NCORN :V ' + str(temppoints) + ")" +'\n')
                ICEScript.write('(:PAR :N CORNERS :DIM (' + str(temppoints) +' 3) :V #2A(')
                for v in ob.data.vertices:
                    ICEScript.write("(")
                    ICEScript.write(str(1*(mw @ v.co).x))
                    ICEScript.write(" ")
                    ICEScript.write(str(1*(mw @ v.co).y)) #check!  ICEScript.write(str(-1*(mw @ v.co).y))
                    ICEScript.write(" ")
                    ICEScript.write(str(mytool.my_prismaticheight)) #Here the height is the z0 for the building body
                    ICEScript.write(") ")
                ICEScript.write("))))" +'\n')
                ICEScript.write('((ROOF-FACE :N "Roof" :T ROOF-FACE :INDEX -1000)' +'\n')
                ICEScript.write("(:PAR :N NCORN :V " + str(temppoints)+ ")" +'\n')
                ICEScript.write("(:PAR :N CORNERS :DIM (" + str(temppoints) + " 3) :V #2A(")
                for v in reversed(ob.data.vertices): #I guess the height needs to be reversed since in is defined from the inside
                    ICEScript.write("(")
                    ICEScript.write(str(1*(mw @ v.co).x))
                    ICEScript.write(" ")
                    ICEScript.write(str(1*(mw @ v.co).y)) #check! ICEScript.write(str(-1*(mw @ v.co).y))
                    ICEScript.write(" ")
                    ICEScript.write(str((mw @ v.co).z))
                    ICEScript.write(") ")
                ICEScript.write("))))" +'\n')
            ICEScript.write(")" +'\n')
            ICEScript.close()
            #Replace  \ with \\
            # Read in the file
            with open(str(bpy.path.abspath(mytool.scriptfolder_path)) + '\\' + scriptname + '.txt', 'r') as file :
              filedata = file.read()
            # Replace the target string
            filedata = filedata.replace("\\", "\\\\")
            # Write the file out again
            with open(str(bpy.path.abspath(mytool.scriptfolder_path)) + '\\' + scriptname + '.txt', 'w') as file:
              file.write(filedata)
        # Divide the code in two parts, scripts that exports geometries and scripts that does not
        if mytool.my_exportobjectlist == "BuildingBodies" or mytool.my_exportobjectlist == "BuildingBodiesAndZones" or mytool.my_exportobjectlist == "Zones" or mytool.my_exportobjectlist == "ExternalObjects":
            if mytool.my_exportobjectlist == "ExternalObjects": #All selected meshes should be grouped
                fn = str(mytool.groupname) + '_' + ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(2)) #Add random 2 digit name to avaoid duplictaes by missatake
                fnorg = fn  #+ str(mytool.groupname) #save the zone name for later
                shadename = (str(bpy.path.abspath(mytool.externalobjetcsfolder_path)) + '\\' + str(fnorg)) #Get path
                if str(mytool.my_fileformatlist) == "OBJ":
                    fp = shadename  + '.obj'
                    # Give name according to selected filter plus a random string
                    bpy.ops.export_scene.obj(filepath=fp, axis_forward='Y', axis_up='Z', use_selection=True, check_existing=True)
                    #Write the script
                    ICEScript.write('(:UPDATE [@]' +'\n')
                    ICEScript.write('((AGGREGATE :N ARCDATA)'  + '\n' + '((AGGREGATE :N "' + fnorg + '" :T PICT3D)'  + '\n' + '(:PAR :N FILE :V "' + fp + '")(:PAR :N TRANSPARENCY :V ' + str(mytool.my_transparency) + ')(:PAR :N SHADOWING :V :' + str(mytool.my_shadingbool) + ')))' + '\n')
                    ICEScript.write(')')
                    ICEScript.close()
                    # Replace  \ with \\
                    # Read in the file
                    with open(str(bpy.path.abspath(mytool.scriptfolder_path)) + '\\' + scriptname + '.txt', 'r') as file :
                      filedata = file.read()
                    # Replace the target string
                    filedata = filedata.replace("\\", "\\\\")
                    # Write the file out again
                    with open(str(bpy.path.abspath(mytool.scriptfolder_path)) + '\\' + scriptname + '.txt', 'w') as file:
                      file.write(filedata)
                if str(mytool.my_fileformatlist) == "3DS":
                    fp = shadename  + '.3ds'
                    # Give name according to selected filter plus a random string
                    bpy.ops.export_scene.autodesk_3ds(filepath=fp, axis_forward='Y', axis_up='Z', use_selection=True, check_existing=True)
                    #Write the script
                    ICEScript.write('(:UPDATE [@]' +'\n')
                    ICEScript.write('((AGGREGATE :N ARCDATA)'  + '\n' + '((AGGREGATE :N "' + fnorg + '" :T PICT3D)'  + '\n' + '(:PAR :N FILE :V "' + fp + '")(:PAR :N TRANSPARENCY :V ' + str(mytool.my_transparency) + ')(:PAR :N SHADOWING :V :' + str(mytool.my_shadingbool) + ')))' + '\n')
                    ICEScript.write(')')
                    ICEScript.close()
                    # Replace  \ with \\
                    # Read in the file
                    with open(str(bpy.path.abspath(mytool.scriptfolder_path)) + scriptname + '.txt', 'r') as file :
                      filedata = file.read()
                    # Replace the target string
                    filedata = filedata.replace("\\", "\\\\")
                    # Write the file out again
                    with open(str(bpy.path.abspath(mytool.scriptfolder_path)) + scriptname + '.txt', 'w') as file:
                      file.write(filedata)
                if str(mytool.my_fileformatlist) == "Text":
                    ShowMessageBox("No export format selected", "Warning", 'ERROR')
                    #ICEScript.close()
            else:
                if str(mytool.my_fileformatlist) == "OBJ" or str(mytool.my_fileformatlist) == "3DS":
                    # Each selected mesh should be a separate object
                    view_layer = bpy.context.view_layer
                    obj_active = view_layer.objects.active
                    selection = bpy.context.selected_objects
                    bpy.ops.object.select_all(action='DESELECT')
                    #Make bounding spaces at -1000 and +1000
                    ICEScript.write('(:UPDATE [@] (:ADD (CE-ZONE :N "ICEBridgeCornerX0Y0" :T ZONE)((AGGREGATE :N GEOMETRY :X ZONE)(:PAR :N ORIGIN :V #(-1000 -1000) :S ' + "'" + "(:DEFAULT NIL 2))(:PAR :N NCORN :V 4 :S '(:DEFAULT NIL 2))(:PAR :N CEILING-HEIGHT :V 1.0)(:PAR :N FLOOR_HEIGHT_FROM_GROUND :V -1000.0)(:PAR :N CORNERS :DIM (4 2) :V #2A((1.0 -1.0) (1.0 1.0) (-1.0 1.0) (-1.0 -1.0) )))))" +'\n')
                    ICEScript.write('(:UPDATE [@] (:ADD (CE-ZONE :N "ICEBridgeCornerX1Y1" :T ZONE)((AGGREGATE :N GEOMETRY :X ZONE)(:PAR :N ORIGIN :V #(1000 1000) :S ' + "'" + "(:DEFAULT NIL 2))(:PAR :N NCORN :V 4 :S '(:DEFAULT NIL 2))(:PAR :N CEILING-HEIGHT :V 1.0)(:PAR :N FLOOR_HEIGHT_FROM_GROUND :V 1000.0)(:PAR :N CORNERS :DIM (4 2) :V #2A((1.0 -1.0) (1.0 1.0) (-1.0 1.0) (-1.0 -1.0) )))))" +'\n')
                    for obj in selection:
                        obj.select_set(True)
                        # Get Speckle category, type and family
                        # Check if a name exists. We should also check if name is valid and unique
                        #custompropertyexists = bpy.data.objects[str(obj.name)].get('name') is not None
                        #if custompropertyexists == True:
                        #        fn = (str(bpy.data.objects[str(obj.name)]['number'])) + " " + (str(bpy.data.objects[str(obj.name)]['name']))  + str(mytool.groupname)
                        #elif custompropertyexists == False:
                        fn = str(obj.name)  + str(mytool.groupname)
                        # Replace long Speckle names
                        fn = fn.replace("Objects.Geometry.Mesh -- ", "")
                        fn = fn.replace('/', '_') #Speckle-names can be invalid file names
                        fn = fn.replace(':', '_') #Speckle-names can be invalid file names
                        fn = fn.replace('.', '_') #Speckle-names can be invalid file names

                        #If ICEName Exsists, use that instead. We asume that it is valid
                        custompropertyexists = bpy.data.objects[str(obj.name)].get('ICEName') is not None
                        if custompropertyexists == True:
                            fn = str(bpy.data.objects[str(obj.name)]['ICEName'])
                        if mytool.my_exportobjectlist == "BuildingBodies":
                            fn = fn + "bb" #Add BB to separate building bodies
                        fnorg = fn # Save the zone name for later
                        fn = (str(bpy.path.abspath(mytool.scriptfolder_path)) + '\\' + str(fn)) #Get path
                        shadename = (str(bpy.path.abspath(mytool.externalobjetcsfolder_path)) + str(fnorg)) #Get path
                        # Exported location for obj-files should be places in tempfolder with the exception of shading objects that are permanent
                        view_layer.objects.active = obj
                        # Some exporters only use the active object
                        if str(mytool.my_fileformatlist) == "OBJ":
                            fp = fn  + '.obj'
                            bpy.ops.export_scene.obj(filepath=fp, axis_forward='Y', axis_up='Z', use_selection=True, check_existing=True)
                        if str(mytool.my_fileformatlist) == "3DS":
                            fp = fn  + '.3ds'
                            # Give name according to selected filter plus a random string
                            bpy.ops.export_scene.autodesk_3ds(filepath=fp, axis_forward='Y', axis_up='Z', use_selection=True, check_existing=True)
                        # The actual script varies with object type
                        if mytool.my_exportobjectlist == "BuildingBodies":
                            ICEScript.write('(:call Import-Geometry (:call ice-3d-pane [@] t t)' +" '" + 'building-body ' + '(0 0 0)' + ' 0 "' + fp + '")' +'\n')
                        if mytool.my_exportobjectlist == "Zones":
                            ICEScript.write('(:call Import-Geometry (:call ice-3d-pane [@] t t)' +" '" + 'zone ' + '(0 0 500)' + ' 0 "' + fp + '")'+'\n') #Place the zone intentionaly off and then move it into poistion to speedup + '(:REMOVE "' + str(fnorg) + '-s")'+'\n')
                            if custompropertyexists == True:
                                #Change Group name to ICEGroup
                                ICEScript.write('(:UPDATE [@]  ((CE-ZONE :N "' + str(bpy.data.objects[str(obj.name)]['ICEName']) + '")(:PAR :N GROUP :V "' + str(bpy.data.objects[str(obj.name)]['ICEGroup']) +'" :S ' + "'(:DEFAULT NIL 2))))" +'\n')
                            #Delete automaicly created building bodies, this code need to change for ICE 5
                            ICEScript.write('(:UPDATE [@]  (:REMOVE "' + fnorg + '-s' + '"))' + '\n')
                            #(:SET h_old [z_ Geometry FLOOR_HEIGHT_FROM_GROUND])
                            ICEScript.write('(:FOR (Z_ [@ :ZONES] :WHEN (== "' + fnorg + '" (:CALL NAME Z_)))(:SET dz_ -500)(:SET h_old [z_ Geometry FLOOR_HEIGHT_FROM_GROUND])(:UPDATE Z_  ((AGGREGATE :N GEOMETRY)   (:PAR :N FLOOR_HEIGHT_FROM_GROUND :V (+ dz_ h_old)))))' + '\n')
                        if mytool.my_exportobjectlist == "BuildingBodiesAndZones":
                            ICEScript.write('(:call Import-Geometry (:call ice-3d-pane [@] t t)' +" '" + 'zone ' + '(0 0 0)' + ' 0 "' + fp + '")' +'\n')
                            if custompropertyexists == True:
                                #Change Group name to ICEGroup
                                ICEScript.write('(:UPDATE [@]  ((CE-ZONE :N "' + str(bpy.data.objects[str(obj.name)]['ICEName']) + '")(:PAR :N GROUP :V "' + str(bpy.data.objects[str(obj.name)]['ICEGroup']) +'" :S ' + "'(:DEFAULT NIL 2))))" +'\n')
                        obj.select_set(False)
                        # Save object name so text files can be edited later if needed
                        objectlist.append(fnorg)
                    #Delete bounding temp zones
                    ICEScript.write('(:UPDATE [@]  (:REMOVE "ICEBridgeCornerX0Y0")(:REMOVE "ICEBridgeCornerX1Y1"))')
                    ICEScript.close()
                    view_layer.objects.active = obj_active
                    for obj in selection:
                        obj.select_set(True)
                    # Replace  \ with \\
                    # Read in the file
                    with open(str(bpy.path.abspath(mytool.scriptfolder_path)) + '\\' + scriptname + '.txt', 'r') as file :
                      filedata = file.read()
                    # Replace the target string
                    filedata = filedata.replace("\\", "\\\\")
                    # Write the file out again
                    with open(str(bpy.path.abspath(mytool.scriptfolder_path)) + '\\' + scriptname + '.txt', 'w') as file:
                      file.write(filedata)
                if str(mytool.my_fileformatlist) == "Text":
                    C = bpy.context
                    objs = C.selected_objects
                    for ob in objs:
                        #me = bpy.context.object.data
                        me = ob.data
                        # per-poly lists of loop indices
                        pli = (p.loop_indices for p in me.polygons)
                        # .. to per-poly lists of vertex indices
                        pvi = ([me.loops[l].vertex_index for l in ll] for ll in pli)
                        # ..to per-poly lists of vertices
                        p_verts = ([me.vertices[id] for id in idl] for idl in pvi)
                        # floating point precision
                        prec = 2
                        co_lists =[]

                        for v_list in p_verts:
                            co_str = '('
                            co_strs = []
                            for v in [*v_list[::-1],v_list[-1]]:
                                tempx = (1*v.co[0])
                                tempy = (1*v.co[1])  #check! tempy = (-1*v.co[1])
                                co_strs.append(f'{tempx: .{prec}f} '
                                               f'{tempy: .{prec}f} '
                                               f'{v.co[2]: .{prec}f}')
                            co_str += ') ('.join(co_strs)
                            co_str += ')'
                            co_lists.append(co_str)
                        DBstr =  "(:set building [@])\n"
                        DBstr +=  "(:set pset (:call polyhedron-p '(("
                        DBstr += ") (".join(co_lists)
                        DBstr += "))))\n"
                        DBstr += "(:set ((bsect zone) (:call values-output-as-list 'surfaces-to-zone nil '(0 0 0) 'ce-zone 'zone :pset pset)))\n"
                        #Get Speckle category, type and family
                        #Check if a name exists. We should also check if name is valid and unique
                        #custompropertyexists = bpy.data.objects[str(ob.name)].get('name') is not None
                        #if custompropertyexists == True:
                        #        fn = (str(bpy.data.objects[str(ob.name)]['number'])) + " " +(str(bpy.data.objects[str(ob.name)]['name'])) + str(mytool.groupname)
                        #elif custompropertyexists == False:
                        fn = str(ob.name) + str(mytool.groupname)
                        #Replace long Speckle names
                        fn = fn.replace("Objects.Geometry.Mesh -- ", "")
                        fn = fn.replace('/', '_') #Speckle-names can be invalid file names
                        fn = fn.replace(':', '_') #Speckle-names can be invalid file names
                        fn = fn.replace('.', '_') #Speckle-names can be invalid file names

                        #If ICEName Exsists, use that instead. We asume that it is valid
                        custompropertyexists = bpy.data.objects[str(ob.name)].get('ICEName') is not None
                        if custompropertyexists == True:
                            fn = (str(bpy.data.objects[str(ob.name)]['ICEName']))

                        DBstr += '(:call Lform-Set-Attributes zone :n "'  + fn + '")\n'
                        DBstr += '(:call Lform-Set-Attributes bsect :n "'  + fn + 'bb")\n'
                        if mytool.my_exportobjectlist == "Zones" or mytool.my_exportobjectlist == "BuildingBodiesAndZones":
                            DBstr += "(:set zone (:call create-and-add-component building zone nil))\n"
                        if mytool.my_exportobjectlist == "BuildingBodies" or mytool.my_exportobjectlist == "BuildingBodiesAndZones":
                            DBstr += "(:set bsect (:call create-and-add-component building bsect nil))\n"
                        ICEScript.write(str(DBstr))
                        #Save object name if we want to create separate script files
                        objectlist.append(fn)
                        #!!!!Here womething is very wrong!!! ICEScript.close() is needed for geometry but not for not geometry
                        ICEScript.close()
        #Code for exporting windows and doors
        if mytool.my_exportobjectlist == "Windows" or mytool.my_exportobjectlist == "Doors": #mytool.my_exportobjectlist == "Windows2" or mytool.my_exportobjectlist == "Windows3" or
            from bpy import context as C
            for ob in C.selected_objects:
                mw = ob.matrix_world #Normal direction should be according to world
                N = mw.inverted_safe().transposed().to_3x3() #Normal direction should be according to world
                #Make sure only meshes are selected
                if ob.type =='MESH': #Ensure origin is centered on bounding box center
                    if bpy.ops.object.type =='MESH':
                        bpy.ops.object.origin_set(type ='ORIGIN_CENTER_OF_MASS')
                        #Center origin
                        bpy.ops.object.origin_set(type ='ORIGIN_GEOMETRY', center='BOUNDS')
                    centre = ob.location  # Does this work for all objects? All objects should be changed mnually manually by using Object-Set Origin-Origin to center of mass (surface) before export
                    faces_up = (p for p in ob.data.polygons)# if p.normal.z > 0) #Not used right now
                    ob2 = max(faces_up, key = lambda f: f.area) #Get largest area in the collection
                    n = N @ ob2.normal
#                    if mytool.my_exportobjectlist == "Windows2":
#                        n = mathutils.Vector((0,-1,0)) #Default vector, pointing -Y
#                        n.rotate(ob.rotation_euler)
#                    if mytool.my_exportobjectlist == "Windows3":
#                        n = mathutils.Vector((0,0,1)) #Default vector, pointing +Z
#                        n.rotate(ob.rotation_euler)
                        #print (n)
                    #Find width and heigh. Probably depends on object type so I use two methods and use the largest
                    #For vertical windows it looks that the x or y is width and z is height
                    #For sloping windows x is with and y is height. z is depth
                    if (ob.dimensions[1]) > (ob.dimensions[2]): #Sloping window
                        dimensionwidth = (ob.dimensions[0])
                        dimensionheight = (ob.dimensions[1])
                        dimensiondepth = (ob.dimensions[2])
                    if (ob.dimensions[1]) < (ob.dimensions[2]): #Horizontal window
                        dimensionwidth = (ob.dimensions[0]) #Width or depth, hard to say
                        dimensiondepth = (ob.dimensions[1]) #Width or depth, hard to say
                        dimensionheight = (ob.dimensions[2]) #Height
                    largestdimensionwidth = (maximum(dimensionwidth, dimensiondepth)) #Pick the largest, most important for vertical windows
                    verts = ob.data.vertices #Get all corners
                    calculatedwidth = max(v.co.x for v in verts) - min(v.co.x for v in verts) #Get largest value, this is only in x, not in the normal plane. One way would be to use the IFC/Speckle data.
                    calculateddepth = max(v.co.y for v in verts) - min(v.co.y for v in verts) #Get smallest value
                    largestcalculatedwidth = (maximum(calculatedwidth, calculateddepth)) #Make sure the largest of with and depth is choosen
                    width = (maximum(largestdimensionwidth, largestcalculatedwidth))
                    #width = width -0.4 #Not used but might be an option to change the size manually
                    #Possibility to rotate normal 90 degrees:
                    #nx = (normal.x * math.cos(math.radians(90))) - (normal.y * math.sin(math.radians(90)))
                    #ny = (normal.x * math.sin(math.radians(90))) + (normal.y * math.cos(math.radians(90)))
                    calculatedheight = max(v.co.z for v in verts) - min(v.co.z for v in verts)
                    height = calculatedheight
                    height = (maximum(dimensionheight, calculatedheight))
                    #height = height -0.4
                    #If it is a IFCWIndow, use the given width
                    #Right now it assumes mm, probably not sure
                    #There is a bug in height
                    if ob.name.startswith("IfcWindow"):
                        ifc_entity = tool.Ifc.get_entity(ob) #gets the Ifc Entity from the Blender object
                        #Unit
                        #IFCHeightm = ifc_entity.OverallHeight/1000
                        #IFCWidthm = ifc_entity.OverallWidth#/1000
                        #height = IFCHeightm
                        #width = IFCWidthm
                    #Get Speckle category, type and family
                    #Check if a name exists. We should also check if name is valid and unique
                    #custompropertyexists = bpy.data.objects[str(ob.name)].get('type') is not None
                    #if custompropertyexists == True:
                    #    panetype = (str(bpy.data.objects[str(ob.name)]['type']))  + str(mytool.groupname)
                    #elif custompropertyexists == False:
                    panetype = "Undefined"  + str(mytool.groupname)
                    #If it is a IFCwindow this name has priority
                    if ob.name.startswith("IfcWindow"):
                        #print (str(tool.Ifc.get_entity(ob)))
                        ifc_entity = tool.Ifc.get_entity(ob) #gets the Ifc Entity from the Blender object
                        if str(ifc_entity) != "Text":
                            panetype = str(ifc_entity.ObjectType) # + str(mytool.groupname)
                        else:
                            panetype = str(mytool.groupname) + "No ObjectType"
                    #Produce script
                    #print(str(width))
                    #if width > 0.2: #Do not export very small windows and doors to avoid errors
                    ICEScript.write("((")
                    ICEScript.write(str(centre.x)) #Change direction
                    ICEScript.write(" ")
                    ICEScript.write(str(centre.y)) #Change direction #check! ICEScript.write(str(-centre.y))
                    ICEScript.write(" ")
                    ICEScript.write(str(centre.z))
                    ICEScript.write(") (")
                    ICEScript.write(str(n[0])) #Change direction (invert is fine)
                    ICEScript.write(" ")
                    ICEScript.write(str(n[1])) #Change direction (invert is fine) #check! ICEScript.write(str(-n[1]))
                    ICEScript.write(" ")
                    ICEScript.write(str(n[2]))
                    if mytool.my_exportobjectlist == "Windows": # or mytool.my_exportobjectlist == "Windows2" or mytool.my_exportobjectlist == "Windows3"
                        ICEScript.write(") (AGGREGATE :T IFCIM_WINDOW :N ")
                    elif mytool.my_exportobjectlist == "Doors":
                        ICEScript.write(") (AGGREGATE :T IFCIM_DOOR :N ")
                    ICEScript.write('"')
                    ICEScript.write(str(ob.name))
                    ICEScript.write('"')
                    ICEScript.write(") (:PAR :N DY :V ")
                    ICEScript.write(str(height))
                    ICEScript.write(") (:PAR :N DX :V ")
                    ICEScript.write(str(width))
                    ICEScript.write(") (:PAR :N STYLE :V ")
                    ICEScript.write('"')
                    ICEScript.write(panetype)
                    ICEScript.write('"))' + '\n')
            ICEScript.close()
            #Adjust long file names
            # Read in the file
            if mytool.my_exportobjectlist == "Windows": #mytool.my_exportobjectlist == "Windows2" or mytool.my_exportobjectlist == "Windows3"
                with open(str(bpy.path.abspath(mytool.scriptfolder_path)) + 'ImportWindows.txt', 'r') as file :
                    filedata = file.read()
                    # Replace the target string
                    filedata = filedata.replace("Objects.Geometry.Mesh -- ", "")
                    # Write the file out again
                    with open(bpy.path.abspath(str(mytool.scriptfolder_path)) + 'ImportWindows.txt', 'w') as file:
                        file.write(filedata)
            elif mytool.my_exportobjectlist == "Doors":
                with open(str(bpy.path.abspath(mytool.scriptfolder_path)) + 'ImportDoors.txt', 'r') as file :
                    filedata = file.read()
                    # Replace the target string
                    filedata = filedata.replace("Objects.Geometry.Mesh -- ", "")
                    # Write the file out again
                    with open(str(bpy.path.abspath(mytool.scriptfolder_path)) + 'ImportDoors.txt', 'w') as file:
                        file.write(filedata)
        #Edit the script and run bat script if selected, scripts using NKS can not be run
        if mytool.my_runIDAICE == True and bpy.context.scene.my_tool.my_exportobjectlist != "Doors" and bpy.context.scene.my_tool.my_exportobjectlist != "Windows":
            #Create BAT-file if selected and script can be run by IDA ICE automaticly (not windows and doors using TTS)
            if mytool.IDAICEfolder_path == "":
                ShowMessageBox("IDA ICE path not selected", "Warning", 'ERROR')
                return {'FINISHED'}
            if mytool.model_path == "" and mytool.my_exportobjectlist == "ExternalObjects":
                ShowMessageBox("IDA ICE model not selected", "Warning", 'ERROR')
                return {'FINISHED'}
            #Create Bat-file
            Tempbatfile = str(bpy.path.abspath(mytool.scriptfolder_path)) + '\\' + scriptname + '.bat'
            BATFile=open(Tempbatfile,'w')
            BATFile.write('"' + str(bpy.path.abspath(mytool.IDAICEfolder_path)) + '\\bin\ice.exe"' + ' -X "' + str(bpy.path.abspath(mytool.scriptfolder_path)) + '\\' + scriptname +'.txt')# + '_bat.txt"')
            BATFile.close()
            #Edit Script so it can be run from BAT-file
            new_content = '(:SET doc_ (:call get-document "' + str(bpy.path.abspath(mytool.model_path)) + '"))'
            new_content = new_content.replace("\\", "\\\\")
            with open(str(bpy.path.abspath(mytool.scriptfolder_path)) + '\\' + scriptname + ".txt", 'r+') as file:
                file_data = file.read()
                file_data = file_data.replace("@", "doc_")
                file.seek(0, 0)
                file.write(new_content + '\n' + file_data)
#            #Run the BAT-file
            subprocess.Popen([Tempbatfile])
        return {'FINISHED'}

class WM_OT_PerformCommand(Operator):
    bl_label = "Perform Command"
    bl_idname = "wm.perform_command"
    bl_description = "Perform selected command"

    def execute(self, context):
        scene = context.scene
        mytool = scene.my_tool


        if mytool.my_postprocesslist == "CreateUDICSV":
            #path_df = "C:\\Temp\\DAYLIGHT-DF.h5"
            path_ggzone = str(bpy.path.abspath(mytool.H5_path)) #"C:\\Temp\\FIELD-3D.h5"

            # Initializing results dataframe and reading measuring plane names
            results = pd.DataFrame()
            results['Zone_name'] = np.nan
            results['UDI_tot'] = np.nan
            results['UDI_sub'] = np.nan
            h5f = h5py.File(path_ggzone, 'r')
            planes = list(h5f.keys())
            h5f.close()

            # Evaluating MT_UDI for all measuring planes
            for i in planes:
                dl_res = UDI_eval(path = path_ggzone, plane = i, year = 2023, sim_type = 'Radiosity', ill_min = 300, ill_max = 3000)
                UDI_tot = round(sum(dl_res['udi_24hr'])/len(dl_res['udi_24hr']), 2)
                UDI_sub = round(sum(dl_res['udi_08to18'])/len(dl_res['udi_08to18']), 2)
                results.loc[results.shape[0]] = [i, UDI_tot, UDI_sub]

            results.to_csv(str(bpy.path.abspath(mytool.scriptfolder_path)) + "UDI.csv",
                           index = False,
                           encoding = 'utf-8',
                           decimal = '.',
                           na_rep = 'NaN')
        if mytool.my_postprocesslist == "CreatePointCSV":
            model = b"C:\\Temp\\building1.idm"
            origos = get_origo_zones(model)

            path_ggzone = "C:\\Temp\\building1\\energy\\FIELD-3D.h5"
            geometry = write_geometry(path_ggzone, origos)
            geometry.to_csv("C:\\Temp\\geometry.csv",
                            index = False,
                            encoding = 'utf-8',
                            decimal = '.',
                            na_rep = 'NaN')
            path_csv = "C:\\Temp\\"
            year = 2023
            write_results(path_ggzone, path_csv, year)
        if mytool.my_postprocesslist == "CreteRoomShape":
            #Create util.py
            #ICEScript = open(str(bpy.path.abspath(mytool.scriptfolder_path)) + '\\' + scriptname + '.txt','w')
            #with open(str(bpy.path.abspath(mytool.scriptfolder_path)) + '\\' + 'untilxx.py', 'w') as f:
            #    f.write(pythoncode)
            #pythoncode
            #Create pythonscript
            #Run scripts
            #Read result
            #Create a .py file
            #Run the pythonfile and read back room name using the API
            import subprocess
            #The python file should be created by code
            comm = subprocess.Popen(["python", "C:\\Temp\\ReadRoomsFromICE.py"], stdout=subprocess.PIPE)
            printedresult = comm.stdout.read().decode('utf-8')
            comm.stdout.close()
            comm.wait()
            #First remove wrong characters
            printedresult = printedresult.replace('[', '')
            printedresult = printedresult.replace(']', '')
            printedresult = printedresult.replace("'", '')
            printedresult = printedresult.replace(', ', ',')
            printedresult = printedresult.replace(' ,', ',')
            storedresult = printedresult.splitlines()
            #print(storedresult)
            #print (storedresult[0])
            #print (storedresult[0][0])
            for zones in storedresult:
                #print (zones)
                #For some reason the list is not a list som lets convert IT
                templist = list(zones.split(","))
                #Create objects representing zones and assign custom properties
                #Assume that zones are quadratic
                tempSize = math.sqrt(float(templist[6]) / float(templist[5]))
                tempX0 = float(templist[2]) + tempSize / 2
                tempY0 = float(templist[3]) + tempSize / 2
                tempZ0 = float(templist[4]) + (float(templist[5]) / 2)
                if str(mytool.my_shapelist) == "Plane":
                    bpy.ops.mesh.primitive_plane_add(location = (tempX0, tempY0, tempZ0), size = float(mytool.my_size))
                elif str(mytool.my_shapelist) == "Cube":
                    bpy.ops.mesh.primitive_cube_add(location = (tempX0, tempY0, tempZ0), size = float(mytool.my_size))
                elif str(mytool.my_shapelist) == "Sphere":
                    bpy.ops.mesh.primitive_uv_sphere_add(radius = (float(mytool.my_size) / 2), location = (tempX0, tempY0, tempZ0))
                elif str(mytool.my_shapelist) == "Cylinder":
                    bpy.ops.mesh.primitive_cylinder_add(radius = (float(mytool.my_size) / 2), depth=0.01, location = (tempX0, tempY0, tempZ0))
                ob = bpy.context.object
                me = ob.data
                #Give zones a nice name, not important since they will have custom parameters to be identified with
                bpy.context.object.name = str(templist[0]) + " " + str(templist[1])
                me.name = str(templist[0]) + " " + str(templist[1]) + "Mesh"
                ob["ICEName"] = str(templist[0])
                ob["ICEGroup"] = str(templist[1])
                ob["ICEType"] = "Zone"
                #ob["ICEZone"] = str(templist[0]) #This is not needed
            #    #Create texts in the right positions using the APi
            #    font_curve = bpy.data.curves.new(type="FONT", name="RoomName")
            #    font_curve.body = texts
            #    obj = bpy.data.objects.new(name="Font Object", object_data=font_curve)
            #    #print(texts)
            #    # -- Set scale and location
            #    obj.location = (-1, 1, 10)
            #    obj.scale = (0.75, 0.5, 0.5)
            #    bpy.context.scene.collection.objects.link(obj)
        if mytool.my_postprocesslist == "CreatePointsFromCSV":
            #Supported format:x,y,z, variables (variables vould be result, name, dx,dy,dz and so on). Requires header rom with name
            csvpath = str(mytool.CSV_path) #"C:/test/Lobby_Floor_Plane.csv"
            with open(csvpath) as csvfile:
                content = csv.reader(csvfile)
                for i, row in enumerate(content):
                    if i == 0:
                        #Save the header row as naming for custom objects
                        header = row
                    else:
                        if str(mytool.my_shapelist) == "Plane":
                            bpy.ops.mesh.primitive_plane_add(location = (float(row [0]), float(row [1]), float(row [2])), size = float(mytool.my_size))
                        elif str(mytool.my_shapelist) == "Cube":
                            bpy.ops.mesh.primitive_cube_add(location = (float(row [0]), float(row [1]), float(row [2])), size = float(mytool.my_size))
                        elif str(mytool.my_shapelist) == "Sphere":
                            bpy.ops.mesh.primitive_uv_sphere_add(radius = (float(mytool.my_size) / 2), location = (float(row [0]), float(row [1]), float(row [2])))
                        elif str(mytool.my_shapelist) == "Cylinder":
                            bpy.ops.mesh.primitive_cylinder_add(radius = (float(mytool.my_size) / 2), depth=0.01, location = (float(row [0]), float(row [1]), float(row [2])))
                        ob = bpy.context.object
                        me = ob.data
                        bpy.context.object.name = 'Point'
                        me.name = 'PointMesh'
                        tempnumber = 0
                        for column in row:
                            customproperty = header[tempnumber]
                            if customproperty != "ICEName" and customproperty != "ICEZone":
                                ob[customproperty] = float(column)
                            else:
                                ob[customproperty] = column
                            ob["ICEType"] = "Point"
                            tempnumber = tempnumber + 1
            bpy.context.view_layer.update()
        if mytool.my_postprocesslist == "ReadCSVData":
            #This asumes a CSV with ICEName and a series of variables
            csvpath = str(mytool.CSV_path)
            with open(csvpath) as csvfile:
                content = csv.reader(csvfile)
                for i, row in enumerate(content):
                    if i == 0:
                        #Save the header row as naming for custom objects
                        header = row
                    else:
                        #For each row, find matching object in the blender file
                        for obj in bpy.context.scene.objects: #Check all objects (there should not be duplicates but I do not check for this)
                            #Kolla att de har ICEName
                            custompropertyexists = bpy.data.objects[str(obj.name)].get('ICEName') is not None
                            if custompropertyexists == True:
                                if obj["ICEName"] == str(row[0]): #The ICEName is the same as the first column name
                                    tempcolumn = 0
                                    for column in row:
                                        if tempcolumn > 0:
                                            #Fill all values to obj
                                            customproperty = header[tempcolumn]
                                            obj[customproperty] = float(column) #Imported values are allways numbers right now
                                        tempcolumn = tempcolumn + 1
        if mytool.my_postprocesslist == "ColorAccordingToProperty":
            #Color each selected object based upon selected custom numerical value
            RED, YELLOW, GREEN, CYAN, BLUE, MAGENTA = range(0, 360, 60)
            for obj in bpy.context.selected_objects:
                if str(mytool.custompropertyname) in obj:
                    #Make sure that values not are greater then max or min
                    tempvalue = float((obj[str(mytool.custompropertyname)]))
                    if tempvalue > float(mytool.my_maxvalue):
                        tempvalue = float(mytool.my_maxvalue)
                    if tempvalue < float(mytool.my_minvalue):
                        tempvalue = float(mytool.my_minvalue)

                    if str(mytool.my_colorscale) == "BLUERED":
                        tempcolor =  (pseudocolor(tempvalue, float(mytool.my_minvalue), float(mytool.my_maxvalue), BLUE, RED))
                    elif str(mytool.my_colorscale) == "GREENRED":
                        tempcolor =  (pseudocolor(tempvalue, float(mytool.my_minvalue), float(mytool.my_maxvalue), GREEN, RED))
                    elif str(mytool.my_colorscale) == "REDGREEN":
                        tempcolor =  (pseudocolor(tempvalue, float(mytool.my_minvalue), float(mytool.my_maxvalue), RED, GREEN))
                    elif str(mytool.my_colorscale) == "MAGENTARED":
                        tempcolor =  (pseudocolor(tempvalue, float(mytool.my_minvalue), float(mytool.my_maxvalue), MAGENTA, RED))
                    #Create a new material for each object
                    tempmaterial = bpy.data.materials.new(str(tempcolor))
                    tempmaterial.diffuse_color = (tempcolor[0],tempcolor[1],tempcolor[2] ,1)
                    tempmaterial.specular_intensity = 0
                    tempmaterial.roughness = 1
                    obj.active_material = tempmaterial
            #Create color scale
            #Delete exsisting scale
            bpy.ops.object.select_all(action = 'DESELECT')
            bpy.ops.object.select_pattern(pattern="ICEScale*")
            bpy.ops.object.delete()
            #Create scale
            scaleX0 = 0
            scaleY0 = 0
            for scalestep in range(0, 11):
                bpy.ops.mesh.primitive_plane_add(location = (scaleX0, scaleY0 + scalestep , 0), size = 1)
                obj = bpy.context.object
                me = obj.data
                #
                bpy.context.object.name = 'ICEScalestep' + str(scalestep)
                me.name = 'ICEScalemesh' + str(scalestep)
                tempvalue = float(mytool.my_minvalue) + scalestep * ((float(mytool.my_maxvalue) - float(mytool.my_minvalue)) / 10)
                obj["ICEvalue"] = tempvalue
                if str(mytool.my_colorscale) == "BLUERED":
                    tempcolor =  (pseudocolor(float((obj["ICEvalue"])), float(mytool.my_minvalue), float(mytool.my_maxvalue), BLUE, RED))
                elif str(mytool.my_colorscale) == "GREENRED":
                    tempcolor =  (pseudocolor(float((obj["ICEvalue"])), float(mytool.my_minvalue), float(mytool.my_maxvalue), GREEN, RED))
                elif str(mytool.my_colorscale) == "REDGREEN":
                    tempcolor =  (pseudocolor(float((obj["ICEvalue"])), float(mytool.my_minvalue), float(mytool.my_maxvalue), RED, GREEN))
                elif str(mytool.my_colorscale) == "MAGENTARED":
                    tempcolor =  (pseudocolor(float((obj["ICEvalue"])), float(mytool.my_minvalue), float(mytool.my_maxvalue), MAGENTA, RED))
                #Create a new material for each object
                tempmaterial = bpy.data.materials.new(str(tempcolor))
                tempmaterial.diffuse_color = (tempcolor[0],tempcolor[1],tempcolor[2] ,1)
                tempmaterial.specular_intensity = 0
                tempmaterial.roughness = 1
                obj.active_material = tempmaterial
                #Create texts in the right positions
                font_curve = bpy.data.curves.new(type="FONT", name="Scale")
                #font_curve.align_x = 'CENTER'
                font_curve.align_y = 'CENTER'
                font_curve.body = str(round(float(tempvalue), 2))
                textobj = bpy.data.objects.new(name="ICEScaletext" + str(scalestep), object_data=font_curve)
                # -- Set scale and location
                textobj.location = (scaleX0 + 0.75, scaleY0 + scalestep, 0)
                textobj.scale = (0.75, 0.75, 0.75)
                bpy.context.scene.collection.objects.link(textobj)
                tempmaterial = bpy.data.materials.new("scalecolormaterial")
                tempmaterial.diffuse_color = (0,0,0,1)
                tempmaterial.specular_intensity = 0
                tempmaterial.roughness = 1
                textobj.active_material = tempmaterial
                #Create Unit on top
                if scalestep == 10:
                    font_curve = bpy.data.curves.new(type="FONT", name="Unit")
                    font_curve.align_x = 'CENTER'
                    font_curve.body = str (mytool.custompropertyname) + " [" + str(mytool.objecttext) +"]"
                    textobj = bpy.data.objects.new(name="ICEScaleUnit", object_data=font_curve)
                    textobj.location = (scaleX0, scaleY0 + scalestep + 1, 0)
                    textobj.scale = (0.95, 0.95, 0.95)
                    bpy.context.scene.collection.objects.link(textobj)
                    textobj.active_material = tempmaterial
            #Update
            bpy.context.view_layer.update()
        if mytool.my_postprocesslist == "TextAccordingToProperty":
            #Color each selected object based upon selected custom numerical value
            for obj in bpy.context.selected_objects:
                centre = obj.location
                if str(mytool.custompropertyname) in obj:
                    #Create texts in the right positions
                    font_curve = bpy.data.curves.new(type="FONT", name="RoomName")
                    font_curve.align_x = 'CENTER'
                    font_curve.align_y = 'CENTER'
                    font_curve.body = obj["ICEName"]
                    font_curve.body = font_curve.body + "\n" + obj["ICEGroup"]
                    #font_curve.body = font_curve.body + "\n" + mytool.custompropertyname + ": "
                    font_curve.body = font_curve.body + "\n" + str(round(obj[mytool.custompropertyname],2)) #2 decimals
                    font_curve.body = font_curve.body + " " +  mytool.objecttext
                    textobj = bpy.data.objects.new(name="Font Object", object_data=font_curve)
                    # -- Set scale and location
                    textobj.location = (centre.x, centre.y, centre.z)
                    textobj.scale = (0.3, 0.3, 0.3)
                    bpy.context.scene.collection.objects.link(textobj)
        if mytool.my_postprocesslist == "CreateShapes":
            for obj in bpy.context.selected_objects:
                centre = obj.location
                if str(mytool.my_shapelist) == "Plane":
                    bpy.ops.mesh.primitive_plane_add(location = (centre.x, centre.y, centre.z), size = float(mytool.my_size))
                elif str(mytool.my_shapelist) == "Cube":
                    bpy.ops.mesh.primitive_cube_add(location = (centre.x, centre.y, centre.z), size = float(mytool.my_size))
                elif str(mytool.my_shapelist) == "Sphere":
                    bpy.ops.mesh.primitive_uv_sphere_add(radius = (float(mytool.my_size) / 2), location = (centre.x, centre.y, centre.z))
                elif str(mytool.my_shapelist) == "Cylinder":
                    bpy.ops.mesh.primitive_cylinder_add(radius = (float(mytool.my_size) / 2), depth=0.01, location = (centre.x, centre.y, centre.z))
                ob = bpy.context.object
                me = ob.data
                bpy.context.object.name = 'Shape'
                me.name = 'ShapeMesh'
                #Copy all properties, can be useful for various reasons
                props = [(k, v) for k, v in obj.items()]
                for k, v in props:
                    ob[k] = v
        if mytool.my_objectoperationlist == "ImportRoomName": #API, not used
            #Create a .py file
            #Run the pythonfile and read back room name using the API
            import subprocess
            #The python file should be created by code
            comm = subprocess.Popen(["python", "C:\\Temp\\readresult.py"], stdout=subprocess.PIPE)
            printedresult = comm.stdout.read().decode('utf-8')
            comm.stdout.close()
            comm.wait()
            storedresult=printedresult.splitlines()
            #print(wait)
            for texts in storedresult:
                #Create texts in the right positions using the APi
                font_curve = bpy.data.curves.new(type="FONT", name="RoomName")
                font_curve.body = texts
                obj = bpy.data.objects.new(name="Font Object", object_data=font_curve)
                #print(texts)
                # -- Set scale and location
                obj.location = (-1, 1, 10)
                obj.scale = (0.75, 0.5, 0.5)
                bpy.context.scene.collection.objects.link(obj)
        if mytool.my_postprocesslist == "AggregatePoints":
            #Aggregate selected points
            templist = []
            tempxlist = []
            tempylist = []
            tempzlist = []
            for obj in bpy.context.selected_objects:
                if str(mytool.custompropertyname) in obj:
                    tempvalue = float((obj[str(mytool.custompropertyname)]))
                    templist.append(tempvalue)
                    tempxlist.append(obj["x"])
                    tempylist.append(obj["y"])
                    tempzlist.append(obj["z"])
            tempmedian = statistics.median(templist)
            tempsum = sum(templist)
            tempmean = tempsum / len(templist)
            tempmin = min(templist)
            tempmax = max(templist)
            #All points needs custom property x,y,z
            tempxlist = statistics.median(tempxlist)
            tempylist = statistics.median(tempylist)
            tempzlist = statistics.median(tempzlist)
            #Create an object to store values on
            if str(mytool.my_shapelist) == "Plane":
                bpy.ops.mesh.primitive_plane_add(location = (tempxlist,tempylist,tempzlist), size = float(mytool.my_size))
            elif str(mytool.my_shapelist) == "Cube":
                bpy.ops.mesh.primitive_cube_add(location = (tempxlist,tempylist,tempzlist), size = float(mytool.my_size))
            elif str(mytool.my_shapelist) == "Sphere":
                bpy.ops.mesh.primitive_uv_sphere_add(radius = (float(mytool.my_size) / 2), location = (tempxlist,tempylist,tempzlist))
            elif str(mytool.my_shapelist) == "Cylinder":
                bpy.ops.mesh.primitive_cylinder_add(radius = (float(mytool.my_size) / 2), depth=0.01, location = (tempxlist,tempylist,tempzlist))
            ob = bpy.context.object
            me = ob.data
            bpy.context.object.name = 'Aggregate'
            me.name = 'AggregateMesh'
            ob[str(mytool.custompropertyname) + "_med"] = tempmedian
            ob[str(mytool.custompropertyname) + "_sum"] = tempsum
            ob[str(mytool.custompropertyname) + "_mean"] = tempmean
            ob[str(mytool.custompropertyname) + "_min"] = tempmin
            ob[str(mytool.custompropertyname) + "_max"] = tempmax
            ob["ICEName"] = "Custom"
            ob["ICEGroup"] = "Selection"
        if mytool.my_postprocesslist == "AggregatePoints2Zones":
            #Go throuogh all zones
            objects = bpy.context.scene.objects
            for tempzone in objects:
                if "ICEType" in tempzone:
                    if tempzone["ICEType"] == "Zone":
                        #print(tempzone["ICEName"])
                        templist = []
                        #Go trough all points
                        for temppoint in objects:
                            if "ICEType" in temppoint:
                                if temppoint["ICEType"] == "Point":
                                    if temppoint["ICEZone"] == tempzone["ICEName"]:
                                        tempvalue = float((temppoint[str(mytool.custompropertyname)]))
                                        templist.append(tempvalue)
                        if templist: #Not empty
                            tempmedian = statistics.median(templist)
                            tempsum = sum(templist)
                            tempmean = tempsum / len(templist)
                            tempmin = min(templist)
                            tempmax = max(templist)
                            tempzone[str(mytool.custompropertyname) + "_med"] = tempmedian
                            tempzone[str(mytool.custompropertyname) + "_sum"] = tempsum
                            tempzone[str(mytool.custompropertyname) + "_mean"] = tempmean
                            tempzone[str(mytool.custompropertyname) + "_min"] = tempmin
                            tempzone[str(mytool.custompropertyname) + "_max"] = tempmax
        return {'FINISHED'}
#class WM_OT_ReadResult(Operator):
#    bl_label = "Read Result from Simulation"
#    bl_idname = "wm.read_result"
#    bl_description = "Read and visualize result"

#    def execute(self, context):
#        scene = context.scene
#        mytool = scene.my_tool
#        #Just for fun, create daylight grid out of sferes, lots of them
#        #root = r'C:\Temp\idamod48'
#        #list_of_files = glob.glob('C:\Temp\idamod48/building1/**/*.pnt', recursive=True)
#        #latest_file = max(list_of_files, key=os.path.getctime)
#        #print(list_of_files)
#
#        # Folder Path
#        path = "C:\Temp\idamod48\building1\temp6451848\tmp"
#        # Change the directory
#        os.chdir(path)
#        # Read text File
#        def read_text_file(file_path):
#            with open(file_path, 'r') as f:
#                print(f.read())
#        # iterate through all file
#        for file in os.listdir():
#            # Check whether file is in text format or not
#            if file.endswith(".txt"):
#                file_path = f"{path}\{file}"
#                # call read text file function
#                read_text_file(file_path)
#
#        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.15,enter_editmode=False, align='WORLD' location=(x, y, z), scale=(1, 1, 1))
#        return {'FINISHED'}
# ------------------------------------------------------------------------
#    Menus
# ------------------------------------------------------------------------

class OBJECT_MT_CustomMenu(bpy.types.Menu):
    bl_label = "Select"
    bl_idname = "OBJECT_MT_custom_menu"

    def draw(self, context):
        layout = self.layout
        # Built-in operators
        layout.operator("object.select_all", text="Select/Deselect All").action = 'TOGGLE'
        layout.operator("object.select_all", text="Inverse").action = 'INVERT'
        layout.operator("object.select_random", text="Random")

# ------------------------------------------------------------------------
#    Panel in Object Mode
# ------------------------------------------------------------------------

class OBJECT_PT_ICEBridgePanel1(Panel):
    bl_label = "Settings"
    bl_idname = "OBJECT_PT_ICEBridge_panel1"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "ICE Bridge"
    bl_context = "objectmode"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        mytool = scene.my_tool

        layout.prop(mytool, "my_version", text="")
        layout.prop(mytool, "scriptfolder_path")
        layout.prop(mytool, "externalobjetcsfolder_path")
        layout.prop(mytool, "IDAICEfolder_path")
        layout.prop(mytool, "IDAICEAPIfolder_path")
        layout.prop(mytool, "model_path")
        layout.prop(mytool, "CSV_path")
        layout.prop(mytool, "H5_path")
        #layout.prop(mytool, "IDAICETempfolder_path")
        #row = layout.row()   # A new row
        #layout.operator("wm.loadsavesettings", icon="FILE_REFRESH") #This buton is scary

class OBJECT_PT_ICEBridgePanel2(Panel):
    bl_label = "Select Objects"
    bl_idname = "OBJECT_PT_ICEBridge_panel2"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "ICE Bridge"
    bl_context = "objectmode"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        mytool = scene.my_tool
        layout.menu(OBJECT_MT_CustomMenu.bl_idname, text="Presets", icon="SCENE")
        layout.prop(mytool, "my_filterlist", text="Filter")
        row = layout.row()   # A new row
        row.prop(mytool, "filtername")
        #Only enable used input
        if bpy.context.scene.my_tool.my_filterlist == "IFCSpaceLongName" or bpy.context.scene.my_tool.my_filterlist == "CustomProperty":
            row.enabled = True
        if bpy.context.scene.my_tool.my_filterlist != "IFCSpaceLongName" and bpy.context.scene.my_tool.my_filterlist != "CustomProperty":
            row.enabled = False
        row = layout.row()   # A new row
        layout.operator("wm.select_filtered_objects", icon="SELECT_INTERSECT")

class OBJECT_PT_ICEBridgePanel3(Panel):
    bl_label = "Object Operations"
    bl_idname = "OBJECT_PT_ICEBridge_panel3"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "ICE Bridge"
    bl_context = "objectmode"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        mytool = scene.my_tool
        layout.prop(mytool, "my_objectoperationlist", text="")
        row = layout.row(align = True)   # Focus on this row
        #Only enable used input
        if bpy.context.scene.my_tool.my_objectoperationlist == "ColorObject":
            row.enabled = True
        if bpy.context.scene.my_tool.my_objectoperationlist != "ColorObject":
            row.enabled = False
        row.prop(mytool, "my_colorlist")
        row.prop(mytool, "my_colortransparency")
        row = layout.row()   # A new row
        row = layout.row(align = True)   # Focus on this row
        #Only enable used input
        if bpy.context.scene.my_tool.my_objectoperationlist == "MoveGivenZ" or bpy.context.scene.my_tool.my_objectoperationlist == "ExtrudeGivenDistance" or bpy.context.scene.my_tool.my_objectoperationlist == "MoveToGivenZ" or bpy.context.scene.my_tool.my_objectoperationlist == "ExtrudeToGivenZ":
            row.enabled = True
        if bpy.context.scene.my_tool.my_objectoperationlist != "MoveGivenZ" and bpy.context.scene.my_tool.my_objectoperationlist != "ExtrudeGivenDistance" and bpy.context.scene.my_tool.my_objectoperationlist != "ExtrudeToGivenZ" and bpy.context.scene.my_tool.my_objectoperationlist != "MoveToGivenZ":
            row.enabled = False
        row.prop(mytool, "my_height")
        row = layout.row()   # A new row
        layout.operator("wm.perform_operation", icon="PLAY")

class OBJECT_PT_ICEBridgePanel4(Panel):
    bl_label = "IDA ICE Script"
    bl_idname = "OBJECT_PT_ICEBridge_panel4"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "ICE Bridge"
    bl_context = "objectmode"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        mytool = scene.my_tool
        #Drop down list with export options
        layout.prop(mytool, "my_exportobjectlist", text="")
        row = layout.row()   # A new row
        #if bpy.context.scene.my_tool.my_exportobjectlist == "BuildingBodies" or bpy.context.scene.my_tool.my_exportobjectlist == "Zones" or bpy.context.scene.my_tool.my_exportobjectlist == "BuildingBodiesAndZones":
            #row.enabled = True
        #else:
        #if bpy.context.scene.my_tool.my_exportobjectlist != "BuildingBodies" and bpy.context.scene.my_tool.my_exportobjectlist != "Zones" and bpy.context.scene.my_tool.my_exportobjectlist != "BuildingBodiesAndZones":
            #row.enabled = False

        row.prop(mytool, "my_fileformatlist")

        row = layout.row()   # A new row
        row.prop(mytool, "groupname")
        row = layout.row()   # A new row
        #Only enable used input
        if bpy.context.scene.my_tool.my_exportobjectlist == "BuildingBodiesFromRoof" or bpy.context.scene.my_tool.my_exportobjectlist == "PrismaticBuildingBodies" or bpy.context.scene.my_tool.my_exportobjectlist == "PrismaticZones":
            row.enabled = True
        else:
        #if bpy.context.scene.my_tool.my_exportobjectlist != "BuildingBodiesFromRoof" and bpy.context.scene.my_tool.my_exportobjectlist != "PrismaticBuildingBodies" and bpy.context.scene.my_tool.my_exportobjectlist != "PrismaticZones":
            row.enabled = False
        row.prop(mytool, "my_prismaticheight")

        row = layout.row()   # A new row
        #Only enable used input
        if bpy.context.scene.my_tool.my_exportobjectlist == "ExternalObjects":
            row.enabled = True
        if bpy.context.scene.my_tool.my_exportobjectlist != "ExternalObjects":
            row.enabled = False

        row = layout.row(align = True)   # Focus on this row
        #Only enable used input
        if bpy.context.scene.my_tool.my_exportobjectlist == "ExternalObjects":
            row.enabled = True
        else:
            row.enabled = False
        row.prop(mytool, "my_shadingbool")
        row.prop(mytool, "my_transparency")
        row = layout.row()   # A new row

        if bpy.context.scene.my_tool.my_exportobjectlist != "Doors" and bpy.context.scene.my_tool.my_exportobjectlist != "Windows" and bpy.context.scene.my_tool.my_exportobjectlist != "Windows2" and bpy.context.scene.my_tool.my_exportobjectlist != "Windows3":
            row.enabled = True
        else:
            row.enabled = False
        row.prop(mytool, "my_runIDAICE")
        layout.operator("wm.ice_export_script", icon="COPYDOWN")

class OBJECT_PT_ICEBridgePanel5(Panel):
    bl_label = "Post Process"
    bl_idname = "OBJECT_PT_ICEBridge_panel5"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "ICE Bridge"
    bl_context = "objectmode"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        mytool = scene.my_tool

        layout.prop(mytool, "my_postprocesslist")
        row = layout.row()   # A new row

        row.prop(mytool, "my_shapelist")
        row.prop(mytool, "my_size")
        row = layout.row()   # A new row

        row.prop(mytool, "custompropertyname")

        row = layout.row()   # A new row
        row.prop(mytool, "my_colorscale")

        row = layout.row()   # A new row
        row.prop(mytool, "my_minvalue")
        row.prop(mytool, "my_maxvalue")

        row = layout.row()   # A new row
        row.prop(mytool, "objecttext")

        row = layout.row()   # A new row
        layout.operator("wm.perform_command", icon="PLAY")


# ------------------------------------------------------------------------
#    Registration
# ------------------------------------------------------------------------

classes = (
    MyICEProperties,
    WM_OT_Export,
    WM_OT_PerformOperation,
    WM_OT_SelectFilteredObjects,
    WM_OT_PerformCommand,
    #WM_OT_ReadResult,
    #WM_OT_ClearScriptFolder,
    #WM_OT_LoadSaveSettings,
    OBJECT_MT_CustomMenu,
    OBJECT_PT_ICEBridgePanel1,
    OBJECT_PT_ICEBridgePanel2,
    OBJECT_PT_ICEBridgePanel3,
    OBJECT_PT_ICEBridgePanel4,
    OBJECT_PT_ICEBridgePanel5,
)

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    bpy.types.Scene.my_tool = PointerProperty(type=MyICEProperties)

def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
    del bpy.types.Scene.my_tool

if __name__ == "__main__":
    register()

#Help functions
#Functions for creating bouding boxes
def get_box_by_selected_objects_with_vec_quaternion(q):
    q_invert = q.inverted()
    verts = []
    for obj in bpy.context.selected_objects:
        obj_mat = obj.matrix_world
        if obj.type != 'MESH': continue
        verts += [q_invert @ (obj_mat @ v.co) for v in obj.data.vertices]
    if not verts: return None

    v_z = [co.z for co in verts]
    v_y = [co.y for co in verts]
    v_x = [co.x for co in verts]

    z_max = max(v_z)
    z_min = min(v_z)
    y_max = max(v_y)
    y_min = min(v_y)
    x_max = max(v_x)
    x_min = min(v_x)

    box_verts = (
        (x_min, y_min, z_min),
        (x_min, y_max, z_min),
        (x_max, y_max, z_min),
        (x_max, y_min, z_min),
        (x_max, y_min, z_max),
        (x_min, y_min, z_max),
        (x_min, y_max, z_max),
        (x_max, y_max, z_max),
    )

    box_verts = [q @ Vector(v) for v in box_verts]

    bpy.ops.mesh.primitive_cube_add(size=2, enter_editmode=False, align='WORLD', location=(0, 0, 0), scale=(1, 1, 1))
    cube = bpy.context.object
    verts = cube.data.vertices

    verts[0].co = box_verts[0]
    verts[2].co = box_verts[1]
    verts[6].co = box_verts[2]
    verts[4].co = box_verts[3]
    verts[5].co = box_verts[4]
    verts[1].co = box_verts[5]
    verts[3].co = box_verts[6]
    verts[7].co = box_verts[7]

    #cube.display_type = 'WIRE'
    return cube

def get_cube_by_selected_objects():
    verts = []
    for obj in bpy.context.selected_objects:
        if obj.type != 'MESH': continue
        verts += [obj.matrix_world @ v.co for v in obj.data.vertices]
    if not verts: return None

    points = np.asarray(verts)
    means = np.mean(points, axis=1)

    cov = np.cov(points, y = None,rowvar = 0,bias = 1)

    v, vect = np.linalg.eig(cov)

    tvect = np.transpose(vect)
    points_r = np.dot(points, np.linalg.inv(tvect))

    co_min = np.min(points_r, axis=0)
    co_max = np.max(points_r, axis=0)

    xmin, xmax = co_min[0], co_max[0]
    ymin, ymax = co_min[1], co_max[1]
    zmin, zmax = co_min[2], co_max[2]

    xdif = (xmax - xmin) * 0.5
    ydif = (ymax - ymin) * 0.5
    zdif = (zmax - zmin) * 0.5

    cx = xmin + xdif
    cy = ymin + ydif
    cz = zmin + zdif

    corners = np.array([
        [cx - xdif, cy - ydif, cz - zdif],
        [cx - xdif, cy + ydif, cz - zdif],
        [cx - xdif, cy + ydif, cz + zdif],
        [cx - xdif, cy - ydif, cz + zdif],
        [cx + xdif, cy + ydif, cz + zdif],
        [cx + xdif, cy + ydif, cz - zdif],
        [cx + xdif, cy - ydif, cz + zdif],
        [cx + xdif, cy - ydif, cz - zdif],
    ])

    corners = np.dot(corners, tvect)
    # center = np.dot([cx, cy, cz], tvect)
    mat = bpy.context.object.matrix_world

    bpy.ops.mesh.primitive_cube_add(enter_editmode=False, align='WORLD', location=(0, 0, 0), scale=(1, 1, 1))
    cube = bpy.context.object
    verts = cube.data.vertices
    verts[0].co = corners[0]
    verts[2].co = corners[1]
    verts[6].co = corners[2]
    verts[4].co = corners[3]
    verts[5].co = corners[6]
    verts[1].co = corners[7]
    verts[3].co = corners[5]
    verts[7].co = corners[4]

    for obj in bpy.context.selected_objects:
        obj.select_set(False)
    bpy.context.view_layer.objects.active = obj
    cube.select_set(True)
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')
    #cube.display_type = 'WIRE'
    return cube

def create_lattice_by_cube(cube, del_org=True):
    "TODO"
    # you need find a way to change points position of the lattice

def copy_rot(tar, source):
    for obj in bpy.context.selected_objects:
        obj.select_set(False)
    tar.select_set(True)
    bpy.context.view_layer.objects.active = tar

    mat = source.matrix_world
    loc, rot, sca = mat.decompose()
    old_mode = tar.rotation_mode
    tar.rotation_mode = "QUATERNION"
    tar.rotation_quaternion = rot.inverted()
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    tar.rotation_quaternion = rot
    tar.rotation_mode = old_mode

#Function to determine largest object
def maximum(a, b):
    if a >= b:
        return a
    else:
        return b
#Function to create new material for selected objects
def get_random_color():
    ''' generate rgb using a list comprehension '''
    r, g, b = [random.random() for i in range(3)]
    return r, g, b, 1
#Function to return rgb based upon number values
def pseudocolor(val, minval, maxval, start_hue, stop_hue):
    """ Convert val in range minval..maxval to the range start_hue..stop_hue
        degrees in the HSV colorspace.
    """
    h = (float(val-minval) / (maxval-minval)) * (stop_hue-start_hue) + start_hue

    # Convert hsv color (h,1,1) to its rgb equivalent.
    # Note: hsv_to_rgb() function expects h to be in the range 0..1 not 0..360
    r, g, b = hsv_to_rgb(h/360, 1., 1.)
    return r, g, b

#Functions for reading H5-files from IDA ICE
def UDI_eval(path, plane, year, sim_type, ill_min, ill_max):
    """Evaluates UDI on a desired measuring plane.
       The h5 file should contain a field called time
       that includes all time-stamps

    Parameters
    ----------
    path : str
        The path to the h5 file to be read
    plane: str
        The name of the plane to be assessed
    year: int
        The simulated year
    sim_type: str
        The type of simulation. Takes Radiance or Radiosity
    ill_min: int
        The minimum illuminance threshold
    ill_max: int
        The maximum illuminance threshold
    Returns
    -------
    udi_res
        percentage of points that fulfill the requirements
    """

    h5f = h5py.File(path, 'r')
    if sim_type == 'Radiosity':
        ill = np.array(h5f[plane + '/' + 'Illum' + '/data'])
        time = list(h5f[plane + '/time/data'])
    else:
        ill = np.array(h5f[plane + '/' + 'ill_controlled' + '/data'])
        #ill = np.array(h5f[plane + '/' + 'ill_none_drawn' + '/data'])
        time = list(h5f[plane + '/time/data'])
    h5f.close()

    df = pd.DataFrame()
    df['x'] = np.nan
    df['y'] = np.nan
    df['z'] = np.nan
    df['udi_24hr'] = np.nan
    df['udi_08to18'] = np.nan

    for z in range(ill.shape[0]):
        for y in range(ill.shape[1]):
            for x in range(ill.shape[2]):
                cur_res = pd.DataFrame()
                cur_res['Datetime'] = pd.to_datetime(time, origin = pd.Timestamp(str(year) + '-01-01'), unit = 's')
                cur_res['ill'] = ill[z, y, x, :]
                cur_res = cur_res.set_index('Datetime')
                udi_tot = round(len(cur_res[(cur_res['ill'] >= ill_min) & (cur_res['ill'] <= ill_max)])/cur_res.shape[0], 2)

                cur_res['Hour'] = cur_res.index.hour
                cur_res['Day'] = cur_res.index.weekday
                cur_res = cur_res[(cur_res['Hour'] >= 8) & (cur_res['Hour'] < 18)]
                udi_sub = round(len(cur_res[(cur_res['ill'] >= ill_min) & (cur_res['ill'] <= ill_max)])/cur_res.shape[0], 2)

                df.loc[df.shape[0]] = [x, y, z, udi_tot, udi_sub]
    return df

def local2global(pt_loc, axis):
    """Transforms local coordinates relative to a measuring plane origo
       to the global coordinate system/building origo.

    Parameters
    ----------
    pt_loc : array
        an array that contains the coordinates of the point [x, y, z]
    axis : array
        the array that is stored in 'measuring_plane/polygon/axis' where the first
        column is the coordinates of the local axis coordinate in respect to the
        global origo, the second column is the direction of the local x-axis and
        the third column is the direction of the local y-axis relative to the global
        coordinate system.
        example: np.array(df['measuring_plane/polygon/axis'])

    Returns
    -------
    pt_glob
        array with the transformed coordinates of the point
    """
    T = np.transpose(axis)[0]
    x1 = np.transpose(axis)[1]
    y1 = np.transpose(axis)[2]

    R = np.array([x1, y1, np.cross(x1,y1)/(np.linalg.norm(np.cross(x1,y1)))])

    pt_glob = np.matmul(pt_loc, R) + T

    return list(pt_glob)




