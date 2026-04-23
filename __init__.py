"""ComfyUI entry point for tk_comfyui_comic_tool.

ComfyUI loads `custom_nodes/<folder>/__init__.py` and reads
NODE_CLASS_MAPPINGS / NODE_DISPLAY_NAME_MAPPINGS from the top-level
module. Our actual implementation lives in the `tk_comfyui_batch_image`
sub-package; this file re-exports its public surface so the folder
name on disk can differ from the Python package name.
"""
from .tk_comfyui_batch_image import (
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
