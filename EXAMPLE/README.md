# EXAMPLE / 示例说明

本目录提供了一个用于体验 PolymCrystIndex 工作流的示例数据集。  
This directory provides an example dataset for trying the PolymCrystIndex workflow.

## 数据说明 / Dataset Information

- 数据来源：上海光源 SSRF 16B 线站  
  Source: SSRF 16B beamline
- 样品：HDPE 纤维样品  
  Sample: HDPE fiber sample
- 标样：Y2O3，使用 `pyFAI-calib2` 校准后得到 `Y2O3.poni`  
  Standard: Y2O3, calibrated with `pyFAI-calib2` to generate `Y2O3.poni`
- 图像经过空气散射背景校正  
  Images were corrected for air-scattering background

## 使用提示 / Usage Notes

- 可使用本目录中的示例文件练习导入、峰提取、积分和指标化流程。  
  You can use the files in this directory to practice import, peak extraction, integration, and indexing.
- 进行指标化时，建议先将体积参数调小，推荐值约为 `50`。  
  For indexing, it is recommended to start with a smaller volume parameter, around `50`.
- `c` 长度建议先在 `2-4` 范围内尝试。  
  It is recommended to first try a `c` length range of `2-4`.

## 说明 / Notes

- 本目录用于示例演示与流程熟悉。  
  This directory is intended for demonstration and workflow familiarization.
- 后续我们会补充更完整的视频或操作说明。  
  More detailed video or step-by-step guidance will be added in the future.
