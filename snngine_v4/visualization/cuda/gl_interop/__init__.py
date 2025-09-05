try:
    from snngine_v4.visualization.cuda.gl_interop.gl_tensor_dict \
        import GLTensorDict
except ModuleNotFoundError:
    class GLTensorDict:
        pass