# ICEBridge

![This is an image](https://github.com/maxtillberg/ICEBridge/blob/main/icebridge.png)

[Blender](https://www.blender.org/) or [grasshopper](https://www.grasshopper3d.com/) plugin to send BIM-data like IFC to [IDA ICE](https://www.equa.se/en/ida-ice).

## Requirements

To run this plugin, you need [Blender](https://www.blender.org/) and [BlenderBIM](https://blenderbim.org/) or [Rhino](https://www.rhino3d.com/). I recommend installing [Speckle](https://speckle.systems/) and [dotBIM](https://dotbim.net/) as well. It also helps if you have access to Revit and/or ArchiCAD, at least demo versions. To import the data you need [IDA ICE](https://www.equa.se/en/ida-ice). Some features requires the usage of the IDA ICE API. 

## Installation

### Blender

Download and install [ICEBridge.zip](https://github.com/maxtillberg/ICEBridge/blob/main/ICEBridge.zip) and [io_scene_3ds.zip](https://github.com/maxtillberg/ICEBridge/blob/main/io_scene_3ds.zip) as a normal Blender plugins. Instructions can be found [here](https://docs.blender.org/manual/en/latest/editors/preferences/addons.html)

### Rhino/grasshopper

This is still under development and will be delivered by request.

### IDA ICE 4.8

To run some of the ICEBridge scripts you need to install a few custom patches and a plugin in IDA ICE.
- IDA NKS Extension v0.3. This can be downloaded [here](https://files.equa.se/courses/ice-nks-03.exe). Run the file to install it. Make sure to select the correct installation of IDA ICE you want to install it to. 
- Patches that can be downloaded [here](https://files.equa.se/courses/ice_patches.zip).
Extract the patches and place them in the ice.patches folder. This should be located at ida\lib\ice\ice.patches\ where "ida" is the IDA ICE installation folder, probably “IDA48” or something similar. Create the folder ice.patches If this does not exist. Restart IDA ICE after the files is installed. Due to security settings in Windows, you 
might extract the files in a separate folder and move them manually.
- Some features requires the usage of the IDA ICE API. Thhis can be optained from EQUA and requires a special license.

Note that these files are not a part of ICEBridge.

![This is an image](https://github.com/maxtillberg/ICEBridge/blob/main/ICEBridge.png)

## Usage
  
1. Create or import BIM- or CAD-data to Blender using BlenderBIM, Speckle, DOTBIM or CAD data as OBJ or DXF. 
2. Make sure that the data is valid. Zones and building bodies must be made up of closed volumes constructed out of planar surfaces or planar surfaces that can be extruded into volumes. Each mesh will create a separate zone or building body. Windows and doors works best if they are planar. Each mesh will create a separate window or door.
3. Select objects of one type with similar properties, for example zones. Supported objects are building bodies, zones, windows, doors and external (shading) objects.
4. Select the corresponding object type in ICEBridge, path and press "Export to IDA ICE". This will generate a script file and optionaly geometry files in the selected folder path. Exporting the same object type twice will overwrite the script file and geometries with the same name.
5. Open IDA ICE and run the generated script. The scripts can be run in any order but windows and doors need to have building bodies to be placed on.

## Limitations
  
This is a proof of concept, not an official product by Equa. There will be bugs and limitations.

## Input

ICEBridge works well with BlenderBIM and Speckle but any valid geometry will work.

## News

- 2023-11-14: Version 0.9.4 Create measuring plane circles and spheres based upon CSV-files with data and name. Requires custom installation of h5py, Select objects based upon custom property, Color selected object with custom property value (colorscale, max, min), Set ICEName to IFCName, Set ICEName to IFCLongName, Set IFCName to SpeckleName, Set IFCName to SpeckleDescription, Set ICEGroup to IFCLongName, Set ICEGroup to SpeckleDescription, Import Room data from CSV, Set objects to color black, Create custon geometry based upon selected objects with same pcustom properties, Color scale with unit and 11 values when something is logged, old one removed,  Possibility to select scale, Possibility to select all font objects, Convert selected fonts to meshes, Filter objects according to content in type, Export IceGroup as grpup for thermal zones if available, Option to only create zones from volumes by deleting building bodies automaticly, Temp bounding zones added and deleted automaticly, Bounding building body removed, Clear materials of selected objects, Convert H5-files with illuminance to custom CSV with custom UDI, requires that h5py is installed, Faster import of zones based upon volumes by importing into temp locations, Move building bodies and zones in IDA ICE in Z, Set custom ICEName and GroupName, Make planar surface out of window in mid position, ICEType: Zone, Point, Window, Door, Building. Used for future features, New custom properties: ICEType, ICEZone, ICEBuilding, Aggregate selected points to new geometry, Aggregate points to Zones.
- 2023-08-21: Version 0.9.3 Random colors of selected objects. Useful for exporting .3DS-files into unique building bodies and spaces. Create and color space boundaries. Useful for ESBO. New ice.exe path. New API Path. Useful for future features. Requires that the IDA ICE 64 bit API is installed. Change default color/material properties for 3DS-files rendering in IDA ICE. Create idm-files for prismatic building bodies and zones. Filter custom IFC longname. Bugfixes
- 2023-05-31: Version 0.9.2 Export as 3DS. This requires separate plugin since Blender >2.8 and < 4.0 does not support 3DS export. This plugin can be downloaded [here](https://github.com/maxtillberg/ICEBridge/blob/main/io_scene_3ds.zip), Align object according to selected surface, Make objects selectable/non selectable.
- 2023-02-08: Version 0.9.1 Bug fixes.
- 2023-01-29: Version 0.9.0 Custom Names can be created for all objects, Removed clear temp folder button, Script for moving windows between building bodies and zones, Script for creating big bounding box in IDA ICE, Always group external objects and always create obj-files, Fill external walls with windows, Note that they cannot be named automatically, Script to delete zones with optionally given name, Script to delete building bodies with optionally given name, New operations for making objects non selectable/selectable, Hide/show imported objects by scale with optionally given name, Single bounding box aligned with last selected object
- 2022-12-21: Version 0.8.8 Faster external scripts, bug fixes.
- 2022-11-03: Version 0.8.7 Possible to run scripts directly from Blender. This is only possible for scripts that creates OBJ-files.
- 2022-11-01: Version 0.8.6 External shading objects can be imported without manual renaming.
- 2022-10-31: Version 0.8.5 New window export function that uses temp zones and a custom script. This method deletes all existing  zones and may create stray windows in corners depending on the bounding box of the window. The method ignores BIM-data.


## Notes
  
- Windows and doors created using the NKS-plugin should have center of origin set to the geometrical center of the object.
- Windows and doors import best if the rotation is not transformed.
- The 3D import can be quite slow, therefore it can be a good idea to export/import larger buildings in parts, for example each floor.
- It is faster to import zones and building bodies without geometries.
- Importing without geometry will make zones non editable in IDA ICE and building bodies are more often non editable.
- Coplanar surfaces will not be merged automatically  if import without geometry is used.
- Building bodies can be created in Revit by deleting room bounding walls, floors and ceilings.
- Spaces can be created from any closed volume, for example Revit rooms or spaces or IFCSpaces.
- Building bodies and zones should if possible be created as objects that can be created in IDA ICE to be editable.
- Building bodies can be edited in IDA ICE if needed.
- External objects with similar properties are merged into one mesh to avoid too many objects.
- Do not import too large shading external objects since this will affect shading calculations. Try to simplify external objects if possible.
