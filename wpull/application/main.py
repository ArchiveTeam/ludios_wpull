import sys

from wpull.application.builder import Builder
from wpull.application.options import AppArgumentParser


def main(exit=True, use_signals=True):
    arg_parser = AppArgumentParser()
    args = arg_parser.parse_args()

    builder = Builder(args)
    application = builder.build()

    if use_signals:
        application.setup_signal_handlers()

    if args.debug_manhole:
        import manhole
        import wpull
        wpull.wpull_builder = builder
        manhole.install()

    exit_code = application.run_sync()

    if exit:
        sys.exit(exit_code)
    else:
        return exit_code
