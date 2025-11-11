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
    cmd = f"bndbuild --direct -- SongToYm \\\"{input}\\\" \\\"{output}\\\""
    subprocess.run(cmd, check=True)



class Dataset:
    pass

class At3DatasetSongKind(enum.Enum):
    ST = "128"
    AT3 = "ArkosTracker3"
    AT2 = "ArkosTracker2"
    SKS = "STarKos"
    VT2 = "VT2"
    WYZ = "Wyz"

class At3Dataset(Dataset):
    def __init__(self, file_kinds= None):
        if file_kinds is None:
            file_kinds = [At3DatasetSongKind.SKS, At3DatasetSongKind.AT3, At3DatasetSongKind.AT2]


     #   file_kinds = [At3DatasetSongKind.VT2]
        self.path = os.path.join("datasets", "ArkosTracker3")
        self.file_kinds = file_kinds

    def __iter__(self):
        for kind in self.file_kinds:
            for item in self.iter_kind(kind):
                yield item

    def iter_kind(self, kind: At3DatasetSongKind):
        kind_path = os.path.join(self.path, kind.value)
        for fname in os.listdir(kind_path):
            #does not seem to work with SKS, ST
            if fname.lower().endswith((MusicFormat.AKS.value)):
                if "FenyxKell - BD10n" in fname:
                    continue
                yield os.path.join(kind_path, fname)

