import argparse
import logging
import sys
from typing import Callable, Iterable, List, Optional, Tuple, Type, TypeVar

import i3ipc

from .kitt import Kitti3, Kitts
from .util import AnimParams, Client, CritAttr, Pos, Shape

try:
    from . import __version__
except ImportError:
    __version__ = "N/A"


DEFAULTS = {
    "name": "kitti3",
    "shape": (1.0, 0.4),
    "position": "RIGHT",
    "anim_enter": 0.15,
    "anim_fps": 60,
}

CLIENTS = {
    "kitty": {
        "i3": {
            "cmd": "--no-startup-id kitty --name {}",
            "cattr": CritAttr.INSTANCE,
        },
        "sway": {
            "cmd": "kitty --class {}",
            "cattr": CritAttr.APP_ID,
        },
    },
    "alacritty": {
        "i3": {
            "cmd": "--no-startup-id alacritty --class {}",
            "cattr": CritAttr.INSTANCE,
        },
        "sway": {
            "cmd": "alacritty --class {}",
            "cattr": CritAttr.APP_ID,
        },
    },
    "firefox": {
        "i3": {
            "cmd": "firefox --class {}",
            "cattr": CritAttr.CLASS,
        },
        "sway": {
            "cmd": "GDK_BACKEND=wayland firefox --name {}",
            "cattr": CritAttr.APP_ID,
        },
    },
}


class _ListClientsAction(argparse.Action):
    def __init__(
        self,
        option_strings,
        dest=argparse.SUPPRESS,
        default=argparse.SUPPRESS,
        help=None,
    ):
        super().__init__(
            option_strings=option_strings,
            dest=dest,
            default=default,
            nargs=0,
            help=help,
        )

    def __call__(self, parser, namespace, values, option_string=None):
        print("Kitti3 known clients")
        for client, wms in CLIENTS.items():
            print(f"\n{client}")
            for wm, props in wms.items():
                print(f"  {wm}")
                for prop, val in props.items():
                    print(f"    {prop}: {val}")
        parser.exit()


def _split_args(args: List[str]) -> Tuple[List, Optional[List]]:
    try:
        split = args.index("--")
        return args[:split], args[split + 1 :]
    except ValueError:
        return args, None


def _format_choices(choices: Iterable):
    choice_strs = ",".join([str(choice) for choice in choices])
    return f"{{{choice_strs}}}"


T = TypeVar("T", int, float)


def _num_in(type_: Type[T], min_: T, max_: T) -> Callable[[str], T]:
    def validator(arg: str) -> T:
        try:
            val = type_(arg)
        except ValueError as e:
            raise argparse.ArgumentTypeError(f"'{arg}': {e}") from None
        if not (min_ <= val <= max_):
            raise argparse.ArgumentTypeError(
                f"'{arg}': {val} is not in the range [{min_}, {max_}]"
            )
        return val

    return validator


