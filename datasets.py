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

class MusicFormat(enum.Enum):
    AKS = "aks"
    ST = "128"
    SKS = "sks"
    YM6 = "ym"
    YM3 = "ym3"
    VT2 = "vt2"
    WYZ = "wyz"

    def get_format(fname: str) -> 'MusicFormat':
        ext = fname.split('.')[-1].lower()
        for fmt in MusicFormat:
            if fmt.value == ext:
                return fmt
        raise ValueError(f"Unsupported music format: {ext}")

    def convertible_to(self):
        return  {self, MusicFormat.YM6}




def convert_music_file(input_file: str, output_file: str):

    if os.path.exists(output_file):
        return

    input_format = MusicFormat.get_format(input_file)
    output_format = MusicFormat.get_format(output_file)

    if input_format == output_format:
        shutil.copyfile(input_file, output_file)
    elif input_format in [MusicFormat.ST, MusicFormat.SKS, MusicFormat.AKS, MusicFormat.VT2, MusicFormat.WYZ] and output_format == MusicFormat.YM6:
        convert_at_to_ym(input_file, output_file)
    else:
        raise NotImplementedError(f"Conversion between different {input_format} and {output_format} is not implemented yet.")


def convert_at_to_ym(input, output):
  #  cmd = f"tools\\SongToYm.exe \\\"{input}\\\" \\\"{output}\\\""
    cmd = f"bndbuild --direct -- SongToYm  \\\"{input}\\\" \\\"{output}\\\" "
    logging.debug(f"AT2YM: {cmd}")
    subprocess.run(cmd, check=True)



class Dataset:
    def __init__(self):
        self.clean_patterns = [
            "**/*.BIN",
            "**/*.sna",
            "**/*.ym", #XXX this ine can be dangerous for new datasets
            "**/*.ayt",
            "**/*.akg",
            "**/*.akm",
            "**/*.aky",
            "**/*.fap",
            "**/*.json",
        ]

    def clean(self):
        for pat in self.clean_patterns:
            for f in glob.glob(pat, root_dir=self.root(), recursive=True):
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
    
class At3Dataset(Dataset):
    def __init__(self, file_kinds= None):
        super().__init__()
        if file_kinds is None:
            file_kinds = [At3DatasetSongKind.SKS, At3DatasetSongKind.AT3, At3DatasetSongKind.AT2, At3DatasetSongKind.ST]
            file_kinds = [At3DatasetSongKind.AT3, At3DatasetSongKind.AT2, At3DatasetSongKind.ST]


     #   file_kinds = [At3DatasetSongKind.VT2]
        self.path = os.path.join("datasets", "ArkosTracker3")
        self.file_kinds = file_kinds

    def root(self):
        return self.path

    def __iter__(self):
        for kind in self.file_kinds:
            for item in self.iter_kind(kind):
                yield item

    def iter_kind(self, kind: At3DatasetSongKind):
        kind_path = os.path.join(self.path, kind.value)
        for fname in os.listdir(kind_path):
            ext = os.path.splitext(fname)[1][1:].upper()
            if any([ext == kind.extension() for kind in self.file_kinds]) and not (
                "BD10" in fname or "Bobline" in fname
            ):
                logging.info(f"{fname} will be handled thanks to type {ext}")
                yield os.path.join(kind_path, fname)
            else:
                logging.info(f"{fname} has been filtered out ({ext})")


