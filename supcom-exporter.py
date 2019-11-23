#!BPY

#**************************************************************************************************
# Supreme Commander Exporter for Blender3D - www.blender3d.org
#
# Written by dan - www.sup-com.net), Brent (www.scmods.net)
#
# further improvements by GeomanNL and Darius
#
# History
#
# 0.1.0  2006-07-02    Dan Initial version.
#
# 0.2.0   2007-03-11    Brent Fixed UV coords, V was inverted.
#                Support for exporting quads.
#                Fixed a padding issue.
#
# 0.3.0   2007-03-18    Dan Code refactoring / Clean up.
#                Fixed 'INFO' section size in header.
#
# 0.3.3  2007-09-25    GeomanNL  fixed a file-write bug
#                orientation fix, changed to matrix rotation
#                other excellent stuff
#                (me darius took the freedom to write your entry:D)
#
# 0.3.5  2009-03-20    Darius_  tangent and binormal calc
#                vertex optimation
#                blender front to supcom front
#                some more fixes and reorganizing/cleanup code
#
# 0.4.0  2014-07-13 Oygron   Script ported to Blender 2.71
#
# 0.4.1  2019-09-19 [e]Exotic_Retard
#               support for smooth and hard edges added
#               support for multiple animations added
# 0.4.2  2019-10-03 [e]Exotic_Retard
#               change padding size from 32 bit to 16 bit, thats how the max plugin does it
#               change padding character from X to Å; thats how it is in the base game models, and the max plugin breaks if it doesnt see them
#               fix an issue with animation exports when there are multiple objects with actions
# 0.4.3  2019-11-06 [e]Exotic_Retard
#               made the scm export several times faster, especially on large models, where the speedup is from minutes to seconds
# 0.4.4  2019-11-23 [e]Exotic_Retard
#               Fixed support for many bones in the model - now up to 256 linked and 256^2 empty bones
#
# Todo
#   - GUI improvements
#   - Support for LOD exporting. Eg. not merging all meshes for an armature into one mech but rather only
#     sub-meshes and export the top level meshes to different files.
#   - Validation, ensure that
#     - Prompt before overwriting files & check that directories exists
#   - Second UV set?
#   - Set animation time per frame
#   - Export LUA script for use in the animation viewer (eg, start anim, set texture etc)..
#   - Set root rot/pos for sca
#   - Progress bar
#   - Support for exporting different animation lengths
#
#**************************************************************************************************

bl_info = {
    "name": "Supcom Exporter",
    "author": "dan & Brent & Oygron, Updated by [e]Exotic_Retard",
    "version": (0,4,4),
    "blender": (2, 79, 0),
    "location": "File -> Export",
    "description": "Exports Supcom files",
    "warning": "",
    "wiki_url": "http://forums.gaspowered.com/"
                "viewtopic.php?t=17286",
    "category": "Import-Export",
}

import bpy

from bgl import *

from mathutils import *

import os
from os import path

import struct
import string
import math
from math import *
from bpy_extras.io_utils import unpack_list, unpack_face_list

from string import *
from struct import *
from bpy.props import *

VERSION = '4.2'

######################################################
# User defined behaviour, Select as you need
######################################################
#if you want to leave an info in your scm file put it in there
USER_INFO = ""


#Enable Progress Bar ( 0 = faster )
PROG_BAR_ENABLE = 1
#how many steps a progress bar has (the lesser the faster)
PROG_BAR_STEP = 25

#slower - reduce vertex amount
VERTEX_OPTIMIZE = 1

#LOG File for debuging
#Enable LOG File (0 = Disabled , 1 = Enabled )
LOG_ENABLE = 0
#Filename / Path. Default is blender directory Filename SC-E_LOG.txt
LOG_FILENAME = "SC-E_LOG.txt"

LOG_BONE = 0
LOG_VERT = 0


inError = 0

######################################################
# Init Supreme Commander SCM( _bone, _vertex, _mesh), SCA(_bone, _frame, _anim) Layout
######################################################

#Transform matrix        z -> yx -> xy -> z
xy_to_xz_transform = Matrix(([ 1, 0, 0],
                            [ 0, 0, -1],
                            [ 0, 1, 0])).to_4x4()
# Armature world matrix
MArmatureWorld = Matrix()
BONES = []
keyedBones = set()

ANIMATION_DURATION = 1.5
def my_popup(msg):
    global inError
    if inError == 0:
        inError = 1
        def draw(self, context):
            self.layout.label(msg)
        bpy.context.window_manager.popup_menu(draw, title="Error", icon='ERROR')
    

def my_popup_warn(msg):
    def draw(self, context):
        self.layout.label(msg)
    bpy.context.window_manager.popup_menu(draw, title="Warning", icon='ERROR')

def my_popup_info(msg):
    def draw(self, context):
        self.layout.label(msg)
    bpy.context.window_manager.popup_menu(draw, title="Info", icon='INFO')


