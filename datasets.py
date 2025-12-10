#!/usr/bin/env python3
# -*- coding: utf-8 -*-


# Filename: player_bench.py
# License: MIT License
# Author: Krusty/Benediction
# Date: 2025-11-11
# Version: 0.1
# Description: This file describes the datasets that can be used within a benchmark


import enum
import shutil
import os
import subprocess
import logging
import glob
from abc import ABC, abstractmethod
from utils import execute_process


class MusicFormat(enum.Enum):
    AKS = "aks"
    CHP = "CHP"
    SKS = "sks"
    ST = "128"
    VT2 = "vt2"
    WYZ = "wyz"
    YM3 = "ym3"
    YM6 = "ym"

    @staticmethod
    def get_format(fname: str) -> "MusicFormat":
        ext = fname.split(".")[-1].lower()
        for fmt in MusicFormat:
            if fmt.value.lower() == ext.lower():
                return fmt
        raise ValueError(f"Unsupported music format: {ext}")

    def convertible_to(self) -> set:
        if self == MusicFormat.CHP:
            return {self, MusicFormat.YM3}
        else:
            return {self, MusicFormat.YM6}


def convert_music_file(input_file: str, output_file: str) -> None:
    logging.info(f"Convert {input_file} to {output_file}")

    if os.path.exists(output_file):
        return

    input_format = MusicFormat.get_format(input_file)
    output_format = MusicFormat.get_format(output_file)

    if input_format == output_format:
        shutil.copyfile(input_file, output_file)
    elif (
        input_format
        in [
            MusicFormat.ST,
            MusicFormat.SKS,
            MusicFormat.AKS,
            MusicFormat.VT2,
            MusicFormat.WYZ,
        ]
        and output_format == MusicFormat.YM6
    ):
        convert_at_to_ym6(input_file, output_file)
    elif input_format == MusicFormat.CHP and output_format in [
        MusicFormat.YM3,
        MusicFormat.YM6,
    ]:
        convert_chp_to_ym3(input_file, output_file)
    else:
        raise NotImplementedError(
            f"Conversion between different {input_format} and {output_format} is not implemented yet."
        )


def convert_at_to_ym6(input, output):
    #  cmd = f"tools\\SongToYm.exe \\\"{input}\\\" \\\"{output}\\\""
    cmd = f'bndbuild --direct -- SongToYm  \\"{input}\\" \\"{output}\\" '
    execute_process(cmd)


def convert_chp_to_ym3(input, output):
    cmd = f'bndbuild --direct -- chipnsfx  \\"{input}\\" -y \\"{output}\\" '
    execute_process(cmd)


class Dataset(ABC):
    def __init__(self, path):
        assert path is not None

        self.clean_patterns = [
            "*.akg",
            "*.akm",
            "*.aky",
            "*.ayt",
            "*.BIN",
            "*.CHPB",
            "*.CHPZ80",
            "*.CSV",
            "*.fap",
            "*.json",
            "*.sna",
            "*.ym",  # XXX this ine can be dangerous for new datasets
            "*.zx0"
        ]
        self.clean_pattern_folder_part = None
        self.path = path

    def root(self):
        return self.path

    @abstractmethod
    def __iter__(self):
        """Return an iterator over dataset items"""
        pass

    def iter_json(self):
        return iter(glob.glob(os.path.join(self.root(), "*.json")))

    def clean(self):
        for pat in self.clean_patterns:
            print(pat, self.root())
            for f in glob.glob(os.path.join("**",pat), root_dir=self.root(), recursive=True):
                f = os.path.join(self.root(), f)
                logging.info(f"Delete {f}")
                os.remove(f)


class At3DatasetSongKind(enum.Enum):
    ST = "128"
    AT3 = "ArkosTracker3"
    AT2 = "ArkosTracker2"
    SKS = "STarKos"
    VT2 = "VT2"
    WYZ = "Wyz"

    def extension(self):
        return {
            At3DatasetSongKind.ST: MusicFormat.ST,
            At3DatasetSongKind.AT2: MusicFormat.AKS,
            At3DatasetSongKind.AT3: MusicFormat.AKS,
            At3DatasetSongKind.SKS: MusicFormat.SKS,
            At3DatasetSongKind.VT2: MusicFormat.VT2,
            At3DatasetSongKind.WYZ: MusicFormat.WYZ,
        }[self].name


class ChpDataset(Dataset):
    def __init__(self):
        super().__init__(os.path.join("datasets", "chipnsfx"))

    def __iter__(self):
        for f in glob.glob(os.path.join(self.root(), "*.CHP")):
            yield f


class At3Dataset(Dataset):
    def __init__(self, file_kinds=None):
        super().__init__(os.path.join("datasets", "ArkosTracker3"))
        if file_kinds is None:
            file_kinds = [
                At3DatasetSongKind.SKS,
                At3DatasetSongKind.AT3,
                At3DatasetSongKind.AT2,
                At3DatasetSongKind.ST,
                At3DatasetSongKind.VT2,
                At3DatasetSongKind.WYZ,
            ]

        #   file_kinds = [At3DatasetSongKind.VT2]
        self.file_kinds = file_kinds

    def __iter__(self):
        for kind in self.file_kinds:
            for item in self.iter_kind(kind):
                yield item

    def iter_kind(self, kind: At3DatasetSongKind):
        kind_path = os.path.join(self.root(), kind.value)
        for fname in os.listdir(kind_path):
            ext = os.path.splitext(fname)[1][1:].upper()
            if any([ext == available_kind.extension() for available_kind in self.file_kinds]):
                logging.info(f"{fname} will be handled thanks to type {ext}")
                yield os.path.join(kind_path, fname)
            else:
                logging.info(f"{fname} has been filtered out ({ext})")

    def iter_json(self):
        for kind in self.file_kinds:
            kind_path = os.path.join(self.root(), kind.value)
            for f in glob.glob(os.path.join(kind_path, "*.json")):
                yield f
