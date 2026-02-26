"""Top-level cogs package.

Keep this module side-effect free.
Do not import handlers here, because infra modules import feature constants
from `cogs.<feature>.constants`, and eager handler imports can create
startup-time import cycles.
"""