class scm_bone :

    rest_pose = []
    rest_pose_inv = []
    rotation = []
    position = []
    parent_index = 0
    keyed = False
    used = False
    name = ""

    def __init__(self, name, rest_pose_inv, rotation, position, parent_index):

        self.rest_pose_inv = rest_pose_inv
        self.rotation = rotation
        self.position = position
        self.parent_index = parent_index
        self.keyed = False
        self.name = name

    def save(self, file):
        bonestruct = '16f3f4f4l'
        #4x4 matrix 
        #3 position
        #4 rotation
        #name offset
        #bone parent index
        #unknown
        
        
        rp_inv = [0] * 16

        icount = 0
        for irow in range(4):
            #rest pose_inv
            for icol in range(4):
                rp_inv[icount] = self.rest_pose_inv[irow][icol]
                icount = icount + 1

        bonedata = struct.pack(bonestruct,
            rp_inv[0], rp_inv[1], rp_inv[2], rp_inv[3],
            rp_inv[4], rp_inv[5], rp_inv[6], rp_inv[7],
            rp_inv[8], rp_inv[9], rp_inv[10],rp_inv[11],
            rp_inv[12],rp_inv[13],rp_inv[14],rp_inv[15],
            self.position[0],self.position[1],self.position[2],
            self.rotation.w,self.rotation.x,self.rotation.y,self.rotation.z, #Quaternion (w,x,y,z)#w,x,y,z
            self.name_offset, self.parent_index,
            0,0)

        file.write(bonedata)


class scm_vertex :

    global xy_to_xz_transform
    position = []
    tangent  = []
    normal   = []
    binormal = []
    uvc = 0
    uv1 = []
    uv2 = []
    bone_index = []

    def __init__(self, pos , no , uv1, bone_index, smoothEdgesList):

        self.position = pos
        self.normal   = no

        #tangent and binormal wil be calculated by face
        self.tangent  = Vector(( 0, 0, 0))
        self.binormal = Vector(( 0, 0, 0))

        self.uvc = 1
        self.uv1 = uv1
        self.uv2 = uv1# Vector(0,0) #uv1 #better results with copy ... strange, where is the use of that?
        self.smoothEdges = smoothEdgesList

        self.bone_index = bone_index


    def save(self, file):

        vertstruct = '3f3f3f3f2f2f4B'
        #3 position
        #3 normal
        #3 tangent
        #3 binormal
        #2 uv1
        #2 uv2
        #4 bone index, but we fill the first one with non-zero values

        #so finally we can norm because here it is sure that no tang norm will be added
        self.tangent.normalize()
        self.binormal.normalize()
        self.normal.normalize()

        if False : #why is this here
            self.tangent = Vector((0,0,0))
            self.binormal= Vector((0,0,0))
            #self.normal  = Vector(0,0,0)

        # so you store in this order:
        # pos, normal, tangent, binormal, uv1, uv2, ibone
        vertex = struct.pack(vertstruct,
            self.position[0], self.position[1], self.position[2],
            self.normal[0],   self.normal[1],   self.normal[2],
            self.tangent[0],  self.tangent[1],  self.tangent[2],
            self.binormal[0], self.binormal[1], self.binormal[2],
            self.uv1[0], self.uv1[1],
            self.uv2[0], self.uv2[1],
            self.bone_index[0], self.bone_index[1],
            self.bone_index[2], self.bone_index[3])


        file.write(vertex)

#helper the real scm face 'tupel is stored in mesh
#quad face
class qFace :

        vertex_cont = []

        def __init__(self):
            self.vertex_cont = []

        def addVert(self, vertex):
            self.vertex_cont.extend( vertex )

        def addToMesh(self, mesh):

            face1 = Face()
            face1.addVert([ self.vertex_cont[0], self.vertex_cont[1], self.vertex_cont[2] ])
            face1.CalcTB()

            face2 = Face()
            face2.addVert([ self.vertex_cont[2], self.vertex_cont[3], self.vertex_cont[0] ])
            face2.CalcTB()

            mesh.addQFace(face1, face2)


