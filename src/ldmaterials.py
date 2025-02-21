# -*- coding: utf-8 -*-
"""LDR Importer GPLv2 license.

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software Foundation,
Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

"""

import bpy

from .ldconsole import Console


__all__ = ("Materials")


class Materials:

    def __init__(self, ld_colors, render_engine):

        self.__ld_colors = ld_colors
        self.__render_engine = render_engine
        self.__materials = {}

    def contains(self, code):
        """Check if a color exists in the color dictionary.

        @param {String} code - The code for the corresponding color.
        @return {Boolean} True if the color was found, False otherwise.
        """
        return code in self.__materials.keys()

    def make(self, code):

        if self.__render_engine == "CYCLES":
            return self.__get_cycles_material(code)
        else:
            return self.__get_bi_materials(code)

    def get(self, code):
        """Get an individual material.

        @param {String} code - The code identifying the color.
        @return {!Dictionary} The color definition if available,
                              None otherwise.
        """
        return self.__materials.get(code)

    def __set(self, code, mat):
        self.__materials[code] = mat
        

    # def __get_bi_materials(self, code):

    #     # We have already generated this material, reuse it
    #     if self.contains(code):
    #         return self.get(code)

    #     # Generate a material from a possible direct color
    #     if not self.__ld_colors.contains(code):
    #         col = self.__ld_colors.makeDirectColor(code)

    #         # No direct color was found
    #         if not col["valid"]:
    #             return None

    #         # We have a direct color on our hands
    #         Console.log("Direct color {0} found".format(code))
    #         mat = bpy.data.materials.new("Mat_{0}".format(code))
    #         # mat.diffuse_color = col["value"]
    #         mat.diffuse_color = (*col["value"], 1.0)

    #         # Add it to the material lists to avoid duplicate processing
    #         self.__set(code, mat)
    #         return self.get(code)

    #     # Valid LDraw color, generate the material
    #     else:
    #         col = self.__ld_colors.get(code)
    #         mat = bpy.data.materials.new("Mat_{0}".format(code))
    #         # mat.diffuse_color = col["value"]
    #         mat.diffuse_color = (*col["value"], 1.0)

    #         alpha = col["alpha"]
    #         if alpha < 1.0:
    #             mat.use_transparency = True
    #             mat.alpha = alpha

    #         mat.emit = col["luminance"] / 100

    #         if col["material"] == "CHROME":
    #             mat.specular_intensity = 1.4
    #             mat.roughness = 0.01
    #             mat.raytrace_mirror.use = True
    #             mat.raytrace_mirror.reflect_factor = 0.3

    #         elif col["material"] == "PEARLESCENT":
    #             mat.specular_intensity = 0.1
    #             mat.roughness = 0.32
    #             mat.raytrace_mirror.use = True
    #             mat.raytrace_mirror.reflect_factor = 0.07

    #         elif col["material"] == "RUBBER":
    #             mat.specular_intensity = 0.19

    #         elif col["material"] == "METAL":
    #             mat.specular_intensity = 1.473
    #             mat.specular_hardness = 292
    #             mat.diffuse_fresnel = 0.93
    #             mat.darkness = 0.771
    #             mat.roughness = 0.01
    #             mat.raytrace_mirror.use = True
    #             mat.raytrace_mirror.reflect_factor = 0.9

    #         # elif col["material"] == "GLITTER":
    #         #    slot = mat.texture_slots.add()
    #         #    tex = bpy.data.textures.new("GlitterTex", type = "STUCCI")
    #         #    tex.use_color_ramp = True
    #         #
    #         #    slot.texture = tex

    #         else:
    #             mat.specular_intensity = 0.2

    #         self.__set(code, mat)
    #         return self.get(code)

    #     # We were unable to generate a material
    #     return None

    def __get_bi_materials(self, code):
        # 已生成材质则复用
        if self.contains(code):
            return self.get(code)

        # 处理直接颜色
        if not self.__ld_colors.contains(code):
            col = self.__ld_colors.makeDirectColor(code)
            if not col["valid"]:
                return None

            # 创建新材质（2.80+需要显式设置use_nodes）
            mat = bpy.data.materials.new(name=f"Mat_{code}")
            mat.use_nodes = True
            nodes = mat.node_tree.nodes
            links = mat.node_tree.links

            # 清除默认节点
            nodes.clear()

            # 创建Principled BSDF节点
            bsdf = nodes.new('ShaderNodeBsdfPrincipled')
            bsdf.location = (0, 0)
            
            # 设置基础颜色（RGBA格式）
            bsdf.inputs['Base Color'].default_value = (*col["value"], 1.0)
            
            # 创建输出节点
            output = nodes.new('ShaderNodeOutputMaterial')
            output.location = (400, 0)
            
            # 连接节点
            links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

            self.__set(code, mat)
            return mat

        # 处理LDraw标准颜色
        col = self.__ld_colors.get(code)
        mat = bpy.data.materials.new(name=f"Mat_{code}")
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()

        # 核心节点配置
        bsdf = nodes.new('ShaderNodeBsdfPrincipled')
        output = nodes.new('ShaderNodeOutputMaterial')
        bsdf.location = (0, 0)
        output.location = (400, 0)
        links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

        # 基础颜色设置
        bsdf.inputs['Base Color'].default_value = (*col["value"], 1.0)

        # 透明度处理（2.80+使用混合模式）
        alpha = col["alpha"]
        if alpha < 1.0:
            mat.blend_method = 'BLEND'
            bsdf.inputs['Alpha'].default_value = alpha

        # 发光设置（使用Emission节点）
        luminance = col["luminance"] / 100
        if luminance > 0:
            emit = nodes.new('ShaderNodeEmission')
            emit.location = (-200, 0)
            emit.inputs['Color'].default_value = (*col["value"], 1.0)
            emit.inputs['Strength'].default_value = luminance
            
            # 使用Mix Shader混合发光和BSDF
            mix = nodes.new('ShaderNodeMixShader')
            mix.location = (200, 0)
            mix.inputs['Fac'].default_value = 0.5  # 根据需求调整混合比例
            
            links.new(emit.outputs[0], mix.inputs[2])
            links.new(bsdf.outputs[0], mix.inputs[1])
            links.new(mix.outputs[0], output.inputs['Surface'])

        blender_version = bpy.app.version_string.split('.')[0]

        # 材质类型处理
        material_type = col["material"]
        if material_type == "CHROME":
            bsdf.inputs['Metallic'].default_value = 1.0
            bsdf.inputs['Roughness'].default_value = 0.02
            bsdf.inputs['Specular' if blender_version=='3' else "Specular IOR Level"].default_value = 0.5
            
            
            
        elif material_type == "PEARLESCENT":
            bsdf.inputs['Metallic'].default_value = 0.7
            bsdf.inputs['Roughness'].default_value = 0.3
            bsdf.inputs['Clearcoat'].default_value = 0.5
            
        elif material_type == "RUBBER":
            bsdf.inputs['Roughness'].default_value = 0.6
            bsdf.inputs['Specular' if blender_version=='3' else "Specular IOR Level"].default_value = 0.2
            
        elif material_type == "METAL":
            bsdf.inputs['Metallic'].default_value = 1.0
            bsdf.inputs['Roughness'].default_value = 0.1
            bsdf.inputs['Specular' if blender_version=='3' else "Specular IOR Level"].default_value = 0.8
            
        else:  # 默认材质
            bsdf.inputs['Roughness'].default_value = 0.4
            bsdf.inputs['Specular' if blender_version=='3' else "Specular IOR Level"].default_value = 0.5

        self.__set(code, mat)
        return mat

    def __get_cycles_material(self, code):
        if self.contains(code):
            return self.get(code)

        # 处理直接颜色
        if not self.__ld_colors.contains(code):
            col = self.__ld_colors.makeDirectColor(code)
            if not col["valid"]:
                return None

            # 创建基础材质节点
            mat = self.__create_base_material(f"Mat_{code}", col["value"], 1.0)
            self.__set(code, mat)
            return mat

        # 处理LDraw标准颜色
        col = self.__ld_colors.get(code)
        
        # 根据材质类型创建节点
        if col["name"] == "Milky_White":
            mat = self.__create_milky_white(f"Mat_{code}", col["value"])
        elif col["luminance"] > 0:
            mat = self.__create_emissive(f"Mat_{code}", col["value"], 
                                    col["alpha"], col["luminance"])
        else:
            material_type = col["material"]
            if material_type == "CHROME":
                mat = self.__create_chrome(f"Mat_{code}", col["value"])
            elif material_type in {"PEARLESCENT", "METAL"}:
                mat = self.__create_metal(f"Mat_{code}", col["value"])
            elif material_type == "RUBBER":
                mat = self.__create_rubber(f"Mat_{code}", col["value"], col["alpha"])
            else:
                mat = self.__create_base_material(f"Mat_{code}", 
                                                col["value"], col["alpha"])

        self.__set(code, mat)
        return mat

    def __create_base_material(self, name, color, alpha):
        """创建基础Principled BSDF材质"""
        mat = bpy.data.materials.new(name=name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        nodes.clear()

        bsdf = nodes.new('ShaderNodeBsdfPrincipled')
        output = nodes.new('ShaderNodeOutputMaterial')
        bsdf.location = (0, 0)
        output.location = (400, 0)

        # 设置颜色和透明度
        rgba = (*color, 1.0)
        bsdf.inputs['Base Color'].default_value = rgba
        if alpha < 1.0:
            mat.blend_method = 'BLEND'
            bsdf.inputs['Alpha'].default_value = alpha

        mat.node_tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
        return mat

    def __create_emissive(self, name, color, alpha, luminance):
        """创建自发光材质"""
        mat = self.__create_base_material(name, color, alpha)
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        # 添加发光节点
        emission = nodes.new('ShaderNodeEmission')
        emission.location = (-300, 0)
        emission.inputs['Color'].default_value = (*color, 1.0)
        emission.inputs['Strength'].default_value = luminance

        # 创建混合节点
        mix = nodes.new('ShaderNodeMixShader')
        mix.location = (200, 0)
        
        # 获取基础BSDF节点
        bsdf = nodes.get('Principled BSDF')
        
        # 重新连接节点
        links.new(emission.outputs[0], mix.inputs[2])
        links.new(bsdf.outputs[0], mix.inputs[1])
        links.new(mix.outputs[0], nodes['Material Output'].inputs['Surface'])
        return mat

    def __create_chrome(self, name, color):
        """铬材质"""
        mat = bpy.data.materials.new(name=name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        nodes.clear()

        bsdf = nodes.new('ShaderNodeBsdfPrincipled')
        output = nodes.new('ShaderNodeOutputMaterial')
        
        blender_version = bpy.app.version_string.split('.')[0]
        # 金属属性设置
        bsdf.inputs['Base Color'].default_value = (*color, 1.0)
        bsdf.inputs['Metallic'].default_value = 1.0
        bsdf.inputs['Roughness'].default_value = 0.02
        bsdf.inputs['Specular' if blender_version=='3' else "Specular IOR Level"].default_value = 0.9

        mat.node_tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
        return mat

    def __create_metal(self, name, color):
        """通用金属材质"""
        mat = bpy.data.materials.new(name=name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        nodes.clear()

        bsdf = nodes.new('ShaderNodeBsdfPrincipled')
        output = nodes.new('ShaderNodeOutputMaterial')
        
        blender_version = bpy.app.version_string.split('.')[0]
        # 金属属性设置
        bsdf.inputs['Base Color'].default_value = (*color, 1.0)
        bsdf.inputs['Metallic'].default_value = 0.95
        bsdf.inputs['Roughness'].default_value = 0.15
        bsdf.inputs['Specular' if blender_version=='3' else "Specular IOR Level"].default_value = 0.5

        mat.node_tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
        return mat

    def __create_rubber(self, name, color, alpha):
        """橡胶材质"""
        mat = self.__create_base_material(name, color, alpha)
        nodes = mat.node_tree.nodes
        bsdf = nodes.get('Principled BSDF')
        
        blender_version = bpy.app.version_string.split('.')[0]
        
        # 调整橡胶属性
        bsdf.inputs['Roughness'].default_value = 0.6
        bsdf.inputs['Specular' if blender_version=='3' else "Specular IOR Level"].default_value = 0.2
        bsdf.inputs['Subsurface'].default_value = 0.1  # 次表面散射
        return mat

    def __create_milky_white(self, name, color):
        """乳白材质"""
        mat = self.__create_base_material(name, color, 1.0)
        nodes = mat.node_tree.nodes
        bsdf = nodes.get('Principled BSDF')
        
        # 调整材质参数
        bsdf.inputs['Roughness'].default_value = 0.3
        bsdf.inputs['Subsurface'].default_value = 0.4
        bsdf.inputs['Subsurface Radius'] = (1.0, 0.2, 0.1)  # 次表面散射半径
        return mat

    # def __get_cycles_material(self, code):

    #     # We have already generated this material, reuse it
    #     if self.contains(code):
    #         return self.get(code)

    #     # Generate a material from a possible direct color
    #     if not self.__ld_colors.contains(code):
    #         col = self.__ld_colors.makeDirectColor(code)

    #         # No direct color was found
    #         if not col["valid"]:
    #             return None

    #         # We have a direct color on our hands
    #         Console.log("Direct color {0} found".format(code))
    #         mat = getCyclesBase("Mat_{0}".format(code), col["value"], 1.0)

    #         # Add it to the material list to avoid duplicate processing
    #         self.__set(code, mat)
    #         return self.get(code)

    #     # Valid LDraw color, generate the material
    #     else:
    #         col = self.__ld_colors.get(code)

    #         if col["name"] == "Milky_White":
    #             mat = getCyclesMilkyWhite("Mat_{0}".format(code), col["value"])

    #         elif col["material"] == "BASIC" and col["luminance"] == 0:
    #             mat = getCyclesBase("Mat_{0}".format(code),
    #                                 col["value"], col["alpha"])

    #         elif col["luminance"] > 0:
    #             mat = getCyclesEmit("Mat_{0}".format(code), col["value"],
    #                                 col["alpha"], col["luminance"])

    #         elif col["material"] == "CHROME":
    #             mat = getCyclesChrome("Mat_{0}".format(code), col["value"])

    #         elif col["material"] == "PEARLESCENT":
    #             mat = getCyclesPearlMetal("Mat_{0}".format(code), col["value"])

    #         elif col["material"] == "METAL":
    #             mat = getCyclesPearlMetal("Mat_{0}".format(code), col["value"])

    #         elif col["material"] == "RUBBER":
    #             mat = getCyclesRubber("Mat_{0}".format(code),
    #                                   col["value"], col["alpha"])

    #         else:
    #             mat = getCyclesBase("Mat_{0}".format(code),
    #                                 col["value"], col["alpha"])

    #         self.__set(code, mat)
    #         return self.get(code)

    #     # We were unable to generate a material
    #     return None


def getCyclesBase(name, diffColor, alpha):
    """Basic material colors for Cycles render engine."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = diffColor

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # Remove all previous nodes
    for node in nodes:
        nodes.remove(node)

    mix = nodes.new('ShaderNodeMixShader')
    mix.location = 0, 90
    mix.inputs['Fac'].default_value = 0.05

    out = nodes.new('ShaderNodeOutputMaterial')
    out.location = 290, 100

    # Solid bricks
    if alpha == 1.0:
        node = nodes.new('ShaderNodeBsdfDiffuse')
        node.location = -242, 154
        node.inputs['Color'].default_value = diffColor + (1.0,)
        node.inputs['Roughness'].default_value = 0.0

    # Transparent bricks
    else:
        # TODO Figure out a good way to make use of the alpha value
        node = nodes.new('ShaderNodeBsdfGlass')
        node.location = -242, 154
        node.inputs['Color'].default_value = diffColor + (1.0,)
        node.inputs['Roughness'].default_value = 0.05
        node.inputs['IOR'].default_value = 1.46

    gloss = nodes.new('ShaderNodeBsdfGlossy')
    gloss.location = -242, -23
    gloss.distribution = 'BECKMANN'
    gloss.inputs['Roughness'].default_value = 0.05
    gloss.inputs['Color'].default_value = (1.0, 1.0, 1.0, 1.0)

    links.new(mix.outputs[0], out.inputs[0])
    links.new(node.outputs[0], mix.inputs[1])
    links.new(gloss.outputs[0], mix.inputs[2])

    return mat


def getCyclesEmit(name, diff_color, alpha, luminance):

    mat = bpy.data.materials.new(name)
    mat.use_nodes = True

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    for node in nodes:
        nodes.remove(node)

    mix = nodes.new('ShaderNodeMixShader')
    mix.location = 0, 90
    mix.inputs['Fac'].default_value = luminance / 100

    out = nodes.new('ShaderNodeOutputMaterial')
    out.location = 290, 100

    """
    NOTE: The alpha value again is not making much sense here.
    I'm leaving it in, in case someone has an idea how to use it.
    """

    trans = nodes.new('ShaderNodeBsdfTranslucent')
    trans.location = -242, 154
    trans.inputs['Color'].default_value = diff_color + (1.0,)

    emit = nodes.new('ShaderNodeEmission')
    emit.location = -242, -23

    links.new(mix.outputs[0], out.inputs[0])
    links.new(trans.outputs[0], mix.inputs[1])
    links.new(emit.outputs[0], mix.inputs[2])

    return mat


def getCyclesChrome(name, diffColor):
    """Chrome material colors for Cycles render engine."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = diffColor

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # Remove all previous nodes
    for node in nodes:
        nodes.remove(node)

    mix = nodes.new('ShaderNodeMixShader')
    mix.location = 0, 90
    mix.inputs['Fac'].default_value = 0.01

    out = nodes.new('ShaderNodeOutputMaterial')
    out.location = 290, 100

    glossOne = nodes.new('ShaderNodeBsdfGlossy')
    glossOne.location = -242, 154
    glossOne.distribution = 'GGX'
    glossOne.inputs['Color'].default_value = diffColor + (1.0,)
    glossOne.inputs['Roughness'].default_value = 0.03

    glossTwo = nodes.new('ShaderNodeBsdfGlossy')
    glossTwo.location = -242, -23
    glossTwo.inputs['Color'].default_value = (1.0, 1.0, 1.0, 1.0)
    glossTwo.inputs['Roughness'].default_value = 0.03

    links.new(mix.outputs[0], out.inputs[0])
    links.new(glossOne.outputs[0], mix.inputs[1])
    links.new(glossTwo.outputs[0], mix.inputs[2])

    return mat


def getCyclesPearlMetal(name, diffColor):
    """Pearlescent material colors for Cycles render engine."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = diffColor

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # Remove all previous nodes
    for node in nodes:
        nodes.remove(node)

    mix = nodes.new('ShaderNodeMixShader')
    mix.location = 0, 90
    mix.inputs['Fac'].default_value = 0.4

    out = nodes.new('ShaderNodeOutputMaterial')
    out.location = 290, 100

    gloss = nodes.new('ShaderNodeBsdfGlossy')
    gloss.location = -242, 154
    gloss.distribution = 'BECKMANN'
    gloss.inputs['Color'].default_value = diffColor + (1.0,)
    gloss.inputs['Roughness'].default_value = 0.05

    diffuse = nodes.new('ShaderNodeBsdfDiffuse')
    diffuse.location = -242, -23
    diffuse.inputs['Color'].default_value = diffColor + (1.0,)
    diffuse.inputs['Roughness'].default_value = 0.0

    links.new(mix.outputs[0], out.inputs[0])
    links.new(gloss.outputs[0], mix.inputs[1])
    links.new(diffuse.outputs[0], mix.inputs[2])

    return mat


def getCyclesRubber(name, diffColor, alpha):
    """Rubber material colors for Cycles render engine."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = diffColor

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # Remove all previous nodes
    for node in nodes:
        nodes.remove(node)

    mixTwo = nodes.new('ShaderNodeMixShader')
    mixTwo.location = 0, 90
    mixTwo.inputs['Fac'].default_value = 0.05

    out = nodes.new('ShaderNodeOutputMaterial')
    out.location = 290, 100

    # Solid bricks
    if alpha == 1.0:
        diffuse = nodes.new('ShaderNodeBsdfDiffuse')
        diffuse.location = -242, 154
        diffuse.inputs['Color'].default_value = diffColor + (1.0,)
        diffuse.inputs['Roughness'].default_value = 0

        trans = nodes.new('ShaderNodeBsdfTranslucent')
        trans.location = -242, 154
        trans.inputs['Color'].default_value = diffColor + (1.0,)

        mixOne = nodes.new('ShaderNodeMixShader')
        mixOne.location = 0, 90
        mixOne.inputs['Fac'].default_value = 0.7

        gloss = nodes.new('ShaderNodeBsdfGlossy')
        gloss.location = -242, 154
        gloss.distribution = 'BECKMANN'
        gloss.inputs['Color'].default_value = diffColor + (1.0,)
        gloss.inputs['Roughness'].default_value = 0.2

        links.new(diffuse.outputs[0], mixOne.inputs[1])
        links.new(trans.outputs[0], mixOne.inputs[2])
        links.new(mixOne.outputs[0], mixTwo.inputs[1])
        links.new(gloss.outputs[0], mixTwo.inputs[2])

    # Transparent bricks
    else:
        glass = nodes.new('ShaderNodeBsdfGlass')
        glass.location = -242, 154
        glass.distribution = 'BECKMANN'
        glass.inputs['Color'].default_value = diffColor + (1.0,)
        glass.inputs['Roughness'].default_value = 0.4
        glass.inputs['IOR'].default_value = 1.160

        gloss = nodes.new('ShaderNodeBsdfGlossy')
        gloss.location = -242, 154
        gloss.distribution = 'GGX'
        gloss.inputs['Color'].default_value = (1.0, 1.0, 1.0, 1.0)
        gloss.inputs['Roughness'].default_value = 0.2

        links.new(glass.outputs[0], mixTwo.inputs[1])
        links.new(gloss.outputs[0], mixTwo.inputs[2])

    links.new(mixTwo.outputs[0], out.inputs[0])

    return mat


def getCyclesMilkyWhite(name, diff_color):

    mat = bpy.data.materials.new(name)
    mat.use_nodes = True

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    for node in nodes:
        nodes.remove(node)

    mix = nodes.new('ShaderNodeMixShader')
    mix.location = 0, 90
    mix.inputs['Fac'].default_value = 0.1

    out = nodes.new('ShaderNodeOutputMaterial')
    out.location = 290, 100

    trans = nodes.new('ShaderNodeBsdfTranslucent')
    trans.location = -242, 154
    trans.inputs['Color'].default_value = diff_color + (1.0,)

    diff = nodes.new('ShaderNodeBsdfDiffuse')
    diff.location = -242, -23
    diff.inputs['Color'].default_value = diff_color + (1.0,)
    diff.inputs['Roughness'].default_value = 0.1

    links.new(mix.outputs[0], out.inputs[0])
    links.new(trans.outputs[0], mix.inputs[1])
    links.new(diff.outputs[0], mix.inputs[2])

    return mat
