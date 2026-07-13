"""Launch all Kafka workers, each in its own process.

Usage:
  python workers/run_workers.py --all
  python workers/run_workers.py --only ocr,ner
"""
import argparse
import logging
import multiprocessing as mp
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level="INFO", format="%(asctime)s %(processName)s %(levelname)s %(message)s")

WORKERS = {
    "ocr": "workers.ocr_worker",
    "ner": "workers.ner_worker",
    "embedding": "workers.embedding_worker",
    "graph": "workers.graph_writer",
}


def run(module_name: str):
    import importlib
    importlib.import_module(module_name).main()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--only", type=str, default="")
    args = parser.parse_args()

    names = list(WORKERS) if args.all or not args.only else [n.strip() for n in args.only.split(",")]
    procs = []
    for name in names:
        p = mp.Process(target=run, args=(WORKERS[name],), name=f"{name}-worker")
        p.start()
        procs.append(p)
        logging.info("Started %s worker (pid %d)", name, p.pid)
    for p in procs:
        p.join()


if __name__ == "__main__":
    main()