#helper the real scm face 'tupel is stored in mesh
#tri face
class Face :

    vertex_cont = []

    def __init__(self):
        self.vertex_cont = []

    def addVert(self, vertex):
        self.vertex_cont.extend(vertex)

    #now contains 3 vertexes calculate bi and ta and add to mesh

    def CalcTB( self ) :
        vert1 = self.vertex_cont[0]
        vert2 = self.vertex_cont[1]
        vert3 = self.vertex_cont[2]

        uv = [ vert1.uv1, vert2.uv1, vert3.uv1]

        # Calculate Tangent and Binormal
        #        (v3 - v1).(p2 - p1) - (v2 - v1).(p3 - p1)
        #    T  =  ------------------------------------------------
        #        (u2 - u1).(v3 - v1) - (v2 - v1).(u3 - u1)
        #        (u3 - u1).(p2 - p1) - (u2 - u1).(p3 - p1)
        #    B  =  -------------------------------------------------
        #        (v2 - v1).(u3 - u1) - (u2 - u1).(v3 - v1)

        P2P1 = vert2.position - vert1.position
        P3P1 = vert3.position - vert1.position

        #UV2UV1 = [ uv[1][0]-uv[0][0], uv[1][1]-uv[0][1] ]
        #UV3UV1 = [ uv[2][0]-uv[0][0], uv[2][1]-uv[0][1] ]

        UV2UV1 = uv[1] - uv[0]
        UV3UV1 = uv[2] - uv[0]

        divide = (UV2UV1[1]*UV3UV1[0] - UV2UV1[0]*UV3UV1[1])

        if ( divide != 0.0 ) :
            tangent = Vector((UV3UV1[1]*P2P1 - UV2UV1[1]*P3P1)/(divide))
            binormal = Vector((UV3UV1[0]*P2P1 - UV2UV1[0]*P3P1)/(-divide))
        else :
            my_popup_warn("Vertex-T-B divided through zero")
            tangent = Vector((0,0,0))
            binormal = Vector((0,0,0))


        #add calculated tangent and binormal to vertices
        for ind in range(3):
            self.vertex_cont[ind].tangent = tangent
            self.vertex_cont[ind].binormal =  binormal

    def addToMesh( self, mesh ) :
        self.CalcTB()
        mesh.addFace( self )


class scm_mesh :

    bones = []
    vertices = []
    vertcounter = 0
    faces = []
    info = []

    def __init__(self):
        self.bones = []
        self.vertices = []
        self.smoothEdgeKeys = {}
        self.faces = []
        self.info = []
        self.vertcounter = 0

    def addVert( self, nvert ):
        if VERTEX_OPTIMIZE :
            vertind = len(self.vertices)
            
            for edgekey in nvert.smoothEdges :
                if edgekey in self.smoothEdgeKeys :
                    for storedVertInd in self.smoothEdgeKeys[edgekey] :
                        vert = self.vertices[storedVertInd]
                        if nvert.uv1 == vert.uv1 and nvert.position == vert.position :
                            vertind = storedVertInd #change the vertex index to the one we are merging to
                            self.mergeVertices(vert,nvert,vertind)
                            
            #update the edge keys in the dictionary
            for edgeKey in nvert.smoothEdges :
                if not edgeKey in self.smoothEdgeKeys :
                    self.smoothEdgeKeys[edgeKey] = {}
                self.smoothEdgeKeys[edgeKey][vertind] = True
            
            #if no merging was done, append the entry
            if vertind == len(self.vertices) :
                self.vertices.append( nvert )
            
            return vertind
        else:
            self.vertices.append(nvert)
            return len(self.vertices)-1

    def mergeVertices( self, vert, nvert, vertind ):
        vert.tangent = Vector( (vert.tangent + nvert.tangent) )
        vert.binormal = Vector( (vert.binormal + nvert.binormal) )
        vert.normal = Vector( (vert.normal + nvert.normal) )

        self.vertices[vertind] = vert
        
    def addFace( self, face ):

        facein = [ self.addVert(nvert) for nvert in face.vertex_cont]
        self.faces.append(facein)

    def addQFace( self, face1, face2):

        facein = [ self.addVert(nvert) for nvert in face1.vertex_cont]
        self.faces.append(facein)

        facein = [ facein[2], self.addVert(face2.vertex_cont[1]), facein[0]]
        self.faces.append(facein)


    def save(self, filename):

        print('Writing Mesh...')

        scm = open(filename, 'wb')
        
        headerstruct = '4s11L'
        headersize = struct.calcsize(headerstruct)

        marker = b'MODL'
        
        version = 5
        boneoffset = 0
        usedBoneCount = 0
        
        vertoffset = 0
        extravertoffset = 0
        vertcount = len(self.vertices)
        indexoffset = 0
        
        indexcount = len(self.faces) * 3
        infooffset = 0
        infosize = 0
        totalbonecount = len(self.bones)

        

        # Write dummy header
        header = struct.pack(headerstruct,
            marker, version, boneoffset, usedBoneCount, vertoffset,
            extravertoffset, vertcount, indexoffset, indexcount,
            infooffset, infosize, totalbonecount)

        scm.write(header)


        # Write bone names
        pad_file(scm, b'NAME')

        for bone in self.bones:
            bone.name_offset = scm.tell()
            name = bone.name
            buffer = struct.pack(str(len(name) + 1)+'s', bytearray(name,'ascii'))
            scm.write(buffer)

        print("[/bone struckt]")

        # Write bones
        boneoffset = pad_file(scm, b'SKEL')

        for bone in self.bones:
            bone.save(scm)
            if bone.used == True:
                usedBoneCount = usedBoneCount + 1




        # Write vertices
        vertoffset = pad_file(scm, b'VTXL')

        for vertex in self.vertices:
            vertex.save(scm)



        # Write Faces
        indexoffset = pad_file(scm, b'TRIS')

        for f in range(len(self.faces)):
            face = struct.pack('3H', self.faces[f][0], self.faces[f][1], self.faces[f][2])
            scm.write(face)


        print( "Bones: %d, Vertices: %d, Faces: %d; \n" % (totalbonecount, len(self.vertices), len(self.faces)))

        #Write Info
        if len(self.info) > 0:

            infooffset = pad_file(scm, b'INFO')

            for i in range(len(self.info)):
                info = self.info[i]
                infolen = len(info) + 1
                buffer = struct.pack(str(infolen)+'s', bytearray(info,'ascii'))
                scm.write(buffer)

            infosize = scm.tell() - infooffset;

        
        # Now we can update the header
        scm.seek(0, 0)
        header = struct.pack(headerstruct,
            marker, version, boneoffset, usedBoneCount, vertoffset,
            extravertoffset, vertcount, indexoffset, indexcount,
            infooffset, infosize, totalbonecount)

        scm.write(header)

        scm.close()


