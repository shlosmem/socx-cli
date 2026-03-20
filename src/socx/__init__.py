"""Aggregate public SoCX APIs to provide a concise import surface."""

__all__ = (
    # core
    "enums",
    "__author__",
    "__project__",
    "__version__",
    "__appname__",
    "__directory__",
    "FuncType",
    "Decorator",
    "GroupType",
    "CommandType",
    "AnyCallable",
    "GroupDecorator",
    "CommandDecorator",
    "USER_LOG_DIR",
    "USER_DATA_DIR",
    "USER_CACHE_DIR",
    "USER_STATE_DIR",
    "USER_CONFIG_DIR",
    "USER_RUNTIME_DIR",
    "USER_LOG_FILE",
    "USER_CONFIG_FILE",
    "LOCAL_CONFIG_FILE",
    "USER_LOG_FILENAME",
    "USER_CONFIG_FILENAME",
    "LOCAL_CONFIG_FILE",
    "LOCAL_CONFIG_FILENAME",
    "PROJECT_ROOT_DIR",
    "PROJECT_ROOT_CONFIG",
    "APP_ROOT_DIR",
    "APP_STATIC_DIR",
    "APP_CONFIG_DIR",
    "APP_TEMPLATES_DIR",
    "APP_CONFIG_FILE",
    "APP_CONFIG_FILENAME",
    "Runner",
    "Encoder",
    "Manager",
    "Serializer",
    "wrap",
    "deduplicate",
    # I/O
    "DEFAULT_LEVEL",
    "DEFAULT_FORMAT",
    "DEFAULT_HANDLERS",
    "DEFAULT_TIME_FORMAT",
    "Level",
    "log_it",
    "logger",
    "console",
    "get_level",
    "set_level",
    "get_logger",
    "get_console",
    "print_outputs",
    "print_with_pager",
    "print_command_outputs",
    "add_filter",
    "remove_filter",
    "add_handler",
    "get_handler",
    "has_handlers",
    "is_enabled_for",
    "remove_handler",
    "get_handler_names",
    # Git
    "get_ssh_config",
    "get_ssh_key_path",
    "get_repo",
    "is_repo",
    "get_repo_dir",
    "get_repo_name",
    "get_ref_name",
    "get_short_ref",
    "get_author_date",
    "get_author_name",
    "get_commit_hash",
    "get_commit_message",
    "get_ahead_behind",
    "format_ahead_behind",
    "is_local_branch",
    "iter_repositories",
    "find_repositories",
    # CLI
    "cli",
    # util
    "join_decorators",
    # config
    "schema",
    "settings",
    "Script",
    "NewPath",
    "FilePath",
    "SocketPath",
    "DirectoryPath",
    "PluginModel",
    "Formatter",
    "TreeFormatter",
    "Converter",
    "ShConverter",
    "PathConverter",
    "CompileConverter",
    "ImportConverter",
    "SymbolConverter",
    "add_converters",
    "get_converters",
    "SettingsEncoder",
    "ModuleSerializer",
    "SettingsSerializer",
    "Validator",
    "ValidationError",
    "validate_all",
    "SETTINGS_DEFAULTS",
    "Settings",
    "settings",
    # Mixins
    "UIDMixin",
    "PtrMixin",
    "ProxyMixin",
    # Patterns
    "Node",
    "Visitor",
    "Traversal",
    "Singleton",
    "StructureProxy",
    "ByLevelTraversal",
    "TopDownTraversal",
    "BottomUpTraversal",
    # Regression
    "Test",
    "TestBase",
    "Regression",
    "TestStatus",
    "TestResult",
    "RegressionProgress",
)

from socx.core import enums as enums
from socx.core import schema as schema
from socx.core import Script as Script
from socx.core import NewPath as NewPath
from socx.core import FilePath as FilePath
from socx.core import SocketPath as SocketPath
from socx.core import DirectoryPath as DirectoryPath
from socx.core import PluginModel as PluginModel
from socx.core import __author__ as __author__
from socx.core import __project__ as __project__
from socx.core import __version__ as __version__
from socx.core import __appname__ as __appname__
from socx.core import __directory__ as __directory__
from socx.core import USER_LOG_DIR as USER_LOG_DIR
from socx.core import USER_DATA_DIR as USER_DATA_DIR
from socx.core import USER_CACHE_DIR as USER_CACHE_DIR
from socx.core import USER_STATE_DIR as USER_STATE_DIR
from socx.core import USER_CONFIG_DIR as USER_CONFIG_DIR
from socx.core import USER_RUNTIME_DIR as USER_RUNTIME_DIR
from socx.core import USER_LOG_FILE as USER_LOG_FILE
from socx.core import USER_CONFIG_FILE as USER_CONFIG_FILE
from socx.core import PROJECT_ROOT_DIR as PROJECT_ROOT_DIR
from socx.core import PROJECT_ROOT_CONFIG as PROJECT_ROOT_CONFIG
from socx.core import LOCAL_CONFIG_FILE as LOCAL_CONFIG_FILE
from socx.core import USER_LOG_FILENAME as USER_LOG_FILENAME
from socx.core import USER_CONFIG_FILENAME as USER_CONFIG_FILENAME
from socx.core import LOCAL_CONFIG_FILENAME as LOCAL_CONFIG_FILENAME
from socx.core import APP_ROOT_DIR as APP_ROOT_DIR
from socx.core import APP_STATIC_DIR as APP_STATIC_DIR
from socx.core import APP_CONFIG_DIR as APP_CONFIG_DIR
from socx.core import APP_TEMPLATES_DIR as APP_TEMPLATES_DIR
from socx.core import APP_CONFIG_FILE as APP_CONFIG_FILE
from socx.core import APP_CONFIG_FILENAME as APP_CONFIG_FILENAME
from socx.core import Runner as Runner
from socx.core import Encoder as Encoder
from socx.core import Manager as Manager
from socx.core import Serializer as Serializer
from socx.core import wrap as wrap
from socx.core import deduplicate as deduplicate

