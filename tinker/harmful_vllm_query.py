import re
import logging
import base64
import os
import json
import time
import re
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI
import io
from PIL import Image
from typing import List, Dict, Any, Tuple

retry_delay = 30
openai_api_key = "token"
openai_api_base = "http://127.0.0.1:8615/v1" # modify
client = OpenAI(
    api_key=openai_api_key,
    base_url=openai_api_base,
)
models = client.models.list()
model = models.data[0].id

def extract_content(tag, text):
    """Extract tag content"""
    start_idx = text.find(tag)
    if start_idx == -1:
        return None
    
    content_after_tag = text[start_idx+len(tag):].strip()
    parts = content_after_tag.split()
    
    if tag == "#thescore:":
        try:
            score = float(parts[0])
            score = max(0.0, min(1.0, score))
            return score
        except (ValueError, IndexError):
            print(f"Unable to parse score: {parts[0] if parts else 'None'}")
            return None
    else:
        end_idx = text.find("#", start_idx + 1)
        return content_after_tag if end_idx == -1 else content_after_tag[:end_idx].strip()

def single_api_call_with_retry(prompt: str, index: int, max_retries: int = 3) -> Tuple[int, float]:
    """
    Single API call with retry mechanism
    
    Args:
        prompt: user instruction
        answer: model response
        index: sample index
        max_retries: maximum number of retries
    
    Returns:
        (index, score): index and its corresponding score
    """
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=prompt,
                temperature=0.1,
                max_tokens=512,
                seed=42
            )
            content = response.choices[0].message.content
            # response = client.completions.create(
            #     model=model,
            #     prompt= prompt,
            #     temperature=0.4,
            #     top_p=1,    # Nucleus sampling
            #     max_tokens=8000,
            # )
            # finish_reason = response.choices[0].finish_reason
            # print("finish reason {}".format(finish_reason))
            # content = response.choices[0].text.strip()
            return index, content
                    
        except Exception as e:
            print(f"[ERROR] Index {index} attempt {attempt + 1} request failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
    
    # If all retries fail, return a default score
    print(f"Warning: Index {index} final score invalid, using default value 0.0")
    return index, ""

def query_vllm_batch( question_strs: List[Dict[str, Any]],
                       max_workers: int =200) -> List[float]:
    """
    Batch compute reward scores
    
    Args:
        data_sources: list of data sources
        solution_strs: list of model outputs
        ground_truths: list of ground-truth answers
        extra_infos: list of additional information (contains question)
        max_workers: maximum number of concurrent threads
    
    Returns:
        List[float]: corresponding list of scores
    """
    # Prepare task list
    tasks = []
    for i,  question_str in enumerate(question_strs):
        prompt = question_str
        tasks.append((prompt, i))
    

    responses = [""] * len(question_strs)

    # Use thread pool for concurrent execution
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_index = {
            executor.submit(single_api_call_with_retry, prompt, index): index 
            for prompt, index in tasks
        }
        
        # Collect results
        completed_count = 0
        for future in as_completed(future_to_index):
            try:
                index, response = future.result()
                responses[index] = response
                completed_count += 1
                # Display progress
                # if completed_count %50 == 0 or completed_count == len(tasks):
                #     print(f"Batch query progress: {completed_count}/{len(tasks)}")
                    
            except Exception as e:
                index = future_to_index[future]
                print(f"Thread {index} failed: {e}")
                responses[index] = ""
    # print(f"Batch query complete. Total processed: {len(responses)} samples")
    return responses

def query_vllm( question_strs):
    return query_vllm_batch( question_strs)