class sca_bone:

    position = Vector(( 0, 0, 0))
    rotation = Quaternion(( 0, 0, 0, 0 ))

    def __init__(self, pos, rot):
        self.position = pos
        self.rotation = rot


class sca_frame:

    keytime = 0.0
    keyflags = 0
    bones = []
    anim = None

    def __init__(self, anim):
        self.keytime = 0.0
        self.keyflags = 0
        self.anim = anim
        self.bones = []

    def save(self, file):
        frameheader_fmt = 'fi'
        frameheader_size = struct.calcsize(frameheader_fmt)

        posrot_fmt = '3f4f'
        posrot_size = struct.calcsize(posrot_fmt)

        # Frame header
        buffer = struct.pack(frameheader_fmt, self.keytime, self.keyflags)
        file.write(buffer)

        #Log(":%d:" % (len(self.bones)))

        # Bones
        for bone in self.bones:

            buffer = struct.pack(    posrot_fmt,
                                    bone.position.x, bone.position.y, bone.position.z,
                                    bone.rotation.w, bone.rotation.x, bone.rotation.y, bone.rotation.z)

            file.write(buffer)


class sca_anim :
    frames = []
    bonelinks = []
    bonenames = []
    duration = 0.0

    def __init__(self):
        global ANIMATION_DURATION
        self.frames = []
        self.bonelinks = []
        self.bonenames = []
        self.duration = ANIMATION_DURATION

    def save(self, filename):

        print('Writing SCA...')

        #self.filename = filename
        sca = open(filename, 'wb')

        headerstruct = '4siifiiiii'

        # Write temp header
        magic = b'ANIM'
        version = 5
        numframes = len(self.frames)
        numbones = len(self.bonenames)

        namesoffset = 0
        linksoffset = 0
        animoffset = 0
        framesize = 0

        header = struct.pack(headerstruct,
            magic, version, numframes, self.duration, numbones,
            namesoffset, linksoffset, animoffset, framesize)
        #note: this header is seen correctly by the GPG dumpsca.py

        sca.write(header)

        # Write bone names
        namesoffset = pad_file(sca, b'NAME')

        for bone_name in self.bonenames:
            buffer = struct.pack(str(len(bone_name) + 1)+'s', bytearray(bone_name,'ascii'))
            sca.write(buffer)


        # Write bone links
        linksoffset = pad_file(sca, b'LINK')

        for link in self.bonelinks:
            buffer = struct.pack('i', link)
            sca.write(buffer)


        # Write data
        animoffset = pad_file(sca, b'DATA')

        #the space occupied by postion and rotation info on the bones.
        posrot_fmt = '3f4f'
        posrot_size = struct.calcsize(posrot_fmt)

        #this writes the position/rotation of the root bone in the first animation, as if it is at position 0, and no rotation
        #note: it looks like rot=1,0,0,0 is needed to indicate no rotation.
        buffer = struct.pack(posrot_fmt, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0)
        sca.write(buffer)

        for frame in self.frames:
            framesize = sca.tell()
            frame.save(sca)
            framesize = sca.tell() - framesize


        # Update header
        sca.seek(0, 0)

        header = struct.pack(headerstruct,
            magic, version, numframes, self.duration, numbones,
            namesoffset, linksoffset, animoffset, framesize)

        sca.write(header)

        sca.close()

        print( "Bones: %d, Frames: %d;\n" % (numbones, numframes) )

        #Log('OFFSETS: names = %d  links = %d  anim = %d  framesize = %d' % (namesoffset, linksoffset, animoffset, framesize))


######################################################
# Exporter Functions
######################################################

# Helper methods
######################################################

def pad(size):
    val = 16 - (size % 16)
    if (val < 4):
        val = val + 16

    return val

def pad_file(file, s4comment):
    N = pad(file.tell()) - 4
    #filldata = b'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'
    filldata = b'\xC5\xC5\xC5\xC5\xC5\xC5\xC5\xC5\xC5\xC5\xC5\xC5\xC5\xC5\xC5\xC5'#the original supcom files use Å instead of X as padding, and the max importer searches for this character explicitly.
    # C5 is Å in hex code, and its 197 which is over 128 so we put it as an escape char so python doesnt explode
    padding = struct.pack(str(N)+'s4s', filldata[0:N], s4comment)

    file.write(padding)
    return file.tell()



