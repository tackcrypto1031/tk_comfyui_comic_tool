"""ComfyUI custom nodes for batch comic generation."""
from .nodes.batch_generator import ComicBatchGenerator
from .nodes.page_composer import ComicPageComposer
from .nodes.sampler_override import ComicSamplerOverride
from .nodes.script_loader import ComicScriptLoader

NODE_CLASS_MAPPINGS = {
    "ComicScriptLoader": ComicScriptLoader,
    "ComicSamplerOverride": ComicSamplerOverride,
    "ComicBatchGenerator": ComicBatchGenerator,
    "ComicPageComposer": ComicPageComposer,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ComicScriptLoader": "Comic Script Loader",
    "ComicSamplerOverride": "Comic Sampler Override (experimental)",
    "ComicBatchGenerator": "Comic Batch Generator",
    "ComicPageComposer": "Comic Page Composer",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
