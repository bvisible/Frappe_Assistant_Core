#!/usr/bin/env python3
# Frappe Assistant Core - Configuration Reader for SSE Bridge
# Copyright (C) 2025 Paul Clinton
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""
Configuration reader for SSE Bridge settings.
Reads configuration from Assistant Core Settings doctype with fallback to environment variables.
"""

import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def get_sse_bridge_config() -> Dict[str, Any]:
    """
    Get SSE bridge configuration from multiple sources:
    1. Assistant Core Settings doctype (if Frappe is available)
    2. Environment variables
    3. Sensible defaults

    Returns:
        Dict[str, Any]: Configuration dictionary
    """
    config = {
        # Default configuration
        "enabled": True,
        "host": "0.0.0.0",
        "port": 8080,
        "debug": False,
        "redis_config": None,  # Will be populated if Frappe is available
    }

    # Try to read from Frappe Assistant Core Settings first
    try:
        import frappe

        if frappe.db and frappe.db.get_value("DocType", "Assistant Core Settings"):
            settings = frappe.get_single("Assistant Core Settings")

            # Update config with settings from doctype
            if hasattr(settings, "sse_bridge_enabled"):
                config["enabled"] = bool(settings.sse_bridge_enabled)
            if hasattr(settings, "sse_bridge_host"):
                config["host"] = settings.sse_bridge_host or config["host"]
            if hasattr(settings, "sse_bridge_port"):
                config["port"] = int(settings.sse_bridge_port) if settings.sse_bridge_port else config["port"]
            if hasattr(settings, "sse_bridge_debug"):
                config["debug"] = bool(settings.sse_bridge_debug)

            logger.info("SSE bridge config loaded from Assistant Core Settings")

            # Get Redis configuration from Frappe
            config["redis_config"] = get_frappe_redis_config()

    except Exception as e:
        logger.info(
            f"Failed to read from Assistant Core Settings ({e}), using environment variables and defaults"
        )

    # Override with environment variables if available
    config["enabled"] = os.environ.get("SSE_BRIDGE_ENABLED", str(config["enabled"])).lower() in (
        "true",
        "1",
        "yes",
        "on",
    )
    config["host"] = os.environ.get("SSE_BRIDGE_HOST", os.environ.get("HOST", config["host"]))
    config["port"] = int(os.environ.get("SSE_BRIDGE_PORT", os.environ.get("PORT", config["port"])))
    config["debug"] = os.environ.get(
        "SSE_BRIDGE_DEBUG", os.environ.get("DEBUG", str(config["debug"]))
    ).lower() in ("true", "1", "yes", "on")

    return config


def get_frappe_redis_config() -> Optional[Dict[str, Any]]:
    """
    Get Redis configuration using Frappe's existing methods.

    Returns:
        Optional[Dict[str, Any]]: Redis configuration or None if not available
    """
    try:
        import frappe
        from frappe.utils.background_jobs import get_redis_conn

        # Try to get Redis connection to validate configuration
        redis_conn = get_redis_conn()

        # Extract connection info from Redis connection
        connection_pool = redis_conn.connection_pool

        redis_config = {
            "host": connection_pool.connection_kwargs.get("host", "localhost"),
            "port": connection_pool.connection_kwargs.get("port", 6379),
            "db": connection_pool.connection_kwargs.get("db", 0),
            "username": connection_pool.connection_kwargs.get("username"),
            "password": connection_pool.connection_kwargs.get("password"),
            "decode_responses": True,
        }

        # Remove None values
        redis_config = {k: v for k, v in redis_config.items() if v is not None}

        logger.info(
            f"Redis config from Frappe: {redis_config['host']}:{redis_config['port']}/{redis_config['db']}"
        )
        return redis_config

    except Exception as e:
        logger.info(f"Failed to get Frappe Redis config ({e}), will fall back to manual discovery")
        return None


def get_fallback_redis_config() -> Dict[str, Any]:
    """
    Get Redis configuration by reading bench config files directly.
    This is used when Frappe context is not available.

    Returns:
        Dict[str, Any]: Redis configuration
    """
    redis_config = {
        "host": "localhost",
        "port": 6379,
        "db": 0,
        "decode_responses": True,
    }

    try:
        # Try to find bench directory and read Redis config
        bench_dir = os.getcwd()
        config_paths = [
            os.path.join(bench_dir, "config", "redis_cache.conf"),
            os.path.join(bench_dir, "config", "redis_queue.conf"),
        ]

        for config_path in config_paths:
            try:
                with open(config_path) as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("port "):
                            redis_config["port"] = int(line.split()[1])
                        elif line.startswith("bind "):
                            bind_addr = line.split()[1]
                            if bind_addr != "127.0.0.1":
                                redis_config["host"] = bind_addr
                break  # Use first available config
            except FileNotFoundError:
                continue

        logger.info(
            f"Fallback Redis config: {redis_config['host']}:{redis_config['port']}/{redis_config['db']}"
        )

    except Exception as e:
        logger.warning(f"Failed to read bench Redis config ({e}), using defaults")

    return redis_config


def is_sse_bridge_enabled() -> bool:
    """
    Check if SSE bridge is enabled in settings.

    Returns:
        bool: True if SSE bridge is enabled
    """
    config = get_sse_bridge_config()
    return config.get("enabled", True)


def get_redis_config() -> Dict[str, Any]:
    """
    Get complete Redis configuration for SSE bridge.
    Tries Frappe's method first, then falls back to manual discovery.

    Returns:
        Dict[str, Any]: Redis configuration
    """
    config = get_sse_bridge_config()

    # Return Frappe Redis config if available
    if config.get("redis_config"):
        return config["redis_config"]

    # Fall back to manual discovery
    return get_fallback_redis_config()
