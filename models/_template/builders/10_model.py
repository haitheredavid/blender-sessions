# First builder step. build_all.py has already cleared Model and Work (never Control).
# Build GN groups + modifiers that read CTL_* objects from Control; don't bake.
# Split into more NN_*.py steps as the model grows (20_details.py, 30_materials.py, ...).
from kit import materials, mesh, scene  # noqa: F401
