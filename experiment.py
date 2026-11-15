"""Run the findingtrace experiment."""

import argparse

from findingtrace import DATA_DIR, run


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--data", default=DATA_DIR)
    parser.add_argument("--v2-out", help="also write the SPEC-v2 metrics here")
    parser.add_argument("--heldout-out", help="also write the blind hold-out scores here")
    args = parser.parse_args(argv)
    run.main(data_dir=args.data, out=args.out)
    if args.v2_out:
        run.main(data_dir=args.data, out=args.v2_out, v2=True)
    if args.heldout_out:
        run.main_heldout(data_dir=args.data, out=args.heldout_out)


if __name__ == "__main__":
    main()
