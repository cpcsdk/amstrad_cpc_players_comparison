# Player benchmark for Amstrad CPC

## Aim

The aim of this repository is to benchmark state-of-the-art music players on Amstrad CPC.

For a given dataset, the music are converted with various replay formats.
An executable is build for each of these formats.
The length of the executable is then retreived to be compared with the other players.

Why using the lenght of this executable and not player and music file ?

 - All extra boilerplate is common with all players, so it does not count in the comparison. We can still substract it.
 - Some players require a buffer. This has to be taken into account with the size.
 - Some players require a save of the stack pointer. This mechanism has to be taken into account, we can consider it takes part of the player routine.
 - Some players require code generation. Even if this code can be removed after usage, this has to be taken into account.

The duration will be collected in future versions. Only FAP allows to retrieve it automatically and easily at the moment.

## Current bugs

 - There is a bug in the execution program for AKY and AKM. The sound is incorrect. This has to be investigated
 - The current ArkosTracker benchmark does not convert formats different than AKS because of some bug somewhere. This has to be fixed to increase dataset size.


## Current limitations

 - This is currently a one man project, the project will be unbiased and finished if other persons join to finish it
 - There is no cache handling => all files are converted/built at each run. It is mandatory to check their existence and not regenerate them !
 - This version has been tested on Windows only. It fails on Linux ATM
 - Player duration has not been taken into account yet. This is mandatory to collect this metric. The choice of the player has to be done on the paret front of a 2d scatter plot on size vs time
 - If have not checked the memory impact of players with code generation. This will be mandatory to adjust figures based on that
 - There is only a single dataset. Various with various properties are expected.
 - AYC cruncher is missing. Either it requires a dedicated PC program (but I have not found a modern one), either it requires emulation with CSL scripting (I have not checked the feasability of the thing)
 - AKM player is used even on music not compatible because they use fancy effects. 
 - FAP does not correct frequency, but AYT does. I do not know if it can be unfair

## Usage

To launch the current benchmark:

```bash
python player_bench.py
```

Additional configurations and options will be added later, depending on community participation.

## Dependencies

The python script uses the following dependencies: `matplotlib`, `seaborn`, `pandas`.
It also requires the `bndbuild` tool which control the various crunchers.


## Datasets evaluation

### ArkosTracker3 AKS dataset
#### Program size

```
format                                  sources   .akm   .aky   .ayt   .fap
0                        Andy Severn - Lop Ears   1944   4138   6590   8642
1                  Doclands - Buzz-o-Meter (YM)   5661   9516  20081   9410
2                 Doclands - Pong Cracktro (YM)   7573  11638  19285  11970
3                    Doclands - Slowly But (YM)   4910   8126  12007   7362
4                    Doclands - The Rivals (YM)   6016  11792  18547   9410
5                      Doclands - The Saga (YM)   5436   9202  15515   8386
6                   Doclands - Tiny Things (YM)   4988   9038  16125  10690
7                   Doclands - Truly Yours (YM)   6077  11912  16527  10434
8                  Doclands - Your Credits (YM)   3812   5876   9890   8642
9       Excellence in Art 2018 - Just add cream   3993   8596  18577  17090
10                         Giherem - Bancaloide   2713   5341  10524   6850
11                         Playing with effects   1864   6366   9580   6594
12                                 SoundEffects   1622   1726   1517   4290
13                 Targhan - A Harmless Grenade   2455   4953   8871   6850
14                               Targhan - Crtc   7611  19382  40287  19906
15                    Targhan - Crtc - End part   2850   9095  11366   8898
16                        Targhan - Hocus Pocus   5830  16559  26206  15560
17                        Totta - BaraBadaBastu   2619   4626   7304   7624
18                             Totta - Crawlers   5358   9998  13622   9928
19                                Totta - Hardy  10606  21410  32639  18376
20                               Totta - Mellow   5447  12919  21977  14530
21                                Totta - Rezzy   6916  13451  19803  12226
22                                Totta - Room5   3450   9311   9863  10690
```
