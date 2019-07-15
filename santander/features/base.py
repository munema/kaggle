# -- coding: utf-8 --
import argparse
import inspect
import re
from abc import ABCMeta, abstractmethod
from pathlib import Path
import feather
import sys
import os
import pandas as pd
import numpy as np
sys.path.append(os.getcwd())
from utils.__init__ import timer
from function import config_json


def get_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--force', '-f', action='store_true', help='Overwrite existing files'
    )
    return parser.parse_args()

def get_features(namespace):
    for k, v in namespace.items():
        if inspect.isclass(v) and issubclass(v, Feature) \
                and not inspect.isabstract(v):
            yield v()

def generate_features(namespace, overwrite):
    for f in get_features(namespace):
        if f.train_path.exists() and f.test_path.exists() and not overwrite:
            print(f.name, 'was skipped')
        else:
            f.run().save()

def generate_dataframe(namespace):
    tr = pd.DataFrame(columns=[], index=[])
    te = pd.DataFrame(columns=[], index=[])
    for f in get_features(namespace):
        if f.train_path.exists() and f.test_path.exists():
            f.load()
            print("{} : {}".format(f.name,f.train.shape[1]))
            tr = pd.concat([tr, f.train], axis = 1)
            te = pd.concat([te, f.test], axis = 1)
    return tr, te

def get_features_to_json(namespace, overwrite=False):
    name_list = []
    for f in get_features(namespace):
        name_list.append(f.name)
    config_json.name_to_json(name_list, overwrite)


class Feature(metaclass=ABCMeta):
    prefix = ''
    suffix = ''
    dir = '.'

    def __init__(self):
        if self.__class__.__name__.isupper():
            self.name = self.__class__.__name__.lower()
        else:
            self.name = re.sub(
                "([A-Z])",
                lambda x: "_" + x.group(1).lower(), self.__class__.__name__
            ).lstrip('_')

        self.train = pd.DataFrame()
        self.test = pd.DataFrame()
        self.train_path = Path(self.dir) / "feather" / f'{self.name}_train.feather'
        self.test_path = Path(self.dir) / "feather" / f'{self.name}_test.feather'

    def run(self):
        with timer(self.name):
            self.create_features()
            prefix = self.prefix + '_' if self.prefix else ''
            suffix = '_' + self.suffix if self.suffix else ''
            self.train.columns = prefix + self.train.columns + suffix
            self.test.columns = prefix + self.test.columns + suffix
        return self

    @abstractmethod
    def create_features(self):
        raise NotImplementedError

    def save(self):
        self.train.to_feather(str(self.train_path))
        self.test.to_feather(str(self.test_path))

    def load(self):
        self.train = feather.read_dataframe(str(self.train_path))
        self.test = feather.read_dataframe(str(self.test_path))