"""Run the findingtrace experiment."""

import argparse

from findingtrace import DATA_DIR, run


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--data", default=DATA_DIR)
    args = parser.parse_args(argv)
    run.main(data_dir=args.data, out=args.out)


if __name__ == "__main__":
    main()
