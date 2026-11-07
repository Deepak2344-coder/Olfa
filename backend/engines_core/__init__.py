"""Built-in engines shipped with the backend.

Modules in this package are discovered automatically by
:func:`backend.engine_registry.load_engines`. A module can expose engines in
either of two ways:

* a module level ``get_engines()`` function returning a list of engines, or
* concrete :class:`shared.base.Engine` subclasses defined in the module.
"""
