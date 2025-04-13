import numpy as np
from vispy import gloo
from vispy.color import Color
from vispy.scene.visuals import create_visual_node
from vispy.util.profiler import Profiler
from vispy.visuals import BoxVisual, CompoundVisual, Visual, LineVisual
# noinspection PyProtectedMember
from vispy.visuals.line.line import _GLLineVisual
from vispy.visuals.shaders import Function
from vispy.visuals.transforms import create_transform, STTransform

from snngine_v4.geometry.grid.finite_grid import FiniteGrid


class GSGLLineVisual(_GLLineVisual):
    _shaders = {
        'vertex': """
            varying out vec4 v_color;

            void main(void) {
                gl_Position = $transform($to_vec4($position));
                v_color = $color;
            }
        """,
        'fragment': """

            varying in vec4 g_color;

            void main() {
                gl_FragColor = g_color;
            }
        """
    }
    # _shaders = {
    #     'vertex': """
    #         out vec4 v_color;
    #
    #         void main(void) {
    #             gl_Position = $transform($to_vec4($position));
    #             v_color = $color;
    #         }
    #     """,
    #     'fragment': """
    #
    #         attribute vec4 g_color;
    #
    #         void main() {
    #             gl_FragColor = g_color;
    #         }
    #     """
    # }

    def __init__(self, parent, gcode):
        self._parent = parent
        self._pos_vbo = gloo.VertexBuffer()
        self._color_vbo = gloo.VertexBuffer()
        self._connect_ibo = gloo.IndexBuffer()
        self._connect = None

        Visual.__init__(self, vcode=self._shaders['vertex'],
                        gcode=gcode,
                        fcode=self._shaders['fragment'])
        self.set_gl_state('translucent')

    def _prepare_transforms(self, view):
        xform = view.transforms.get_transform()

        view.view_program.vert['transform'] = xform
        if view.view_program.geom is not None:
            # xform = view.transforms.get_transform(
            # map_from='visual', map_to='render')
            view.view_program.geom['transform'] = xform
            view.view_program.geom['transform_inv'] = (
                view.transforms.get_transform(map_from='render',
                                              map_to='visual'))

    # noinspection DuplicatedCode,PyProtectedMember
    def _prepare_draw(self, view):
        prof = Profiler()

        if self._parent._changed['pos']:
            if self._parent._pos is None:
                return False
            # TODO: Use self._pos_vbo.set_subdata(pos)
            pos = np.ascontiguousarray(self._parent._pos.astype(np.float32))
            self._pos_vbo.set_data(pos)
            self._program.vert['position'] = self._pos_vbo
            # self._program.geom['position'] = self._pos_vbo
            self._program.vert['to_vec4'] = self._ensure_vec4_func(
                pos.shape[-1])
            # self._program.geom['to_vec4'] =
            # self._ensure_vec4_func(pos.shape[-1])
            self._parent._changed['pos'] = False

        if self._parent._changed['color']:
            color, cmap = self._parent._interpret_color()
            # If color is not visible, just quit now
            if isinstance(color, Color) and color.is_blank:
                return False
            if isinstance(color, Function):
                # TODO: Change to the parametric coordinates once that is done
                self._program.vert['color'] = color(
                    '(gl_Position.x + 1.0) / 2.0')
            else:
                if color.ndim == 1:
                    self._program.vert['color'] = color
                else:
                    self._color_vbo.set_data(color)
                    self._program.vert['color'] = self._color_vbo
            self._parent._changed['color'] = False

            self.shared_program['texture2D_LUT'] = cmap and cmap.texture_lut()

            # noinspection PyTypeChecker
        # noinspection PyTypeChecker,PydanticTypeChecker
        self.update_gl_state(line_smooth=bool(self._parent._antialias))
        px_scale = self.transforms.pixel_scale
        width = px_scale * self._parent._width
        self.update_gl_state(line_width=max(width, 1.0))

        if self._parent._changed['connect']:
            self._connect = self._parent._interpret_connect()
            if isinstance(self._connect, np.ndarray):
                self._connect_ibo.set_data(self._connect)
            self._parent._changed['connect'] = False
        if self._connect is None:
            return False

        prof('prepare')

        # Draw
        if isinstance(self._connect, str) and \
                self._connect == 'strip':
            self._draw_mode = 'line_strip'
            self._index_buffer = None
        elif isinstance(self._connect, str) and \
                self._connect == 'segments':
            self._draw_mode = 'lines'
            self._index_buffer = None
        elif isinstance(self._connect, np.ndarray):
            self._draw_mode = 'lines'
            self._index_buffer = self._connect_ibo
        else:
            raise ValueError("Invalid line connect mode: %r" % self._connect)

        prof('draw')


class GSLineVisual(LineVisual):

    def __init__(self, gcode, pos: np.ndarray = None, color=(1., 1., 1., 1.),
                 width=1,
                 connect='strip', method='gl', antialias=False):
        self.gcode = gcode
        # noinspection PyTypeChecker,PydanticTypeChecker
        super().__init__(pos=pos, color=color, width=width, connect=connect,
                         method=method, antialias=antialias)
        # self.unfreeze()
        #
        # self.freeze()

    @property
    def method(self):
        return self._method

    @method.setter
    def method(self, method):

        if method not in ('agg', 'gl'):
            raise ValueError('method argument must be "agg" or "gl".')
        if method == self._method:
            return

        self._method = method
        if self._line_visual is not None:
            self.remove_subvisual(self._line_visual)

        if method == 'gl':
            self._line_visual = GSGLLineVisual(self, gcode=self.gcode)
        elif method == 'agg':
            raise NotImplementedError()
            # self._line_visual = _AggLineVisual(self)
        self.add_subvisual(self._line_visual)

        for k in self._changed:
            self._changed[k] = True

    # @property
    # def visible(self):
    #     return super().visible


