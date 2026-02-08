"""
Multi-Model LLM Manager for Backtest Crew

Provides task-specific model selection and fallback chain logic for robust LLM calls.
"""

import os
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Callable, Any
import time
from dotenv import load_dotenv

load_dotenv()


class TaskType(Enum):
    """Types of tasks with different model requirements."""
    DECOMPOSITION = "decomposition"      # Parse user query into structured tasks
    CODE_GENERATION = "code_generation"  # Generate trading strategy code
    ERROR_FIXING = "error_fixing"        # Fix code errors
    VALIDATION = "validation"            # Validate code structure
    ASSEMBLY = "assembly"                # Assemble code pieces


@dataclass
class ModelConfig:
    """Configuration for a single model."""
    provider: str  # "openai", "anthropic", "google", "groq"
    model_name: str
    confidence_threshold: float  # Minimum confidence to accept response
    max_tokens: int = 4096
    temperature: float = 0.1
    cost_per_1k_tokens: float = 0.0  # For cost tracking


# Task-specific model configurations
# Note: CrewAI agents use OpenAI directly (no litellm needed)
# Groq is available for direct API calls in verification.py
TASK_MODEL_CONFIGS = {
    TaskType.DECOMPOSITION: [
        ModelConfig("openai", "gpt-4.1-mini", 0.8, max_tokens=2048, temperature=0.0, cost_per_1k_tokens=0.00015),
        ModelConfig("openai", "gpt-4.1", 0.95, max_tokens=2048, temperature=0.0, cost_per_1k_tokens=0.002),
    ],
    TaskType.CODE_GENERATION: [
        ModelConfig("openai", "gpt-4o", 0.95, max_tokens=16384, temperature=0.1, cost_per_1k_tokens=0.005),
        ModelConfig("openai", "gpt-4o-mini", 0.9, max_tokens=16384, temperature=0.1, cost_per_1k_tokens=0.00015),
    ],
    TaskType.ERROR_FIXING: [
        ModelConfig("openai", "gpt-4o", 0.9, max_tokens=16384, temperature=0.0, cost_per_1k_tokens=0.005),
        ModelConfig("openai", "gpt-4.1", 0.85, max_tokens=8192, temperature=0.0, cost_per_1k_tokens=0.002),
        ModelConfig("openai", "gpt-4.1-mini", 0.75, max_tokens=4096, temperature=0.0, cost_per_1k_tokens=0.00015),
    ],
    TaskType.VALIDATION: [
        ModelConfig("openai", "gpt-4.1-mini", 0.8, max_tokens=2048, temperature=0.0, cost_per_1k_tokens=0.00015),
        ModelConfig("openai", "gpt-4.1", 0.95, max_tokens=2048, temperature=0.0, cost_per_1k_tokens=0.002),
    ],
    TaskType.ASSEMBLY: [
        ModelConfig("openai", "gpt-4o-mini", 0.95, max_tokens=16384, temperature=0.0, cost_per_1k_tokens=0.00015),
        ModelConfig("openai", "gpt-4o", 0.95, max_tokens=16384, temperature=0.0, cost_per_1k_tokens=0.005),
    ],
}


class LLMClient:
    """Unified client for multiple LLM providers (OpenAI + Groq)."""
    
    def __init__(self):
        self._openai_client = None
        self._groq_client = None
        
    @property
    def openai(self):
        if self._openai_client is None:
            from openai import OpenAI
            self._openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        return self._openai_client
    
    @property
    def groq(self):
        if self._groq_client is None:
            try:
                from groq import Groq
                self._groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
            except ImportError:
                raise ImportError("groq package not installed. Run: pip install groq")
        return self._groq_client
    
    def call(self, config: ModelConfig, messages: list[dict], system_prompt: str = None) -> tuple[str, dict]:
        """
        Call an LLM with the given configuration.
        
        Returns:
            tuple: (response_text, metadata_dict)
        """
        start_time = time.time()
        
        if config.provider == "openai":
            return self._call_openai(config, messages, system_prompt, start_time)
        elif config.provider == "groq":
            return self._call_groq(config, messages, system_prompt, start_time)
        else:
            raise ValueError(f"Unknown provider: {config.provider}")
    
    def _call_openai(self, config: ModelConfig, messages: list[dict], system_prompt: str, start_time: float) -> tuple[str, dict]:
        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)
        
        response = self.openai.chat.completions.create(
            model=config.model_name,
            messages=full_messages,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
        )
        
        duration = time.time() - start_time
        usage = response.usage
        
        return response.choices[0].message.content, {
            "provider": "openai",
            "model": config.model_name,
            "input_tokens": usage.prompt_tokens,
            "output_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
            "duration_seconds": duration,
            "estimated_cost": (usage.total_tokens / 1000) * config.cost_per_1k_tokens,
        }
    
    def _call_groq(self, config: ModelConfig, messages: list[dict], system_prompt: str, start_time: float) -> tuple[str, dict]:
        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)
        
        response = self.groq.chat.completions.create(
            model=config.model_name,
            messages=full_messages,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
        )
        
        duration = time.time() - start_time
        usage = response.usage
        
        return response.choices[0].message.content, {
            "provider": "groq",
            "model": config.model_name,
            "input_tokens": usage.prompt_tokens,
            "output_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
            "duration_seconds": duration,
            "estimated_cost": 0.0,  # Groq is free tier
        }


