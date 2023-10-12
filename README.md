SupCom_Import_Export_Blender
============================

Python scripts to import and export Supreme Commander units (.scm) and animations (.sca) in Blender.

Setting up the plugins :
------

Download the importer and exporter files from the github repo. They are counted as separate plugins.

These scripts are installed just like other blender plugins:
You can then place them into your plugins directory: `BlenderInstallDir/BlenderVersion/scripts/addons`
Then you can enable them in the user preferences, in the plugins section. There will be two plugins, import and export, under the Import/Export category.

Importing :
------
- You can import .scm models from Supreme commander, find the corresponding model in the game files (units.scd)

- To import animations (.sca), you have to have already loaded a model on Blender, either the corresponding mesh (.scm), or a custom mesh of your own, with the bones corresponding in names with the animation bones (each bone named in the animation must have a corresponding one with the same name in the mesh).

- Animation import is functional, but due to supcom file format reasons, the file is filled with keyframes for every frame, making it nearly impossible to edit.

Exporting :
------

- The exporter deals with one armature at a time. You can hide any armatures you dont want to be taken into account.

- All vertices must be in a "Vertex Group", and each vertex group must have the name of a bone. If some vertices are not moving, just assign them to the group with the base bone as bonename. The exporter will put you into edit mode and select all non-assigned vertices if your mesh contains them.

- When exporting, the script will assume the unit name (and so the .scm filename) from the name of your armature. So you'll have only to select the output folder, filenames will be deduced.

- It is recommended to triangulate the mesh. Quads and ngons are now supported, but in general triangulating gives more control over the mesh.

- Vertices at the same location will be merged, unless they are part of a sharp edge. Supcom uses merged vertices for smooth shading. To get hard shading, set the edges you want to sharp. Nothing else is required. The exporter will not merge them together.

known bugs :
- Models exported by this will work fine in the game, but importing them into 3dsMax with the 3ds importer is erratic and buggy due to how blender orders its vertices. I have a partial fix in another repository for the 3ds exporter here:

Exporting Animations :
------

- When exporting, the script will assume the filename for the animation from the action name in Blender (can be seen in the NLA editor). So you'll have only to select the output folder, filenames will be deduced.

- When exporting animations, you need to have the armature with that animation selected.

- An animation must be associated with an action (see the NLA editor).

- Multiple animations are now supported: the exporter will export each animation in your model separately.

Old blender versions :
------
If you are using blender 2.79 there is a version of the plugin on the 2.79 branch, though it has fewer features so using it isn't recommended.

Credits to dan & Brent for the original version and all the engineering work. Thanks to Oygron for porting it to 2.71.
