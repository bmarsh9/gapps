"""
LLM Provider abstraction for Claude (Anthropic) and OpenAI integrations.
Supports both direct API calls and MCP (Model Context Protocol) server mode.
"""

import json
import logging
import requests

logger = logging.getLogger(__name__)


class LLMProvider:
    """Base class for LLM providers."""

    def __init__(self, api_key=None, model=None, max_tokens=2048):
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens

    def chat(self, messages, system_prompt=None):
        raise NotImplementedError

    def is_configured(self):
        return bool(self.api_key)


class ClaudeProvider(LLMProvider):
    """Anthropic Claude API integration."""

    API_URL = "https://api.anthropic.com/v1/messages"
    DEFAULT_MODEL = "claude-sonnet-4-20250514"

    def __init__(self, api_key=None, model=None, max_tokens=2048):
        super().__init__(api_key, model or self.DEFAULT_MODEL, max_tokens)

    def chat(self, messages, system_prompt=None):
        if not self.is_configured():
            return {"error": "Claude API key not configured"}

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        # Convert messages to Anthropic format
        anthropic_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            if role == "system":
                continue  # system prompt handled separately
            anthropic_messages.append(
                {"role": role, "content": msg.get("content", "")}
            )

        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": anthropic_messages,
        }

        if system_prompt:
            payload["system"] = system_prompt

        try:
            response = requests.post(
                self.API_URL, headers=headers, json=payload, timeout=60
            )
            response.raise_for_status()
            data = response.json()
            content = data.get("content", [{}])
            text = content[0].get("text", "") if content else ""
            return {
                "message": text,
                "usage": data.get("usage", {}),
                "model": data.get("model", self.model),
            }
        except requests.exceptions.Timeout:
            logger.error("Claude API request timed out")
            return {"error": "Request timed out"}
        except requests.exceptions.RequestException as e:
            logger.error(f"Claude API error: {e}")
            return {"error": str(e)}


class OpenAIProvider(LLMProvider):
    """OpenAI API integration."""

    API_URL = "https://api.openai.com/v1/chat/completions"
    DEFAULT_MODEL = "gpt-4o"

    def __init__(self, api_key=None, model=None, max_tokens=2048):
        super().__init__(api_key, model or self.DEFAULT_MODEL, max_tokens)

    def chat(self, messages, system_prompt=None):
        if not self.is_configured():
            return {"error": "OpenAI API key not configured"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        openai_messages = []
        if system_prompt:
            openai_messages.append({"role": "system", "content": system_prompt})

        for msg in messages:
            openai_messages.append(
                {"role": msg.get("role", "user"), "content": msg.get("content", "")}
            )

        payload = {
            "model": self.model,
            "messages": openai_messages,
            "max_tokens": self.max_tokens,
        }

        try:
            response = requests.post(
                self.API_URL, headers=headers, json=payload, timeout=60
            )
            response.raise_for_status()
            data = response.json()
            choices = data.get("choices", [{}])
            text = (
                choices[0].get("message", {}).get("content", "") if choices else ""
            )
            return {
                "message": text,
                "usage": data.get("usage", {}),
                "model": data.get("model", self.model),
            }
        except requests.exceptions.Timeout:
            logger.error("OpenAI API request timed out")
            return {"error": "Request timed out"}
        except requests.exceptions.RequestException as e:
            logger.error(f"OpenAI API error: {e}")
            return {"error": str(e)}


class MCPServer:
    """
    Model Context Protocol (MCP) server integration.
    Acts as a bridge between the compliance platform and LLM providers,
    providing structured tool access to compliance data.
    """

    def __init__(self, base_url=None, auth_token=None):
        self.base_url = base_url or "http://localhost:3001"
        self.auth_token = auth_token

    def is_configured(self):
        return bool(self.base_url)

    def _headers(self):
        h = {"Content-Type": "application/json"}
        if self.auth_token:
            h["Authorization"] = f"Bearer {self.auth_token}"
        return h

    def list_tools(self):
        """List available MCP tools."""
        try:
            response = requests.post(
                f"{self.base_url}/mcp/v1/tools/list",
                headers=self._headers(),
                json={},
                timeout=10,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"MCP tools/list error: {e}")
            return {"tools": []}

    def call_tool(self, tool_name, arguments=None):
        """Call an MCP tool."""
        try:
            response = requests.post(
                f"{self.base_url}/mcp/v1/tools/call",
                headers=self._headers(),
                json={"name": tool_name, "arguments": arguments or {}},
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"MCP tools/call error: {e}")
            return {"error": str(e)}


def get_llm_provider(config):
    """
    Factory function to get the configured LLM provider.
    Reads from app config / ConfigStore settings.
    """
    provider_name = config.get("LLM_PROVIDER", config.get("LLM_NAME", ""))
    if not provider_name:
        provider_name = ""

    provider_name = provider_name.lower().strip()

    if provider_name in ("claude", "anthropic"):
        return ClaudeProvider(
            api_key=config.get("ANTHROPIC_API_KEY") or config.get("LLM_TOKEN"),
            model=config.get("ANTHROPIC_MODEL"),
            max_tokens=int(config.get("LLM_MAX_TOKENS", 2048)),
        )
    elif provider_name in ("openai", "gpt"):
        return OpenAIProvider(
            api_key=config.get("OPENAI_API_KEY") or config.get("LLM_TOKEN"),
            model=config.get("OPENAI_MODEL"),
            max_tokens=int(config.get("LLM_MAX_TOKENS", 2048)),
        )
    else:
        # Default: return Claude if ANTHROPIC_API_KEY is set, else OpenAI
        if config.get("ANTHROPIC_API_KEY"):
            return ClaudeProvider(
                api_key=config.get("ANTHROPIC_API_KEY"),
                model=config.get("ANTHROPIC_MODEL"),
            )
        elif config.get("OPENAI_API_KEY"):
            return OpenAIProvider(
                api_key=config.get("OPENAI_API_KEY"),
                model=config.get("OPENAI_MODEL"),
            )
        return ClaudeProvider()  # unconfigured


def get_mcp_server(config):
    """Factory function to get the configured MCP server."""
    return MCPServer(
        base_url=config.get("MCP_SERVER_URL"),
        auth_token=config.get("MCP_SERVER_TOKEN"),
    )


# Compliance-specific system prompt
COMPLIANCE_SYSTEM_PROMPT = """You are a compliance assistant for a GRC (Governance, Risk, and Compliance) platform powered by Masri Digital. You help users with:

1. Understanding compliance frameworks (FTC Safeguards, SOC 2, HIPAA, NIST, ISO 27001, PCI DSS, CMMC, etc.)
2. Implementing security controls and writing policies
3. Risk assessment and management
4. Vendor risk management
5. Audit preparation and evidence collection
6. Industry-specific compliance guidance (mortgage lenders, CPAs, tax preparers, auto dealers, etc.)

Always provide actionable, specific guidance. Reference the relevant framework control IDs when applicable. Be precise and professional."""