######################################################
    
# This places all the bones in a list, with their position in the list being the bone index.
# because SCM vertices only support up to 256 bones, we need to sort the IDs such that used bones are listed first.
def createBoneList(mesh_objs, arm, supcom_mesh):
    #we need to store the bones in a specific order, and we also need to store their parent index values
    #to do this, we store them in the order we want first, and then assign indeces after that.
    
    #first make a dictionary containing all used bones
    BonesWithVertices = {}
    
    for mesh_obj in mesh_objs:
        for i, vertex in enumerate(mesh_obj.data.vertices):
            for g in vertex.groups:
                vgName =  mesh_obj.vertex_groups[g.group].name
                if g.weight > 0.5 and not vgName in BonesWithVertices :
                    BonesWithVertices[vgName] = arm.bones[vgName]
                    break
    
    #extend the used bones dictionary to include all parents
    BonesWithVertices = getAllBoneParents(BonesWithVertices)
    
    SortedBones = []
    BoneSortQueue = []
    BonesWithAnimKeys = {}
    numroots = 0
    global keyedBones
    for bone in arm.bones.values():
        if (bone.parent == None):
            #count the root bones, there is only supposed to be one
            numroots += 1
            BoneSortQueue.insert(0,bone)
        if bone.name in keyedBones:
            #flag bones which hold animation data
            BonesWithAnimKeys[bone.name] = bone
    
    #extend the keyed bones dictionary to include all parents
    #TODO:check if this is needed
    BonesWithAnimKeys = getAllBoneParents(BonesWithAnimKeys)

    if numroots > 1:
        my_popup("Error: there are multiple root bones -> check you bone relations!")
        print("Error: there are multiple root bones -> check you bone relations!")
        return
    
    SortedBones = sortBonesList(BoneSortQueue, BonesWithVertices)
    
    #process the root bone, which has no parent
    processSingleBone(supcom_mesh,SortedBones[0],-1,BonesWithAnimKeys)
    #assign indeces to the remaining bones and process them
    for index in range(1,len(SortedBones)):
        #assign parent index
        bone = SortedBones[index]
        parentIndex = SortedBones.index(bone.parent)
        processSingleBone(supcom_mesh,SortedBones[index],parentIndex,BonesWithAnimKeys)
        
#when given a dictionary of bones, returns that dictionary with all their parents in there as well
def getAllBoneParents(InitialBones):
    counter = 1
    BoneQueue = [] #a temporary list, which allows us to append bones with vertices first.
    for bone in InitialBones.values():
        BoneQueue.append(bone)
    NewBones = {}
    while len(BoneQueue) > 0 and counter < 100: #we process the bones in order, parents first, children last.
        ParentBonesList = []
        for bone in BoneQueue:
            NewBones[bone.name] = bone
            if bone.parent and not bone.parent.name in InitialBones:
                ParentBonesList.append(bone.parent)
        BoneQueue = [] #clear the list
        BoneQueue.extend(ParentBonesList)
        counter +=1 #failsafe for infinite looping
        
    return NewBones
    
def sortBonesList(BoneSortQueue, BonesWithVertices):
    counter = 1
    UsedBonesList = [] #a temporary list, which allows us to append bones with vertices first.
    UnusedBonesList = []
    while len(BoneSortQueue) > 0 and counter < 500: #we process the bones in order, parents first, children last.
        ChildrenBonesList = []
        for bone in BoneSortQueue:
            if bone.name in BonesWithVertices:
                UsedBonesList.append(bone)
            else:
                UnusedBonesList.append(bone)
            
            if (bone.children != None):
                for child in bone.children:
                    ChildrenBonesList.append(child)
        
        BoneSortQueue = [] #clear the list
        BoneSortQueue.extend(ChildrenBonesList)
        counter +=1 #failsafe for infinite looping
    return UsedBonesList + UnusedBonesList

def processSingleBone(mesh, bone, parentBoneIndex,BonesWithAnimKeys):
    b_rest_pose     = Matrix(([0,0,0,0],[0,0,0,0],[0,0,0,0],[0,0,0,0]))
    b_rest_pose_inv = Matrix(([0,0,0,0],[0,0,0,0],[0,0,0,0],[0,0,0,0]))
    b_rotation        = Quaternion(( 0,0,0,0 ))
    b_position        = Vector(( 0,0,0 ))

    bone_matrix = bone.matrix_local.transposed()
    
    # Calculate the inverse rest pose for the bone #instead bonearmmat*worldmat = Matrix['BONESPACE']
    b_rest_pose     = bone_matrix * MArmatureWorld
    b_rest_pose_inv = ( b_rest_pose * xy_to_xz_transform ).inverted()

    if (bone.parent == None):
        rel_mat = b_rest_pose * xy_to_xz_transform
        #root pos is the same as the rest-pose
    else:
        parent_matrix_inv = Matrix( bone.parent.matrix_local.transposed() ).inverted()
        rel_mat = Matrix(bone_matrix * parent_matrix_inv)
        # must be BM * PMI in that order
        # do not use an extra (absolute) extra rotation here, cause this is only relative
    
    #  Position & Rotation   relative to parent (if there is a parent)
    b_rotation = rel_mat.transposed().to_quaternion()
    
    #row 3, cols 0,1,2 indicate position
    b_position = rel_mat.transposed().to_translation()
    
            
    sc_bone = scm_bone( bone.name, b_rest_pose_inv, b_rotation, b_position, parentBoneIndex )
    
    if bone.name in BonesWithAnimKeys:
        sc_bone.keyed = True
    
    BONES.append(sc_bone)
    mesh.bones.append(sc_bone)
    