class MultiModelManager:
    """
    Manages multiple LLM models with task-specific selection and fallback logic.
    """
    
    def __init__(self, verbose: bool = True):
        self.client = LLMClient()
        self.verbose = verbose
        self.total_cost = 0.0
        self.total_tokens = 0
        self.call_history = []
    
    def generate(
        self,
        task_type: TaskType,
        prompt: str,
        system_prompt: str = None,
        validate_fn: Callable[[str], tuple[bool, float]] = None,
    ) -> tuple[str, dict]:
        """
        Generate a response using task-appropriate models with fallback.
        
        Args:
            task_type: Type of task to determine which models to use
            prompt: User prompt
            system_prompt: Optional system prompt
            validate_fn: Optional function to validate response. 
                         Returns (is_valid, confidence_score)
        
        Returns:
            tuple: (response_text, metadata)
        """
        models = TASK_MODEL_CONFIGS.get(task_type, TASK_MODEL_CONFIGS[TaskType.CODE_GENERATION])
        
        messages = [{"role": "user", "content": prompt}]
        last_error = None
        all_attempts = []
        
        for i, config in enumerate(models):
            try:
                if self.verbose:
                    print(f"\n[LLM] Attempting {config.provider}/{config.model_name} for {task_type.value}...")
                
                response, metadata = self.client.call(config, messages, system_prompt)
                metadata["attempt"] = i + 1
                metadata["task_type"] = task_type.value
                
                # Validate response if validation function provided
                if validate_fn:
                    is_valid, confidence = validate_fn(response)
                    metadata["validated"] = is_valid
                    metadata["confidence"] = confidence
                    
                    if is_valid and confidence >= config.confidence_threshold:
                        if self.verbose:
                            print(f"[LLM] ✓ Success with {config.model_name} (confidence: {confidence:.2f})")
                        self._record_usage(metadata)
                        return response, metadata
                    elif self.verbose:
                        print(f"[LLM] ✗ Validation failed or low confidence ({confidence:.2f} < {config.confidence_threshold})")
                else:
                    # No validation, accept response
                    if self.verbose:
                        print(f"[LLM] ✓ Response received from {config.model_name}")
                    self._record_usage(metadata)
                    return response, metadata
                    
                all_attempts.append((response, metadata))
                
            except Exception as e:
                last_error = e
                if self.verbose:
                    print(f"[LLM] ✗ Error with {config.model_name}: {str(e)}")
                continue
        
        # All models failed - return best attempt or raise error
        if all_attempts:
            # Return the response with highest confidence
            best = max(all_attempts, key=lambda x: x[1].get("confidence", 0))
            if self.verbose:
                print(f"[LLM] ⚠ Returning best attempt despite low confidence")
            self._record_usage(best[1])
            return best
        
        raise RuntimeError(f"All models failed for {task_type.value}. Last error: {last_error}")
    
    def _record_usage(self, metadata: dict):
        """Record usage statistics."""
        self.total_cost += metadata.get("estimated_cost", 0)
        self.total_tokens += metadata.get("total_tokens", 0)
        self.call_history.append(metadata)
    
    def get_stats(self) -> dict:
        """Get usage statistics."""
        return {
            "total_cost": self.total_cost,
            "total_tokens": self.total_tokens,
            "total_calls": len(self.call_history),
            "calls_by_model": self._group_by_model(),
        }
    
    def _group_by_model(self) -> dict:
        """Group call history by model."""
        by_model = {}
        for call in self.call_history:
            model = f"{call['provider']}/{call['model']}"
            if model not in by_model:
                by_model[model] = {"calls": 0, "tokens": 0, "cost": 0}
            by_model[model]["calls"] += 1
            by_model[model]["tokens"] += call.get("total_tokens", 0)
            by_model[model]["cost"] += call.get("estimated_cost", 0)
        return by_model


# CrewAI LLM wrapper for easy integration
def get_crew_llm(task_type: TaskType):
    """
    Get a CrewAI-compatible LLM instance for a specific task type.
    
    Returns the primary model for the task type.
    """
    from crewai import LLM
    
    configs = TASK_MODEL_CONFIGS.get(task_type, TASK_MODEL_CONFIGS[TaskType.CODE_GENERATION])
    primary = configs[0]
    
    if primary.provider == "openai":
        return LLM(
            model=primary.model_name,
            api_key=os.getenv("OPENAI_API_KEY"),
            temperature=primary.temperature,
        )
    elif primary.provider == "groq":
        return LLM(
            model=f"groq/{primary.model_name}",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=primary.temperature,
        )
    else:
        raise ValueError(f"Unknown provider: {primary.provider}")


# Singleton instance for easy access
_manager_instance = None

def get_manager(verbose: bool = True) -> MultiModelManager:
    """Get the singleton MultiModelManager instance."""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = MultiModelManager(verbose=verbose)
    return _manager_instance


# Convenience function for direct LLM calls with fallback
def generate_with_fallback(
    task_type: TaskType,
    prompt: str,
    system_prompt: str = None,
) -> str:
    """
    Generate response using task-appropriate model with automatic fallback.
    
    This is a convenience wrapper around MultiModelManager.
    """
    manager = get_manager()
    response, _ = manager.generate(task_type, prompt, system_prompt)
    return response
