"""
Skills MCP Server

A Model Context Protocol server for discovering, loading, and executing Agent Skills.
Based on the Agent Skills specification: https://agentskills.io/specification
"""

from .server import mcp, main

__version__ = "0.2.0"
__all__ = ["mcp", "main"]
