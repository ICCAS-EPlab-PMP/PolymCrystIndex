[中文版](README.zh.md)

# EXAMPLE

This directory provides an example dataset for trying the PolymCrystIndex workflow.

## Dataset Information

- Source: SSRF 16B beamline
- Sample: HDPE fiber sample
- Standard: Y2O3, calibrated with `pyFAI-calib2` to generate `Y2O3.poni`
- Images were corrected for air-scattering background

## Usage Notes

- You can use the files in this directory to practice import, peak extraction, integration, and indexing.
- For indexing, it is recommended to start with a smaller volume parameter, around `50`.
- It is recommended to first try a `c` length range of `2-4`.

## Notes

- This directory is intended for demonstration and workflow familiarization.
- More detailed video or step-by-step guidance will be added in the future.
