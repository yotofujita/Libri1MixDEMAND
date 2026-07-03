# LibriDEMAND

LibriDEMAND is a dataset-generation repository for creating noisy single-speaker speech mixtures from LibriSpeech speech and DEMAND environmental noise. This codebase was created from a fork of the original LibriMix repository and keeps the LibriMix-style metadata and waveform generation pipeline while replacing WHAM noise with DEMAND-derived noise segments.

This repository currently targets the `Libri1MixDemand` configuration:

- one LibriSpeech source utterance plus one DEMAND noise source
- `mix_single` mixtures only
- `wav16k` output only
- `min` length mode only
- fixed metadata supplied under `metadata/`

## Requirements

Install the Python dependencies:

```bash
pip install -r requirements.txt
```

The augmentation step uses `pysndfx`, which depends on SoX. If augmentation fails with an audio effects error, install SoX with your system package manager.

## Input Data

Prepare a storage directory with the DEMAND dataset placed at:

```text
<storage_dir>/
  DEMAND/
    <noise_type>/
      ch01.wav
```

Only `ch01.wav` from each DEMAND noise type is used. LibriSpeech `train-clean-100` is downloaded automatically if it is not already present at:

```text
<storage_dir>/LibriSpeech/train-clean-100
```

## Generate LibriDEMAND

Run:

```bash
./generate_libri1mix_demand.sh <storage_dir>
```

The script performs these steps:

1. Downloads LibriSpeech `train-clean-100` if needed.
2. Converts DEMAND into LibriMix-compatible `tr`, `cv`, and `tt` noise splits.
3. Augments DEMAND training noise with speed factors `0.8` and `1.2`.
4. Uses the fixed metadata in `metadata/LibriSpeech/for_demand/` and `metadata/Demand_noise/`.
5. Creates mixture metadata in `metadata/Libri1MixDemand/`.
6. Writes generated waveforms under `<storage_dir>/Libri1MixDemand/`.

## Output Layout

The generated dataset is written as:

```text
<storage_dir>/Libri1MixDemand/
  wav16k/
    min/
      train-100/
        s1/
        noise/
        mix_single/
      dev/
        s1/
        noise/
        mix_single/
      test/
        s1/
        noise/
        mix_single/
      metadata/
```

`mix_single` contains the noisy speech mixture. `s1` contains the scaled speech source, and `noise` contains the scaled DEMAND noise source.

## Important Notes

The DEMAND split script creates 8-second, non-overlapping segments by default and stores them in `demand_noise/tr`, `demand_noise/cv`, and `demand_noise/tt`. The split is deterministic because `scripts/create_demand_splits.py` fixes the random seed.

The DEMAND metadata is not regenerated during the main script. The files in `metadata/Demand_noise/` are fixed inputs to the LibriMix metadata stage, so the generated `demand_noise` files must match those metadata entries. With the expected DEMAND input, the original training split contains 449 segments and becomes 1347 files after speed augmentation.

The LibriSpeech metadata in `metadata/LibriSpeech/for_demand/` is also fixed. Although the files are named `train-clean-100`, `dev-clean`, and `test-clean` to match the LibriMix metadata convention, they reference utterances from LibriSpeech `train-clean-100`.

Existing output directories are not overwritten by `scripts/create_librimix_from_metadata.py`. Remove the corresponding output directory before rerunning generation if you need to regenerate waveforms.

## Debug With Dummy Inputs

For quick pipeline debugging, you can generate synthetic LibriSpeech and DEMAND-like files that satisfy the fixed metadata paths:

```bash
python scripts/create_dummy_inputs.py --storage_dir /tmp/libridemand-debug --max_seconds 1.0
./generate_libri1mix_demand.sh /tmp/libridemand-debug
```

The dummy script creates:

- `/tmp/libridemand-debug/LibriSpeech/train-clean-100/.../*.flac`
- `/tmp/libridemand-debug/demand_noise/{tr,cv,tt}/*.wav`

Because `demand_noise` is pre-created, the main generation script skips DEMAND splitting. The dummy audio is synthetic and should be used only to verify the pipeline, file layout, multiprocessing behavior, and metadata handling.

## Scripts

- `generate_libri1mix_demand.sh`: end-to-end LibriDEMAND generation entry point.
- `scripts/create_dummy_inputs.py`: creates synthetic inputs for pipeline debugging.
- `scripts/create_demand_splits.py`: converts DEMAND `ch01.wav` files into LibriMix-compatible noise splits.
- `scripts/augment_train_noise.py`: creates `sp08` and `sp12` speed-augmented training noise files.
- `scripts/create_librimix_metadata.py`: creates LibriMix-style mixture metadata.
- `scripts/create_librimix_from_metadata.py`: renders source, noise, and mixture waveforms from metadata.

## Citation

If you use this repository, cite the original LibriMix work and the DEMAND dataset.

```bibtex
@article{cosentino2020librimix,
  title={LibriMix: An Open-Source Dataset for Generalizable Speech Separation},
  author={Cosentino, Joris and Pariente, Manuel and Cornell, Samuele and Deleforge, Antoine and Vincent, Emmanuel},
  journal={arXiv preprint arXiv:2005.11262},
  year={2020}
}

@inproceedings{thiemann2013demand,
  title={The Diverse Environments Multi-channel Acoustic Noise Database (DEMAND): A database of multichannel environmental noise recordings},
  author={Thiemann, Joachim and Ito, Nobutaka and Vincent, Emmanuel},
  booktitle={Proceedings of Meetings on Acoustics},
  year={2013}
}
```

## License

This repository retains the upstream license from the LibriMix codebase. See `LICENSE`.