class MultiBoxLinesVisual(GSLineVisual):

    def __init__(self, lattice, technical_max_z_value,
                 pos: np.ndarray = None, color=(1., 1., 1., 1.), width=1,
                 connect='strip', method='gl', antialias=False):

        if not isinstance(color, np.ndarray) or color.shape[0] != pos.shape[0]:
            if not isinstance(color, (list, tuple, np.ndarray)):
                raise ValueError('color must be a list, tuple or numpy array.')
            elif len(color) != 4:
                color = [*color, 1.]
            color_array = np.ones((pos.shape[0], 4), dtype=np.float32)
            color_array[:] = color
            color = color_array

        gcode = f"""
                // #version 430

                layout (lines) in;
                layout (line_strip, max_vertices=16) out;

                in vec4 v_color[];
                out vec4 g_color;

                void main(void){{

                    float size_x = {lattice[0]}f;
                    float size_y = {lattice[1]}f;
                    float size_z = {lattice[2]}f;

                    g_color = v_color[0];

                    // gl_PointSize = 75;

                    vec4 source_pos = gl_in[0].gl_Position;

                    if ($transform_inv(source_pos).z > {technical_max_z_value}f)
                    {{
                        return;
                    }}

                    vec4 x_offset = $transform(vec4(size_x, 0.f, 0.f, 0.f));
                    vec4 y_offset = $transform(vec4(0.f, size_y, 0.f, 0.f));
                    vec4 z_offset = $transform(vec4(0.f, 0.f, size_z, 0.f));

                    vec4 o = source_pos;
                    vec4 x = source_pos + x_offset;
                    vec4 y = source_pos + y_offset;
                    vec4 z = source_pos + z_offset;
                    vec4 xy = source_pos + x_offset + y_offset;
                    vec4 xz = source_pos + x_offset + z_offset;
                    vec4 yz = source_pos + y_offset + z_offset;
                    vec4 xyz = source_pos + x_offset + y_offset + z_offset;

                    gl_Position = o;
                    EmitVertex();
                    gl_Position = x;
                    EmitVertex();
                    gl_Position = xz;
                    EmitVertex();
                    gl_Position = z;
                    EmitVertex();
                    gl_Position = yz;
                    EmitVertex();
                    gl_Position = xyz;
                    EmitVertex();
                    gl_Position = xz;
                    EmitVertex();
                    gl_Position = xyz;
                    EmitVertex();
                    gl_Position = xy;
                    EmitVertex();
                    gl_Position = x;
                    EmitVertex();
                    gl_Position = xy;
                    EmitVertex();
                    gl_Position = y;
                    EmitVertex();
                    gl_Position = o;
                    EmitVertex();
                    gl_Position = z;
                    EmitVertex();
                    gl_Position = yz;
                    EmitVertex();
                    gl_Position = y;
                    EmitVertex();
                    EndPrimitive();

                }}
            """

        super().__init__(gcode=gcode, pos=pos, color=color, width=width,
                         connect=connect, method=method,
                         antialias=antialias)


class FiniteGridLinesVisual(BoxVisual):
    """
    Base class for all visual nodes that are associated with a finite grid.
    """
    def __init__(self,
                 grid,
                 connect=None,
                 line_color=(0.1, 1., 1., 1.),
                 **box_kwargs):

        self.grid: FiniteGrid = grid

        if connect is None:
            connect = np.zeros((self.grid.n_technical_segments, 2),
                               dtype=np.uint32)
            connect[:, 0] = np.arange(grid.n_technical_segments)
            connect[:, 1] = np.arange(grid.n_technical_segments) + 1

        self.lines_visual: MultiBoxLinesVisual = MultiBoxLinesVisual(
            lattice=self.grid.lattice,
            technical_max_z_value=self.grid.technical_max_z_value,
            connect=connect,
            pos=self.grid._pos - (self.grid.shape / 2).astype(np.float32),
            color=line_color)

        BoxVisual.__init__(self, **box_kwargs)

        self.unfreeze()

        # self._transform = None
        # self.transform: STTransform = STTransform(
        #     translate=(0, 0, 0), scale=(1, 1, 1))
        # self.transform.move(self._grid.shape / 2)
        # self.transforms.changed()

        self.add_subvisual(self.lines_visual)
        # self.lines_visual.transform = STTransform(
        #     translate=(0, 0, 0), scale=(1, 1, 1))
        # self.lines_visual.transform.move(-self.grid.shape / 2)
        # self.lines_visual.transforms.changed()


        # noinspection PyTypeChecker,PydanticTypeChecker
        self.lines_visual.set_gl_state(
            polygon_offset_fill=True,
            polygon_offset=(1, 1), depth_test=False, blend=True)

        self.freeze()
        # self.G_flags: Optional[VisualizedGridGroupFlags] = None
        # self.G_props: Optional[VisualizedGridGroupProperties] = None
        # self.g2g_info_arrays: Optional[G2GInfoArrays] = None


# FiniteGridLines = create_visual_node(FiniteGridLinesVisual)
# FiniteGridLines = FiniteGridLinesVisual
