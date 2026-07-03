#!/usr/bin/env python3
"""
Script to create train/dev/test splits for DEMAND dataset
to be compatible with LibriMix pipeline.

This script:
1. Reads all DEMAND noise files
2. Splits each file into segments
3. Creates train/dev/test splits with similar proportions to WHAM
4. Organizes files into tr/cv/tt directories like WHAM
"""

import os
import argparse
import soundfile as sf
import numpy as np
import random
from pathlib import Path
import shutil

# Set random seed for reproducibility
random.seed(42)
np.random.seed(42)

def parse_args():
    parser = argparse.ArgumentParser(description='Create DEMAND train/dev/test splits')
    parser.add_argument('--demand_dir', type=str, required=True,
                        help='Path to DEMAND dataset directory')
    parser.add_argument('--output_dir', type=str, required=True,
                        help='Path to output directory for splits')
    parser.add_argument('--segment_duration', type=float, default=8.0,
                        help='Duration of each segment in seconds (default: 8.0 for reasonable segments)')
    parser.add_argument('--overlap', type=float, default=0.0,
                        help='Overlap between segments in seconds (default: 0.0)')
    parser.add_argument('--train_ratio', type=float, default=0.714,
                        help='Ratio of files for training (default: 0.714 = 20k/28k to match WHAM)')
    parser.add_argument('--dev_ratio', type=float, default=0.179,
                        help='Ratio of files for development (default: 0.179 = 5k/28k to match WHAM)')
    parser.add_argument('--test_ratio', type=float, default=0.107,
                        help='Ratio of files for testing (default: 0.107 = 3k/28k to match WHAM)')
    return parser.parse_args()

def get_audio_duration(file_path):
    """Get duration of audio file in seconds"""
    try:
        info = sf.info(file_path)
        return info.duration
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return 0

def create_segments_from_file(input_file, output_dir, segment_duration, overlap, 
                             sample_rate=16000, noise_type=None, file_index=None):
    """
    Create segments from a single DEMAND file
    
    Args:
        input_file: Path to input DEMAND file
        output_dir: Directory to save segments
        segment_duration: Duration of each segment in seconds
        overlap: Overlap between segments in seconds
        sample_rate: Target sample rate
        noise_type: Type of noise (e.g., 'TCAR', 'DLIVING')
        file_index: Index of the file for naming
    
    Returns:
        List of created segment file paths
    """
    try:
        # Read audio file
        audio, sr = sf.read(input_file)
        
        # Convert to mono if stereo
        if len(audio.shape) > 1:
            audio = np.mean(audio, axis=1)
        
        # Resample if necessary
        if sr != sample_rate:
            # Simple resampling (for production, use scipy.signal.resample)
            ratio = sample_rate / sr
            new_length = int(len(audio) * ratio)
            audio = np.interp(np.linspace(0, len(audio), new_length), 
                             np.arange(len(audio)), audio)
        
        # Calculate segment parameters
        samples_per_segment = int(segment_duration * sample_rate)
        samples_overlap = int(overlap * sample_rate)
        samples_step = samples_per_segment - samples_overlap
        
        segments = []
        start_sample = 0
        
        while start_sample + samples_per_segment <= len(audio):
            # Extract segment
            segment = audio[start_sample:start_sample + samples_per_segment]
            
            # Create filename
            segment_filename = f"{noise_type}_{file_index:02d}_{start_sample//samples_per_segment:03d}.wav"
            segment_path = os.path.join(output_dir, segment_filename)
            
            # Save segment
            sf.write(segment_path, segment, sample_rate)
            segments.append(segment_path)
            
            start_sample += samples_step
        
        return segments
        
    except Exception as e:
        print(f"Error processing {input_file}: {e}")
        return []

