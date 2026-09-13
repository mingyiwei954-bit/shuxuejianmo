import argparse
from .config import load_config
from .data import load_data
from .experiments import run_all

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--config',default='config/final.yaml');ap.add_argument('--scope',choices=['all','train','official'],default='all');a=ap.parse_args();cfg=load_config(a.config);run_all(load_data(cfg),cfg,a.scope);return 0