def _parse_args(argv: List[str], defaults: dict) -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description=(
            "Kitti3: i3/sway floating window handler. Arguments following '--' are"
            " forwarded to the client when spawning"
        )
    )
    ap.set_defaults(**defaults)
    ap.add_argument(
        "-a",
        "--cattr",
        type=CritAttr.from_str,
        choices=list(CritAttr),
        help=(
            f"CATTR ({_format_choices(list(CritAttr))}): criterium attribute used to"
            " match a CLIENT instance to its NAME. Only required if a custom"
            " expression is provided for CLIENT. If CATTR is provided but no CLIENT,"
            " spawning is diabled and assumed to be handled by the user"
        ),
        metavar="",
    )
    _cl = ap.add_argument(
        "-c",
        "--client",
        dest="cmd",
        help=(
            f"CLIENT (cmd exp. or {_format_choices(CLIENTS.keys())}): a custom command"
            " expression or shorthand for one of Kitti3's known clients. For the"
            " former, a placeholder for NAME is required, e.g. 'myapp --class {}"
        ),
        metavar="",
    )
    ap.add_argument(
        "-n",
        "--name",
        help=(
            f"NAME (string, default: '{DEFAULTS['name']}'): name used to identify the"
            " CLIENT via CATTR. Must match the keybinding used in the i3/Sway config"
            " (e.g. `bindsym $mod+n nop NAME`)"
        ),
        metavar="",
    )
    ap.add_argument(
        "-p",
        "--position",
        type=Pos.from_str,
        choices=list(Pos),
        help=(
            f"POSITION ({_format_choices(list(Pos))}, default:"
            f" '{DEFAULTS['position']}'): where to position the client window within"
            " the workspace, e.g. 'TL' for Top Left, or 'BC' for Bottom Center"
            " (character order does not matter)"
        ),
        metavar="",
    )
    _sh = ap.add_argument(
        "-s",
        "--shape",
        nargs=2,
        help=(
            "SHAPE SHAPE (x y, default:"
            f" '{' '.join(str(s) for s in reversed(DEFAULTS['shape']))}'): size of the"
            " client window relative to its workspace. Values can be given as decimals"
            " or fractions, e.g., '1 0.25' and '1.0 1/4' are both interpreted as full"
            " width, quarter height. Note: for backwards compatibility, if POSITION is"
            " 'left' or 'right' (default), the dimensions are interpreted in (y, x)"
            " order"
        ),
        metavar="",
    )
    ap.add_argument(
        "--animate",
        action="store_true",
        help="enable slide-in animation",
    )
    ap.add_argument(
        "--anim-enter",
        type=_num_in(float, 0.01, 1),
        help=(
            f"DURATION (float in [0.01, 1], default: {DEFAULTS['anim_enter']}):"
            " duration of animated slide-in"
        ),
        metavar="",
    )
    ap.add_argument(
        "--anim-fps",
        type=_num_in(int, 1, 100),
        help=(
            f"FPS (int in [1, 100], default: {DEFAULTS['anim_fps']}):"
            " target animation frames per second"
        ),
        metavar="",
    )
    ap.add_argument(
        "--debug",
        action="store_true",
        help="enable diagnostic messages",
    )

    ap.add_argument(
        "--list-clients",
        action=_ListClientsAction,
        help="list Kitti3's known clients and their command expressions",
    )
    ap.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="show %(prog)s's version number and exit",
    )
    args = ap.parse_args(argv)

    try:
        args.shape = Shape.from_strs(args.shape, args.position.compat)
    except argparse.ArgumentTypeError as e:
        ap.error(str(argparse.ArgumentError(_sh, str(e))))

    if args.cmd is None:
        # default to Kitty for backwards compatibility
        if args.cattr is None:
            args.cmd = "kitty"
    elif args.cmd not in CLIENTS:
        if args.cattr is None:
            msg = (
                f"'{args.cmd}' is not a known client; if it is a custom expression,"
                " CATTR must also be provided"
            )
            ap.error(str(argparse.ArgumentError(_cl, msg)))
        elif "{}" not in args.cmd:
            msg = (
                f"custom client expression '{args.cmd}' must contain a '{{}}'"
                " placeholder for NAME"
            )
            ap.error(str(argparse.ArgumentError(_cl, msg)))

    args.anim_params = AnimParams(
        args.animate, args.position.anchor, args.anim_enter, args.anim_fps
    )

    return args


def cli() -> None:
    argv_kitti3, argv_client = _split_args(sys.argv[1:])
    args = _parse_args(argv_kitti3, DEFAULTS)

    if args.debug:
        logging.basicConfig(
            datefmt="%Y-%m-%dT%H:%M:%S",
            format=(
                "%(asctime)s.%(msecs)03dZ %(levelname)-7s"
                " %(filename) 4s:%(lineno)03d"
                " %(name)s.%(funcName)-12s %(message)s"
            ),
            level=logging.DEBUG,
        )

    # FIXME: half-baked way of checking what WM we're running on.
    conn = i3ipc.Connection()
    sway = "sway" in conn.socket_path  # or conn.get_version().major < 3
    _Kitt = Kitts if sway else Kitti3

    if args.cmd in CLIENTS:
        c = CLIENTS[args.cmd]["sway" if sway else "i3"]
        args.cmd = c["cmd"]
        args.cattr = c["cattr"]
    client = Client(args.cmd, args.cattr)

    kitt = _Kitt(
        conn=conn,
        name=args.name,
        shape=args.shape,
        pos=args.position,
        client=client,
        client_argv=argv_client,
        anim=args.anim_params,
    )
    kitt.loop()
