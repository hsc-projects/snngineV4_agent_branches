
class OpenglTextureDataError(AssertionError):
    pass


class RegisteredTexture3D(RegisteredOpenGLObject):

    def __init__(self,
                 parent,
                 texture_id,
                 cpu_data: np.ndarray,
                 device: Union[torch.device, int],
                 stream: int = 0):

        np_dtype = np.float32
        nbytes = numpy_dtype_to_byte_size_dict[np_dtype]
        strides = (cpu_data.shape[1] * (nbytes ** 2),
                   cpu_data.shape[2] * nbytes,
                   nbytes),

        # noinspection PyUnresolvedReferences
        reg = RegisteredImage(texture_id, gl.GL_TEXTURE_3D,
                              graphics_map_flags.NONE
                              # graphics_map_flags.WRITE_DISCARD
                              )
        mapping: RegisteredMapping = reg.map(None)
        gpu_data = mapping.array(0, 0)
        ptr = gpu_data.handle
        # noinspection PyArgumentList
        mapping.unmap()

        # noinspection PyTypeChecker
        super().__init__(parent=parent,
                         shape=cpu_data.shape, strides=strides,
                         gpu_data=gpu_data,
                         register_buffer=reg,
                         mapping=mapping,
                         register_buffer_ptr=ptr,
                         opengl_id=texture_id,
                         np_dtype=np_dtype,
                         device=device,
                         stream=stream)

        self.tensor: torch.Tensor = torch.zeros(self._shape, device=self._device,
                                                dtype=numpy_to_torch_dtype_dict[np.float32])

        # noinspection PyArgumentList
        self._cpy_tnsr2tex = pycuda.driver.Memcpy3D()
        self._cpy_tnsr2tex.set_src_device(self.tensor.data_ptr())
        self._cpy_tnsr2tex.set_dst_array(self._gpu_data)

        # noinspection PyArgumentList
        self._cpy_tex2tnsr = pycuda.driver.Memcpy3D()
        self._cpy_tex2tnsr.set_src_array(self._gpu_data)
        self._cpy_tex2tnsr.set_dst_device(self.tensor.data_ptr())

        self._cpy_tnsr2tex.width_in_bytes = self._cpy_tex2tnsr.width_in_bytes = nbytes * self._shape[2]

        self._cpy_tnsr2tex.src_pitch = self._cpy_tex2tnsr.src_pitch = nbytes * self._shape[2]

        self._cpy_tnsr2tex.src_height = self._cpy_tnsr2tex.height\
            = self._cpy_tex2tnsr.src_height = self._cpy_tex2tnsr.height = self._shape[1]

        self._cpy_tnsr2tex.depth = self._cpy_tex2tnsr.depth = self._shape[0]

        # self.cpy_tnsr2tex()
        self.cpy_tex2tnsr(cpu_data)

    def cpy_tnsr2tex(self, cpu_data=None):
        """
        TODO: Restrict copying to actually modified data.
        """
        # self.map()
        #
        # if cpu_data is not None:
        #     self.tensor[:] = torch.from_numpy(cpu_data)
        # torch.cuda.synchronize()
        # noinspection PyArgumentList
        self._cpy_tnsr2tex()
        return

    def cpy_tex2tnsr(self, cpu_data=None, validate: bool = True):
        self.map()
        torch.cuda.synchronize()
        # noinspection PyArgumentList
        self._cpy_tex2tnsr()
        if cpu_data is not None:
            t = self.tensor.cpu().numpy()
            if (validate is True) and (((cpu_data - t) != 0).all()):
                raise OpenglTextureDataError("((cpu_data - t) != 0).all()")
        return