#!/bin/bash
# Slurm wrapper: sbatch run_room.sbatch [rooms]   (edit the partition / account lines for your cluster)
#SBATCH -J rgb_room
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH -t 04:00:00
#SBATCH -o rgb_room_%j.log
##SBATCH -p <partition>
##SBATCH -A <account>
cd "$SLURM_SUBMIT_DIR"
bash run_room.sh "${1:-room_079}"
