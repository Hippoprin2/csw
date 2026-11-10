# Blender -b hippo_walk_front.blend -P measure_stride.py
# Foot travel during stance (front foot at contact -> same foot at the opposite contact) = ground speed
# the sprite must move at for the feet not to slide.
import bpy
s = bpy.context.scene; rig = bpy.data.objects["HippoRig"]
def foot(f, b):
    s.frame_set(f); bpy.context.view_layer.update()
    return rig.matrix_world @ rig.pose.bones[b].tail
import os
C = int(os.environ.get("WALK_C", "16"))
a, b = foot(1, "leg.L"), foot(1 + C // 2, "leg.L")
d = (a - b).length
print("STRIDE half-cycle travel %.4f unit, speed %.3f unit/s (fps %d)" % (d, d / (C / 2 / s.render.fps), s.render.fps))
