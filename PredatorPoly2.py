bl_info = {
    "name": "Predator View",
    "author": "Juno Mars",
    "version": (1, 2),
    "blender": (2, 80, 0),  # Adjust to your Blender version
    "location": "View3D > Sidebar > JunoTools",
    "description": "Toggle coloring objects based on their triangle counts and display a polycount list",
    "category": "3D View",
}

import bpy

def apply_polycount_coloring(depsgraph=None):
    if depsgraph is None:
        depsgraph = bpy.context.evaluated_depsgraph_get()

    # Get all visible mesh objects in the scene
    mesh_objects = [
        obj for obj in bpy.context.visible_objects
        if obj.type == 'MESH'
    ]

    if not mesh_objects:
        return

    # Get the triangle counts and sort them
    polycounts = []
    for obj in mesh_objects:
        eval_obj = obj.evaluated_get(depsgraph)
        eval_mesh = eval_obj.to_mesh()
        eval_mesh.calc_loop_triangles()
        num_triangles = len(eval_mesh.loop_triangles)
        polycounts.append(num_triangles)
        eval_obj.to_mesh_clear()

    sorted_polycounts = sorted(set(polycounts))
    num_ranks = len(sorted_polycounts) - 1  # Subtract 1 to prevent division by zero

    # Create a mapping from polycount to rank
    polycount_ranks = {polycount: rank for rank, polycount in enumerate(sorted_polycounts)}

    # For each object, store original color and apply new color
    for obj in mesh_objects:
        # Store original color if not already stored
        if "_original_color" not in obj:
            obj["_original_color"] = obj.color[:]

        # Get evaluated object and mesh
        eval_obj = obj.evaluated_get(depsgraph)
        eval_mesh = eval_obj.to_mesh()
        eval_mesh.calc_loop_triangles()
        polycount = len(eval_mesh.loop_triangles)
        eval_obj.to_mesh_clear()

        rank = polycount_ranks[polycount]

        # Compute normalized t value based on rank
        t = rank / num_ranks if num_ranks > 0 else 0.5

        # Clamp t to [0.0, 1.0]
        t = max(0.0, min(1.0, t))

        # Get color from weight paint color spectrum
        color = weight_paint_color(t)
        obj.color = color

    # Set viewport shading to display object colors
    set_viewport_shading_to_object_colors()

def restore_original_colors():
    # Get all objects
    all_objects = bpy.data.objects

    for obj in all_objects:
        if "_original_color" in obj:
            obj.color = obj["_original_color"]
            del obj["_original_color"]

    # Optionally reset the viewport shading
    reset_viewport_shading()

def weight_paint_color(t):
    # Define color stops for the weight paint spectrum
    color_stops = [
        (0.0, (0.0, 0.0, 1.0, 1.0)),   # Blue
        (0.25, (0.0, 1.0, 1.0, 1.0)),  # Cyan
        (0.5, (0.0, 1.0, 0.0, 1.0)),   # Green
        (0.75, (1.0, 1.0, 0.0, 1.0)),  # Yellow
        (1.0, (1.0, 0.0, 0.0, 1.0)),   # Red
    ]

    # Clamp t to [0, 1]
    t = max(0.0, min(1.0, t))

    # Find the two color stops t is between
    for i in range(len(color_stops) - 1):
        t1, color1 = color_stops[i]
        t2, color2 = color_stops[i + 1]
        if t1 <= t <= t2:
            # Normalize t between t1 and t2
            t_normalized = (t - t1) / (t2 - t1)
            return interpolate_color(color1, color2, t_normalized)

    # If t is exactly 1.0
    return color_stops[-1][1]

def interpolate_color(color_start, color_end, t):
    # Linear interpolation of RGBA colors
    return [
        color_start[i] + (color_end[i] - color_start[i]) * t
        for i in range(4)
    ]

def set_viewport_shading_to_object_colors():
    # Set the viewport shading to display object colors
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.shading.type = 'SOLID'
                        space.shading.color_type = 'OBJECT'

def reset_viewport_shading():
    # Reset the viewport shading to default settings
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.shading.type = 'SOLID'
                        space.shading.color_type = 'MATERIAL'

def update_predator_view(self, context):
    if context.scene.predator_view_enabled:
        # Start modal operator
        bpy.ops.wm.predator_view_modal_operator()
    else:
        restore_original_colors()

class VIEW3D_PT_PredatorViewPanel(bpy.types.Panel):
    bl_label = "Predator View"
    bl_idname = "VIEW3D_PT_predator_view_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'JunoTools'

    def draw(self, context):
        layout = self.layout
        layout.prop(context.scene, "predator_view_enabled", toggle=True, text="Enable Predator View")

class VIEW3D_PT_PolycountListPanel(bpy.types.Panel):
    bl_label = "Polycount List"
    bl_idname = "VIEW3D_PT_polycount_list_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'JunoTools'
    bl_parent_id = 'VIEW3D_PT_predator_view_panel'

    @classmethod
    def poll(cls, context):
        return context.scene.predator_view_enabled

    def draw(self, context):
        layout = self.layout
        mesh_objects = [
            obj for obj in bpy.context.visible_objects
            if obj.type == 'MESH'
        ]

        if not mesh_objects:
            layout.label(text="No visible mesh objects.")
            return

        depsgraph = bpy.context.evaluated_depsgraph_get()

        # Get objects with their triangle counts
        obj_polycounts = []
        for obj in mesh_objects:
            eval_obj = obj.evaluated_get(depsgraph)
            eval_mesh = eval_obj.to_mesh()
            eval_mesh.calc_loop_triangles()
            num_triangles = len(eval_mesh.loop_triangles)
            obj_polycounts.append((obj.name, num_triangles))
            eval_obj.to_mesh_clear()

        # Sort the list by polycount in descending order
        obj_polycounts.sort(key=lambda x: x[1], reverse=True)

        # Display the list
        for name, polycount in obj_polycounts:
            row = layout.row()
            row.label(text=name)
            row.label(text=f"{polycount} triangles")

class PredatorViewModalOperator(bpy.types.Operator):
    bl_idname = "wm.predator_view_modal_operator"
    bl_label = "Predator View Modal Operator"

    _timer = None

    def modal(self, context, event):
        if not context.scene.predator_view_enabled:
            self.cancel(context)
            return {'CANCELLED'}

        if event.type == 'TIMER':
            depsgraph = bpy.context.evaluated_depsgraph_get()
            apply_polycount_coloring(depsgraph)
        return {'PASS_THROUGH'}

    def execute(self, context):
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.5, window=context.window)  # Update every 0.5 seconds
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)

classes = (
    VIEW3D_PT_PredatorViewPanel,
    VIEW3D_PT_PolycountListPanel,
    PredatorViewModalOperator,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.predator_view_enabled = bpy.props.BoolProperty(
        name="Predator View Enabled",
        default=False,
        update=update_predator_view
    )

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.predator_view_enabled

if __name__ == "__main__":
    register()
