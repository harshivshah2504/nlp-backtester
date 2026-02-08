try:
    from ._version import version as __version__  # noqa: F401
except ImportError:
    __version__ = '?.?.?'  # Package not installed

from . import lib  # noqa: F401
from ._plotting import set_bokeh_output  # noqa: F401
from .backtesting import Backtest, Strategy  # noqa: F401
from . import quantstats
#from .quantstats import quantstats