"""
title: LiteLLM Manifold Pipeline
author: open-webui
date: 2024-05-30
version: 1.0.1
license: MIT
description: A manifold pipeline that uses LiteLLM.
"""

from typing import List, Union, Generator, Iterator
from schemas import OpenAIChatMessage
from pydantic import BaseModel
import requests
import os
from security import safe_requests


class Pipeline:

    class Valves(BaseModel):
        LITELLM_BASE_URL: str = ""
        LITELLM_API_KEY: str = ""
        LITELLM_PIPELINE_DEBUG: bool = False

    def __init__(self):
        # You can also set the pipelines that are available in this pipeline.
        # Set manifold to True if you want to use this pipeline as a manifold.
        # Manifold pipelines can have multiple pipelines.
        self.type = "manifold"

        # Optionally, you can set the id and name of the pipeline.
        # Best practice is to not specify the id so that it can be automatically inferred from the filename, so that users can install multiple versions of the same pipeline.
        # The identifier must be unique across all pipelines.
        # The identifier must be an alphanumeric string that can include underscores or hyphens. It cannot contain spaces, special characters, slashes, or backslashes.
        # self.id = "litellm_manifold"

        # Optionally, you can set the name of the manifold pipeline.
        self.name = "LiteLLM: "

        # Initialize rate limits
        self.valves = self.Valves(
            **{
                "LITELLM_BASE_URL": os.getenv(
                    "LITELLM_BASE_URL", "http://localhost:4001"
                ),
                "LITELLM_API_KEY": os.getenv("LITELLM_API_KEY", "your-api-key-here"),
                "LITELLM_PIPELINE_DEBUG": os.getenv("LITELLM_PIPELINE_DEBUG", False),
            }
        )
        # Get models on initialization
        self.pipelines = self.get_litellm_models()
        pass

    async def on_startup(self):
        # This function is called when the server is started.
        print(f"on_startup:{__name__}")
        # Get models on startup
        self.pipelines = self.get_litellm_models()
        pass

    async def on_shutdown(self):
        # This function is called when the server is stopped.
        print(f"on_shutdown:{__name__}")
        pass

    async def on_valves_updated(self):
        # This function is called when the valves are updated.

        self.pipelines = self.get_litellm_models()
        pass

    def get_litellm_models(self):

        headers = {}
        if self.valves.LITELLM_API_KEY:
            headers["Authorization"] = f"Bearer {self.valves.LITELLM_API_KEY}"

        if self.valves.LITELLM_BASE_URL:
            try:
                r = safe_requests.get(
                    f"{self.valves.LITELLM_BASE_URL}/v1/models", headers=headers
                )
                models = r.json()
                return [
                    {
                        "id": model["id"],
                        "name": model["name"] if "name" in model else model["id"],
                    }
                    for model in models["data"]
                ]
            except Exception as e:
                print(f"Error fetching models from LiteLLM: {e}")
                return [
                    {
                        "id": "error",
                        "name": "Could not fetch models from LiteLLM, please update the URL in the valves.",
                    },
                ]
        else:
            print("LITELLM_BASE_URL not set. Please configure it in the valves.")
            return []

    def pipe(
        self, user_message: str, model_id: str, messages: List[dict], body: dict
    ) -> Union[str, Generator, Iterator]:
        if "user" in body:
            print("######################################")
            print(f'# User: {body["user"]["name"]} ({body["user"]["id"]})')
            print(f"# Message: {user_message}")
            print("######################################")

        headers = {}
        if self.valves.LITELLM_API_KEY:
            headers["Authorization"] = f"Bearer {self.valves.LITELLM_API_KEY}"

        try:
            payload = {**body, "model": model_id, "user": body["user"]["id"]}
            payload.pop("chat_id", None)
            payload.pop("user", None)
            payload.pop("title", None)

            r = requests.post(
                url=f"{self.valves.LITELLM_BASE_URL}/v1/chat/completions",
                json=payload,
                headers=headers,
                stream=True,
            )

            r.raise_for_status()

            if body["stream"]:
                return r.iter_lines()
            else:
                return r.json()
        except Exception as e:
            return f"Error: {e}"