def create_demand_splits(demand_dir, output_dir, segment_duration=8.0, overlap=0.0,
                        train_ratio=0.714, dev_ratio=0.179, test_ratio=0.107):
    """
    Create train/dev/test splits from DEMAND dataset
    
    Args:
        demand_dir: Path to DEMAND dataset
        output_dir: Path to output directory
        segment_duration: Duration of each segment in seconds (default: 8s for reasonable segments)
        overlap: Overlap between segments in seconds
        train_ratio: Ratio for training set (default: 0.714 = 20k/28k)
        dev_ratio: Ratio for development set (default: 0.179 = 5k/28k)
        test_ratio: Ratio for test set (default: 0.107 = 3k/28k)
    """
    
    # Validate ratios
    if abs(train_ratio + dev_ratio + test_ratio - 1.0) > 1e-6:
        raise ValueError("Ratios must sum to 1.0")
    
    # Create output directories
    tr_dir = os.path.join(output_dir, 'tr')
    cv_dir = os.path.join(output_dir, 'cv')
    tt_dir = os.path.join(output_dir, 'tt')
    
    for dir_path in [tr_dir, cv_dir, tt_dir]:
        os.makedirs(dir_path, exist_ok=True)
    
    # Get all DEMAND noise types
    demand_types = [d for d in os.listdir(demand_dir) 
                   if os.path.isdir(os.path.join(demand_dir, d))]
    demand_types.sort()
    
    print(f"Found {len(demand_types)} DEMAND noise types: {demand_types}")
    
    all_segments = []
    
    # Process each noise type - only use ch01.wav from each type
    for noise_type in demand_types:
        noise_dir = os.path.join(demand_dir, noise_type)
        ch01_file = os.path.join(noise_dir, 'ch01.wav')
        
        if not os.path.exists(ch01_file):
            print(f"Warning: {ch01_file} not found, skipping {noise_type}")
            continue
        
        print(f"Processing {noise_type}: ch01.wav")
        
        # Create segments from ch01.wav
        segments = create_segments_from_file(
            ch01_file, 
            tr_dir,  # Temporarily put all in tr_dir
            segment_duration, 
            overlap,
            noise_type=noise_type,
            file_index=0  # Always 0 since we only use ch01.wav
        )
        
        all_segments.extend(segments)
    
    print(f"Created {len(all_segments)} total segments")
    
    # Shuffle all segments
    random.shuffle(all_segments)
    
    # Split into train/dev/test
    total_segments = len(all_segments)
    train_end = int(total_segments * train_ratio)
    dev_end = train_end + int(total_segments * dev_ratio)
    
    train_segments = all_segments[:train_end]
    dev_segments = all_segments[train_end:dev_end]
    test_segments = all_segments[dev_end:]
    
    print(f"Split: {len(train_segments)} train, {len(dev_segments)} dev, {len(test_segments)} test")
    
    # Move files to appropriate directories
    for segment in dev_segments:
        filename = os.path.basename(segment)
        shutil.move(segment, os.path.join(cv_dir, filename))
    
    for segment in test_segments:
        filename = os.path.basename(segment)
        shutil.move(segment, os.path.join(tt_dir, filename))
    
    # Verify final counts
    final_train = len([f for f in os.listdir(tr_dir) if f.endswith('.wav')])
    final_dev = len([f for f in os.listdir(cv_dir) if f.endswith('.wav')])
    final_test = len([f for f in os.listdir(tt_dir) if f.endswith('.wav')])
    
    print(f"Final counts:")
    print(f"  Train (tr): {final_train} files")
    print(f"  Dev (cv): {final_dev} files")
    print(f"  Test (tt): {final_test} files")
    
    # Create summary file
    summary_path = os.path.join(output_dir, 'split_summary.txt')
    with open(summary_path, 'w') as f:
        f.write(f"DEMAND Dataset Split Summary\n")
        f.write(f"============================\n\n")
        f.write(f"Original DEMAND files: {len(demand_types)} noise types × 1 file (ch01.wav) = {len(demand_types)} files\n")
        f.write(f"Segment duration: {segment_duration} seconds\n")
        f.write(f"Segment overlap: {overlap} seconds\n")
        f.write(f"Total segments created: {total_segments}\n\n")
        f.write(f"Split ratios (matching WHAM proportions):\n")
        f.write(f"  Train: {train_ratio:.1%} ({final_train} files) - matches WHAM 20k\n")
        f.write(f"  Dev: {dev_ratio:.1%} ({final_dev} files) - matches WHAM 5k\n")
        f.write(f"  Test: {test_ratio:.1%} ({final_test} files) - matches WHAM 3k\n\n")
        f.write(f"Noise types included: {', '.join(demand_types)}\n")
        f.write(f"Note: Only ch01.wav from each noise type was used\n")
    
    print(f"Split summary saved to {summary_path}")

def main():
    args = parse_args()
    
    if not os.path.exists(args.demand_dir):
        raise ValueError(f"DEMAND directory not found: {args.demand_dir}")
    
    print(f"Creating DEMAND splits...")
    print(f"Input directory: {args.demand_dir}")
    print(f"Output directory: {args.output_dir}")
    print(f"Segment duration: {args.segment_duration}s")
    print(f"Overlap: {args.overlap}s")
    
    create_demand_splits(
        args.demand_dir,
        args.output_dir,
        args.segment_duration,
        args.overlap,
        args.train_ratio,
        args.dev_ratio,
        args.test_ratio
    )
    
    print("DEMAND splits created successfully!")

if __name__ == "__main__":
    main() 