def make_scm(arm_obj):
    global BONES
    global MArmatureWorld
    global xy_to_xz_transform
    
    BONES = []
    
    arm = arm_obj.data

    scn = bpy.context.scene


    bpy.ops.object.select_all(action='DESELECT')

    # Get all mesh objects for the selected armature & calculate progbar length
    pb_length = 0
    mesh_objs = []
    for obj in scn.objects:
        if obj.parent == arm_obj and obj.type == 'MESH':
            #calculate progbar length
            obj.data.update (calc_tessface=True)
            
            bmesh_data = obj.data
            pb_length += len(bmesh_data.tessfaces)
            mesh_objs.append(obj)


    #ProgBarFaces = ProgressBar( "Exp: Verts", pb_length )

    # Create SCM Mesh
    supcom_mesh = scm_mesh()
    
    createBoneList(mesh_objs, arm, supcom_mesh)

    # Process all the meshes
    for mesh_obj in mesh_objs:

        mesh_obj.data.update (calc_tessface=True)
        bmesh_data = mesh_obj.data
        
        # Build lookup dictionary for edge keys to edges
        edges = bmesh_data.edges
        face_edge_map = {ek: edges[i] for i, ek in enumerate(bmesh_data.edge_keys)}
        
        #why is this here twice?
        # Build lookup dictionary for edge keys to edges
        edges = bmesh_data.edges
        face_edge_map = {ek: edges[i] for i, ek in enumerate(bmesh_data.edge_keys)}

        if not bmesh_data.tessface_uv_textures :
            my_popup("Mesh has no texture values -> Please set your UV!")
            print("Mesh has no texture values -> Please set your UV!")
            return

        MatrixMesh = Matrix(mesh_obj.matrix_world)
        mesh_name = mesh_obj.name

        for face in bmesh_data.tessfaces:
            #ProgBarFaces.do()

            vertList = []

            for i in range(len(face.vertices)):
                vert = face.vertices[i]
                vertex = bmesh_data.vertices[vert]

                v_nor = Vector(( 0, 0, 0 ))
                v_pos = Vector(( 0, 0, 0 ))
                v_uv1 = Vector(( 0, 0)) #SC allows 2 uv's
                v_boneIndex = [0]*4 #  SC supports up to 4 bones we will use only one
                #v_boneIndex = [-1,0,0,0]

                #Find controling bone
                v_boneIndex[0] = -1

                for vgroup in vertex.groups:
                    if vgroup.weight > 0.5:
                        bonename = mesh_obj.vertex_groups[vgroup.group].name
                        for b in range(len(supcom_mesh.bones)):
                            bone = supcom_mesh.bones[b]
                            if bone.name == bonename:
                                bone.used = True
                                v_boneIndex[0] = b
                                break

                if (v_boneIndex[0] == -1):
                    v_boneIndex[0] = 0

                    bpy.ops.object.mode_set(mode='OBJECT')
                    bpy.ops.object.select_all(action='DESELECT')
                    
                    mesh_obj.select=True
                    bpy.context.scene.objects.active = mesh_obj
                    
                    bpy.ops.object.mode_set(mode='EDIT')
                    bpy.ops.mesh.select_all(action="DESELECT")
                    bpy.context.tool_settings.mesh_select_mode[0] = True
                    
                    #On ne peut sélectionner les vertices qu'en object mode (apparemment, on bosse sur une copie)
                    bpy.ops.object.mode_set(mode='OBJECT')
                    bmesh_data.vertices[vert].select = True
                    bpy.ops.object.mode_set(mode='EDIT')
                    
                    my_popup("Error: Vertice without Bone Influence in %s. (Selected) " % (mesh_name))
                    print("Error: Vertice without Bone Influence in %s. (Selected) " % (mesh_name))
                    return
                v_pos = Vector( vertex.co * (MatrixMesh * xy_to_xz_transform))

                v_nor = vertex.normal * (MatrixMesh * xy_to_xz_transform)

                #needed cause supcom scans an image in the opposite vertical direction or something?.


                uv = bmesh_data.tessface_uv_textures[0]

                my_uv = None
                if (i == 0):
                    my_uv = uv.data[face.index].uv1
                if (i == 1):
                    my_uv = uv.data[face.index].uv2
                if (i == 2):
                    my_uv = uv.data[face.index].uv3
                
                if my_uv is None :
                    i = face.index
                    bpy.ops.object.mode_set(mode='OBJECT')
                    bpy.ops.object.select_all(action='DESELECT')
                    
                    mesh_obj.select=True
                    bpy.context.scene.objects.active = mesh_obj
                    
                    bpy.ops.object.mode_set(mode='EDIT')
                    bpy.ops.mesh.select_all(action="DESELECT")
                    bpy.context.tool_settings.mesh_select_mode[0] = True
                    
                    #On ne peut sélectionner les vertices qu'en object mode (apparemment, on bosse sur une copie)
                    bpy.ops.object.mode_set(mode='OBJECT')
                    mesh_obj.data.update (calc_tessface=True)
                    #on va prendre tous les points de la face, et les sélectionner.
                    for i in range(len(face.vertices)):
                        vert = face.vertices[i]
                        bmesh_data.vertices[vert].select = True
                        
                        
                    bpy.ops.object.mode_set(mode='EDIT')
                    
                    my_popup("Error: Face %d is not a triangle (selected)" % i)
                    print("Error: Face %d is not a triangle (selected)" % i)
                    return
                
                v_uv1 = Vector((my_uv[0], 1.0 - my_uv[1]))
                
                #for each vertex give it a list of smooth edges its part of so it can be merged down later
                v_smoothEdgeList = []
                
                for ek in face.edge_keys :
                    edge = face_edge_map[ek]
                    if not edge.use_edge_sharp :
                        for smoothVert in edge.vertices :
                            if vertex.index == smoothVert :
                                v_smoothEdgeList.append( ek )
                
                vertList.append( scm_vertex( v_pos, v_nor, v_uv1, v_boneIndex, v_smoothEdgeList) )

            if len(vertList) > 3:
                newFace = qFace()
            else:
                newFace = Face()

            newFace.addVert(vertList)
            newFace.addToMesh(supcom_mesh)

        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')

    return supcom_mesh


