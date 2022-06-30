# ICEBridge

Blender plugin to send BIM data to IDA ICE

## Requirements
To run this plugin you need Blender (https://www.blender.org/). To get BIM-data into Blender I recommend BlenderBIM (https://blenderbim.org/) and Speckle (https://speckle.systems/). It also helps if you have access to Revit and/or ArchiCAD, at least demo versions. To import the data you need IDA ICE (https://www.equa.se/en/ida-ice).

## Installation
Download ICEBridge.zip and install as a normal Blender plugin. Instructions can be found here https://docs.blender.org/manual/en/latest/editors/preferences/addons.html

![This is an image](https://github.com/maxtillberg/ICEBridge/blob/main/ICEBridge.png)

## Usage

1. Create or import BIM- or CAD-data to Blender. 
2. Make sure that the data is valid.

  Zones and building bodies must be made up of closed volumes constructed out of planar surfaces. Each mesh will create a separate zone or building body.
  
  Windows and doors works best if they are planar. Each mesh will create a separate window or door.
3. Select objects of one type with similar properties, for example zones. Supported objects are building bodies, zones, windows, doors and external (shading) objects.
4. Select the corresponding object type in ICEBridge, path and press "Export to IDA ICE". This will generate a script file and geometry files in the selected folder path. Exporting the same object type twice will overwrite the script file and geometries with the same name.
5. Open IDA ICE and run the generated script. The scripts can be run in any order but windows and doors need to have building bodies to be placed on.

## Limitations

This is a proof of concept, not an official product by Equa. There will be bugs and limitations.
- Windows and doors must be rectangular.
- Windows and doors can only be placed in building bodies. Windows can be moved to zones manually.
- Sloped roof windows can be created smaller than the original windows. This is a bug.
- Windows and doors must not overlap building bodies. If they are larger, you need to divide them or merge the building bodies.

## Input

ICEBridge works well with BlenderBIM and Speckle but any valid geometry will work.

## Notes

- Windows and doors import best if the center of origin is the to center of mass (surface)
- Windows and doors import best if the rotation is not transformed.
- The import can be quite slow, therefore it can be a good idea to export/import larger buildings in parts, for example each floor.
- Building bodies can be created in Revit by deleting room bounding walls, floors and ceilings.
- Spaces can be created from any closed volume, for example Revit rooms or spaces or IFCSpaces.
- Building bodies and zones should if possible be created as objects that can be created in IDA ICE to be editable.
- Building bodies can be edited in IDA ICE if needed.
- External objects with similar properties can be merged into one mesh to avoid too many objects.
- Do not import too large shading external objects since this will affect shading calculations. Try to simplify external objects if possible.

