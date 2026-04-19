"""
Fiber Diffraction Indexing 版本信息。
"""

VERSION = "1.8.1"
RELEASE_DATE = "2026.02.28"
PROGRAM_NAME = "POLYCRYSTINDEX"


def get_version_string():
    """获取格式化的版本字符串。"""
    return f"{PROGRAM_NAME} VERSION {VERSION} RELEASE in {RELEASE_DATE}"


def get_citation():
    """获取引用信息。"""
    return """
-------------------------REFERENCE-------------------
This software utilizes the MINPACK library for nonlinear optimization.
Software base on following MINPACK references:

Jorge More, Burton Garbow, Kenneth Hillstrom,
User Guide for MINPACK-1,
Technical Report ANL-80-74,
Argonne National Laboratory, 1980.

Jorge More, Danny Sorenson, Burton Garbow, Kenneth Hillstream,
The MINPACK Project,
in Sources and Development of Mathematical Software,
edited by Wayne Cowell,
Prentice-Hall, 1984,
ISBN: 0-13-823501-5,
LC: QA76.95.S68.

Additionally, please CITE the following paper for this work:

Ma, T., Hu, W., Wang, D. & Liu, G. (2025).A global optimization approach 
to automated indexing of fiber diffraction patterns. J. Appl. Cryst. 58.
------------------------------------------------------------------
"""