def getBoneNameAndAction(path):

    return [path.split('"')[1] , path.split('.')[-1]]

def make_sca(arm_obj, action):

    global BONES
    global MArmatureWorld
    global xy_to_xz_transform
    global keyedBones
    BONES = []
    
    keyedBones = set()
    
    #get textInfo for present keys in armature
    if arm_obj.animation_data.action:
        for fc in arm_obj.animation_data.action.fcurves:
            keyParsed = getBoneNameAndAction(fc.data_path)
            if (keyParsed[1] in ["scale","rotation_quaternion","location"]):
                keyedBones.add(keyParsed[0])
    
    print ("animatedBones",keyedBones)
    
    scene = bpy.context.scene
    context = bpy.context
    endframe = context.scene.frame_end

    scene.objects.active = arm_obj

    animation = sca_anim()

    supcom_mesh = scm_mesh()
    
    
    if len(BONES) == 0:
        mesh_objs = []
        for obj in scene.objects:
            if obj.parent == arm_obj and obj.type == 'MESH':
                mesh_objs.append(obj)
        createBoneList(mesh_objs, arm_obj.data, supcom_mesh)
        
    BONES2 = [b for b in BONES if b.keyed]
    
    for b in BONES2:
        #on récupère le nom du parent
        if b.parent_index != -1:
            parentName = BONES[b.parent_index].name
            
            for i in range(len(BONES2)):
                b2 = BONES2[i]
                if b2.name == parentName:
                    b.parent_index = i
    
    BONES = [b for b in BONES2]

    # Add bone names & links
    for bone in BONES:
        animation.bonenames.append(bone.name)
        animation.bonelinks.append(bone.parent_index)

    #ProgBarAnimation = ProgressBar( "Exp: Anim", endframe)

    # Add frames
    for frame_counter in range(endframe):
        #ProgBarAnimation.do()

        frame = sca_frame(animation)

        context.scene.frame_set(frame_counter+1)

        POSED_BONES = {}
        for posebone in arm_obj.pose.bones:
            POSED_BONES[posebone.name] = posebone.matrix

        for bone in BONES:
            pose_bone_matrix = POSED_BONES[bone.name].transposed()

            if (bone.parent_index == -1):
                rel_mat = (pose_bone_matrix * MArmatureWorld) * xy_to_xz_transform
            else:
                rel_mat = pose_bone_matrix * POSED_BONES[BONES[bone.parent_index].name].transposed().inverted()

            #rel_mat.transpose()
            rotation = rel_mat.transposed().to_quaternion().normalized()
            #pos = Vector(( rel_mat[3][0], rel_mat[3][1], rel_mat[3][2] ))
            #rel_mat.transpose()
            pos = rel_mat.transposed().to_translation()
            anim_bone = sca_bone(pos, rotation)
            frame.bones.append(anim_bone)

        animation.frames.append(frame)

    context.scene.frame_set(1)

    return animation

