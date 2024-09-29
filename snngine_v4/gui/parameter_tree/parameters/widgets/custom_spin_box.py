from pyqtgraph import SpinBox

from snngine_v4.utils.settings.ui_parameter_options import ParamOpts


class CustomSpinBox(SpinBox):

    @classmethod
    def from_opts(cls, **opts):
        sp = cls()
        t = opts[ParamOpts.KW.TYPE]
        defs = {
            ParamOpts.KW.VALUE: 0,
            ParamOpts.KW.MIN: None,
            ParamOpts.KW.MAX: None,
            ParamOpts.KW.STEP: 1.0,
            ParamOpts.KW.DEC: False,
            ParamOpts.KW.SI_PREFIX: False,
            ParamOpts.KW.SUFFIX: '',
            ParamOpts.KW.DECIMALS: 3,
        }
        if t == ParamOpts.KW.INT:
            defs[ParamOpts.KW.INT] = True
            defs[ParamOpts.KW.MIN_STEP] = 1.0
        for k in sp.opts:
            if k in opts:
                defs[k] = opts[k]
        if opts.get(ParamOpts.KW.BOUNDS) is not None:
            pass
        elif opts.get(ParamOpts.KW.LIMITS) is not None:
            defs[ParamOpts.KW.MIN], defs[ParamOpts.KW.MAX] = (
                opts)[ParamOpts.KW.LIMITS]
        sp.setOpts(**defs)
        return sp

    def selectNumber(self):
        """
        Select the numerical portion of the text to allow quick editing by the user.
        """
        le = self.lineEdit()
        text = le.text()
        prefix = self.opts['prefix']
        len_prefix = len(prefix) if isinstance(prefix, str) else 0
        b_prefix = (len_prefix > 0 and text.startswith(prefix))
        if b_prefix:
            text = text[len_prefix + 1:]
        m = self.opts['regex'].match(text)
        if m is None:
            return
        s, e = m.start('number'), m.end('number')
        if b_prefix:
            s, e = s + len_prefix + 1, e + len_prefix + 1
        le.setSelection(s, e-s)

    def _updateHeight(self):
        pass
