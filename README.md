# ICEBridge

Blender plugin to send BIM data to [IDA ICE]([https://files.equa.se/courses/ice_patches.zip](https://www.equa.se/en/ida-ice)).

![This is an image](https://github.com/maxtillberg/ICEBridge/blob/main/ICEBridge.png)

## Requirements

To run this plugin you need Blender (https://www.blender.org/) and BlenderBIM (https://blenderbim.org/). I recomend to install Speckle (https://speckle.systems/) and dotBIM (https://dotbim.net/) as well. It also helps if you have access to Revit and/or ArchiCAD, at least demo versions. To import the data you need IDA ICE (https://www.equa.se/en/ida-ice).

## Installation

### Blender

Download ICEBridge.zip and install as a normal Blender plugin. Instructions can be found here https://docs.blender.org/manual/en/latest/editors/preferences/addons.html

### IDA ICE 4.8

To run some of the ICEBridge scripts you need to install a few custom patches and a plugin in IDA ICE.
- IDA NKS Extension v0.3. This can be downloaded [here](https://files.equa.se/courses/ice-nks-03.exe). Run the file to install. Make sure to select the correct installation of IDA ICE you want to install it to. 
- Patches that can be downloaded [here](https://files.equa.se/courses/ice_patches.zip).
Extract the patches and place them in the ice.patches folder. This should be located at <ida>\lib\ice\ice.patches\ (<ida> is the installation folder, probably “IDA48” or something similar). Create the folder ice.patches If this does not exist. Restart IDA ICE after the files is installed. Due to security settings in Windows, you 
might extract the files in a separate folder and move them manually.
Note that these files are not a part of ICEBridge.

## Usage
  
1. Create or import BIM- or CAD-data to Blender using BlenderBIM, Speckle, DOTBIM or CAD data as OBJ or DXF. 
2. Make sure that the data is valid. Zones and building bodies must be made up of closed volumes constructed out of planar surfaces or planar surfaces that can be extruded into volumes. Each mesh will create a separate zone or building body. Windows and doors works best if they are planar. Each mesh will create a separate window or door.
3. Select objects of one type with similar properties, for example zones. Supported objects are building bodies, zones, windows, doors and external (shading) objects.
4. Select the corresponding object type in ICEBridge, path and press "Export to IDA ICE". This will generate a script file and optionaly geometry files in the selected folder path. Exporting the same object type twice will overwrite the script file and geometries with the same name.
5. Open IDA ICE and run the generated script. The scripts can be run in any order but windows and doors need to have building bodies to be placed on.

## Limitations
  
This is a proof of concept, not an official product by Equa. There will be bugs and limitations.
- Windows and doors will be rectangular.
- Windows and doors can only be placed in building bodies. Windows can be moved to zones manually.
- Windows and doors must not overlap building bodies. If they are larger, you need to divide them or merge the building bodies.

## Input

ICEBridge works well with BlenderBIM and Speckle but any valid geometry will work.

## News
  
- 2023-01-29: Version 0.9.0 Custom Names can be created for all objects, Removed clear temp folder button, Script for moving windows between building bodies and zones, Script for creating big bounding box in IDA ICE, Allways group external objects and allways create obj-fies, Fill external walls with windows, Note that they can not be named automaticly, Script to delete zones with optionally given name, Script to delete building bodies with optionally given name, New operations for making objects non selectble/selectable, Hide/show imported objects by scale with optionally given name, Single bounding box aligned with last selected bject
- 2023-01-16: Version 0.8.9 Same geo-referencing in the exported scripts from BlenderBIM as the BIM-import in IDA ICE.
- 2022-12-21: Version 0.8.8 Faster external scripts, bug fixes.
- 2022-11-03: Version 0.8.7 Possible to run scripts directly from Blender. This is only possible for scripts that creates OBJ-files.
- 2022-11-01: Version 0.8.6 External shading objects can be imported without manual renaming.
- 2022-10-31: Version 0.8.5 New window export function that uses temp zones and a custom script. This method deletes all exsisting zones and may create stray windows in corners depending on the bounding box of the window. The method ignores BIM-data.


## Notes
  
- Windows and doors should have center of origin is the to center of mass (surface)
- Windows and doors import best if the rotation is not transformed.
- The import can be quite slow, therefore it can be a good idea to export/import larger buildings in parts, for example each floor.
- It is faster to import zones and building bodies without geometries.
- Importing without geometry will make zones non editable in IDA ICE and building bodies are more often non editable.
- Coplanar surfaces will not be merged automaticly if import without geometry is used.
- Building bodies can be created in Revit by deleting room bounding walls, floors and ceilings.
- Spaces can be created from any closed volume, for example Revit rooms or spaces or IFCSpaces.
- Building bodies and zones should if possible be created as objects that can be created in IDA ICE to be editable.
- Building bodies can be edited in IDA ICE if needed.
- External objects with similar properties can be merged into one mesh to avoid too many objects.
- Do not import too large shading external objects since this will affect shading calculations. Try to simplify external objects if possible.

