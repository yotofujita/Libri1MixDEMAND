#!/bin/bash
set -eu  # Exit on error

storage_dir=$1
librispeech_dir=$storage_dir/LibriSpeech
demand_dir=$storage_dir/demand_noise
librimix_outdir=$storage_dir/Libri1MixDemand

function LibriSpeech_clean100() {
	if ! test -e $librispeech_dir/train-clean-100; then
		echo "Download LibriSpeech/train-clean-100 into $storage_dir"
		# If downloading stalls for more than 20s, relaunch from previous state.
		wget -c --tries=0 --read-timeout=20 http://www.openslr.org/resources/12/train-clean-100.tar.gz -P $storage_dir
		tar -xzf $storage_dir/train-clean-100.tar.gz -C $storage_dir
		rm -rf $storage_dir/train-clean-100.tar.gz
	fi
}

function demand_noise() {
	if ! test -e $demand_dir; then
		echo "Creating DEMAND noise splits in $storage_dir"
		# Create DEMAND splits using our script
		python scripts/create_demand_splits.py --demand_dir $storage_dir/DEMAND --output_dir $demand_dir
	fi
}

LibriSpeech_clean100 &
demand_noise &

wait

# Path to python
python_path=python

# If you wish to rerun this script in the future please comment this line out.
$python_path scripts/augment_train_noise.py --wham_dir $demand_dir --orig_num_samples 449

$python_path scripts/create_librimix_metadata.py --librispeech_dir $librispeech_dir \
	--librispeech_md_dir metadata/LibriSpeech/for_demand/ \
	--wham_dir $demand_dir \
	--wham_md_dir metadata/Demand_noise/ \
	--metadata_outdir metadata/Libri1MixDemand \
	--n_src 1

metadata_dir=metadata/Libri1MixDemand
$python_path scripts/create_librimix_from_metadata.py --librispeech_dir $librispeech_dir \
	--wham_dir $demand_dir \
	--metadata_dir $metadata_dir \
	--librimix_outdir $librimix_outdir \
	--n_src 1 \
	--freqs 16k \
	--modes min \
	--types mix_single