def export_scm(outdir):
    global VERSION, USER_INFO
    global MArmatureWorld
    global xy_to_xz_transform
    
    bpy.ops.object.mode_set(mode='OBJECT')

    #xy_to_xz_transform.resize_4x4()

    arm_obj = find_armature()

    # this defines the ARMATURE_SPACE.
    # all bones in the armature are positioned relative to this space.
    MArmatureWorld = Matrix(arm_obj.matrix_world)

    # SCM
    mesh = make_scm(arm_obj)
    if mesh == None :
        
        print('No mesh Aborted!')
        my_popup('No mesh Aborted!')
        return

    mesh.info.append('Exported with Blender SupCom-Exporter ' + VERSION)
    if USER_INFO != "" :
        mesh.info.append( USER_INFO )
    
    mesh.save(outdir + arm_obj.name + '.scm')
    mesh = None
    
    loc_filename = arm_obj.name + '.scm'
    my_popup_info("Object saved to " + loc_filename)

def find_armature():
    scene = bpy.context.scene #TODO:prioritise visible objects over this

    bpy.ops.object.mode_set(mode='OBJECT')
    # Get Selected object(s)
    selected_objects = bpy.context.selected_objects

    # Prioritise selected armature
    arm_obj = None
    for obj in selected_objects:
        if obj.type == "ARMATURE":
            arm_obj = obj
            break

    # Is there one armature? Take this one
    if arm_obj == None :
        for obj in scene.objects:
            if obj.type == "ARMATURE":
                arm_obj = obj
                break

    if arm_obj == None:
        my_popup("Error: No armature detected. If exists but not detected, please select your armature.")
        return
    return arm_obj


def export_sca(outdir):
    global VERSION, USER_INFO
    global MArmatureWorld
    global xy_to_xz_transform

    bpy.ops.object.mode_set(mode='OBJECT')


    xy_to_xz_transform.resize_4x4()

    arm_obj = find_armature()

    # this defines the ARMATURE_SPACE.
    # all bones in the armature are positioned relative to this space.
    MArmatureWorld = Matrix(arm_obj.matrix_world)


    # SCA
    # This plays through every action in the NLA tracks linked to our armature and records the relevant bone positions every frame, then saves that to sca
    for track in arm_obj.animation_data.nla_tracks:
        for NlaStrip in track.strips:
            #set active action
            arm_obj.animation_data.action = NlaStrip.action
            
            animation = make_sca(arm_obj, NlaStrip.action)
            animation.save(outdir + NlaStrip.action.name + ".sca")
            
            my_popup_info("Action saved to " + NlaStrip.action.name)



class EXPORT_OT_scm(bpy.types.Operator):
    """Export Skeleton Mesh""" \
    """One mesh and one armature else select one mesh or armature to be exported"""

    global modelfile
    bl_idname = "export_mesh.scm" # this is important since its how bpy.ops.export.udk_anim_data is constructed
    bl_label = "Export Directory"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_options = {'UNDO'}

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.

    #filepath = StringProperty(
    #        subtype='FILE_PATH',
    #        )
    directory = StringProperty(
            subtype='DIR_PATH',
            )
    filter_glob = StringProperty(
            default="*.scm",
            options={'HIDDEN'},
            )


    @classmethod
    def poll(cls, context):
        return context.active_object != None

    def execute(self, context):
        global inError
        inError = 0
        scene = bpy.context.scene

        export_scm(self.directory)

        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        wm.fileselect_add(self)
        return {'RUNNING_MODAL'}

class EXPORT_OT_sca(bpy.types.Operator):
    """Export Skeleton Mesh""" \
    """One mesh and one armature else select one mesh or armature to be exported"""
    global modelfile
    bl_idname = "export_anim.sca" # this is important since its how bpy.ops.export.udk_anim_data is constructed
    bl_label = "Export Directory"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_options = {'UNDO'}

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.

    #filepath = StringProperty(
    #        subtype='FILE_PATH',
    #        )
    directory = StringProperty(
            subtype='DIR_PATH',
            )
    filter_glob = StringProperty(
            default="*.sca",
            options={'HIDDEN'},
            )

    @classmethod
    def poll(cls, context):
        return context.active_object != None

    def execute(self, context):
        global inError
        inError = 0
        scene = bpy.context.scene
        export_sca(self.directory)

        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        wm.fileselect_add(self)
        return {'RUNNING_MODAL'}

def menu_func(self, context):
    self.layout.operator(EXPORT_OT_scm.bl_idname, text="Supcom Mesh (.scm)")
    self.layout.operator(EXPORT_OT_sca.bl_idname, text="Supcom Anim (.sca)")


#===========================================================================
# Entry
#===========================================================================
def register():
    bpy.utils.register_module(__name__)
    bpy.types.INFO_MT_file_export.append(menu_func)

def unregister():
    bpy.utils.unregister_module(__name__)
    bpy.types.INFO_MT_file_export.remove(menu_func)

if __name__ == "__main__":
    print(header("SupCom Export scm/sca 4.0", 'CENTER'))
    register()