from socx.utils import join_decorators as join_decorators

from socx.io import Level as Level
from socx.io import log_it as log_it
from socx.io import logger as logger
from socx.io import console as console
from socx.io import get_level as get_level
from socx.io import set_level as set_level
from socx.io import get_logger as get_logger
from socx.io import get_console as get_console
from socx.io import print_outputs as print_outputs
from socx.io import print_with_pager as print_with_pager
from socx.io import print_command_outputs as print_command_outputs
from socx.io import add_filter as add_filter
from socx.io import remove_filter as remove_filter
from socx.io import add_handler as add_handler
from socx.io import get_handler as get_handler
from socx.io import has_handlers as has_handlers
from socx.io import is_enabled_for as is_enabled_for
from socx.io import remove_handler as remove_handler
from socx.io import get_handler_names as get_handler_names

from socx.git import get_ssh_config as get_ssh_config
from socx.git import get_ssh_key_path as get_ssh_key_path
from socx.git import get_repo as get_repo
from socx.git import get_repo_dir as get_repo_dir
from socx.git import get_repo_name as get_repo_name
from socx.git import get_ref_name as get_ref_name
from socx.git import get_short_ref as get_short_ref
from socx.git import get_author_date as get_author_date
from socx.git import get_author_name as get_author_name
from socx.git import get_commit_hash as get_commit_hash
from socx.git import get_commit_message as get_commit_message
from socx.git import get_ahead_behind as get_ahead_behind
from socx.git import format_ahead_behind as format_ahead_behind
from socx.git import is_repo as is_repo
from socx.git import is_local_branch as is_local_branch
from socx.git import iter_repositories as iter_repositories
from socx.git import find_repositories as find_repositories

from socx.config import Settings as Settings
from socx.config import SETTINGS_DEFAULTS as SETTINGS_DEFAULTS
from socx.config import settings as settings
from socx.config import get_settings as get_settings
from socx.config import (
    get_local_config_files as get_local_config_files,
)
from socx.config import Validator as Validator
from socx.config import Formatter as Formatter
from socx.config import Converter as Converter
from socx.config import ShConverter as ShConverter
from socx.config import PathConverter as PathConverter
from socx.config import SymbolConverter as SymbolConverter
from socx.config import ImportConverter as ImportConverter
from socx.config import CompileConverter as CompileConverter
from socx.config import add_converters as add_converters
from socx.config import get_converters as get_converters
from socx.config import TreeFormatter as TreeFormatter
from socx.config import SettingsEncoder as SettingsEncoder
from socx.config import ModuleSerializer as ModuleSerializer
from socx.config import SettingsSerializer as SettingsSerializer
from socx.config import ValidationError as ValidationError
from socx.config import validate_all as validate_all

from socx.patterns import Node as Node
from socx.patterns import Visitor as Visitor
from socx.patterns import Traversal as Traversal
from socx.patterns import StructureProxy as StructureProxy
from socx.patterns import TopDownTraversal as TopDownTraversal
from socx.patterns import BottomUpTraversal as BottomUpTraversal
from socx.patterns import ByLevelTraversal as ByLevelTraversal
from socx.patterns import UIDMixin as UIDMixin
from socx.patterns import PtrMixin as PtrMixin
from socx.patterns import Singleton as Singleton
from socx.patterns import ProxyMixin as ProxyMixin

from socx.regression import Test as Test
from socx.regression import TestBase as TestBase
from socx.regression import Regression as Regression
from socx.regression import TestStatus as TestStatus
from socx.regression import TestResult as TestResult
from socx.regression import RegressionProgress as RegressionProgress

from socx.cli import FuncType as FuncType
from socx.cli import Decorator as Decorator
from socx.cli import GroupType as GroupType
from socx.cli import CommandType as CommandType
from socx.cli import AnyCallable as AnyCallable
from socx.cli import GroupDecorator as GroupDecorator
from socx.cli import CommandDecorator as CommandDecorator
from socx.cli import opts as opts
from socx.cli import group as group
from socx.cli import command as command
from socx.cli import color as color
from socx.cli import debug as debug
from socx.cli import configure as configure
from socx.cli import verbosity as verbosity
from socx.cli import cli as cli
