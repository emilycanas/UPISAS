#!/bin/bash
export PYTHONPATH=$PYTHONPATH:$(pwd)
python3 experiment-runner/experiment-runner/ UPISAS/experiment_runner_configs/RAMSES_experiment.py
