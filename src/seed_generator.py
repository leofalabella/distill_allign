import json
import random
import logging
from pathlib import Path
from typing import List, Dict, Any
import requests
from dotenv import load_dotenv
import os
import re

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def configure():
    load_dotenv()

class MathProbGenerator:
    """Generates the logical skeletons for mathematical reasoning, where the result 
    is always an integer."""

    def __init__(self):
        self.categories = ["linear_equations", "ratio_reasoning", "percentage_logic"]
    
    def generate_skeleton(self) -> Dict[str, Any]:
        category = random.choice(self.categories)

        if category == "linear_equations":
            # ax + b = c
            x = random.randint(5, 50)
            a = random.randint(2, 10)
            b = random.randint(1, 100)
            c = a * x + b
            return {
                "category": category,
                "variables": {"a": a, "b": b, "c": c},
                "answer": x
            }
        
        elif category == "ratio_reasoning":
            # A/B = X/C
            p = random.randint(1,9)
            q = random.randint(1,9)
            k = random.randint(2,10)
            m = random.randint(2,10)

            a, b = p * k, q * k
            c = q * m
            x = p * m

            return {
                "category": category,
                "variables": {"a": a, "b": b, "c": c},
                "answer": x,
                "logic_type": "solve_for_x"
            }

        elif category == "percentage_logic":
            # a * (1+b) * (1+c) = x
            # to guarantee and int answer for ANY integer percentage b and c, a must be
            # multiple of 10,000
            k = random.randint(1,5)
            a = 10000 * k
            b = random.randint(-50, 50)
            c = random.randint(-50, 50)

            step1 = a * (100 + b) // 100
            x = step1 * (100 + c) // 100

            return {
                "category": category,
                "variables": {"base_value": a, "percent_1": b, "percent_2": c},
                "answer": x,
            }
        else:
            return {}

class TeacherSynthesizer:
    """Interacts with a 'teacher' LLM to turn skeletons into word problems."""

    def __init__(self, api_key:str):
        self.api_key = api_key
        self.url = "https://openrouter.ai/api/v1/chat/completions" 

        # system prompt
        self.system_prompt = (
            "You are a Mathematical Data Synthesis engine. Your task is to turn raw logic skeletons "
            "into engaging, high-quality word problems. \n"
            "STRICT RULES:\n"
            "1. Use the EXACT numbers provided. Never change them.\n"
            "2. Ensure the logic of the story perfectly matches the provided variables.\n"
            "3. Output MUST follow this format exactly:\n"
            "Problem: <the story>\n"
            "Reasoning: <step-by-step logic>\n"
            "Final Answer: <number>"
        )

    def _get_few_shot_examples(self, category: str) -> str:
        """Provides an example for the model"""
        if category == "linear_equations":
            return (
                "Example Input: variables {'a': 3, 'b': 10, 'c': 40}, answer 10\n"
                "Example Output:\n"
                "Problem: A rental company charges a $10 base fee plus $3 per hour for a bike. If a customer paid $40, how many hours did they rent the bike?\n"
                "Reasoning: 1. Subtract the base fee: 40 - 10 = 30. 2. Divide by the hourly rate: 30 / 3 = 10.\n"
                "Final Answer: 10"
            )
        elif category == "ratio_reasoning":
            return (
                "Example Input: variables {'a': 3, 'b': 10, 'c': 40}, answer 10\n"
                "Example Output:\n"
                "Problem: A baker is following a recipe that take 3 parts of sugar for 10 of flour. If added 40g of flour, how many grams of sugar he should add?\n"
                "Reasoning: 1. Find the factor that multiplied the flour: 40 / 10 = 4. 2. Mutiply the factor by the sugar ratio: 3 * 4 = 12.\n"
                "Final Answer: 12"
            )
        elif category == "percentage_logic":
            return (
                "Example Input: variables {'base_value': 10000, 'percent_1': 20, 'c': -40}, answer 10\n"
                "Example Output:\n"
                "Problem: A car buyer is interested in buying a car that has the initial value of $10000. In addition, they have to pay 20% taxes on it. Finally, the car broker offered a 40%% discount of the final price. How much the buyer will pay in the end?\n"
                "Reasoning: 1. Find the price after taxes: 10000 * (100 + 20)/100 = 12000. 2. Apply the discount: 12000 * (100-40)/100 = 7200.\n"
                "Final Answer: 7200"
            )
        return ""


    def create_prompt(self, skeleton: Dict[str, Any]) -> str:
        example = self._get_few_shot_examples(skeleton["category"])
        vars = skeleton['variables']
        prompt = (
            f"{example}\n\n"
            f"Now generate a new one for:\n"
            f"Input: variables {skeleton['variables']}, answer {skeleton['answer']}\n"
            f"Output:"
        )
        return prompt
    
    def call_teacher(self, skeleton: Dict[str, Any]) -> str:
        """
        API call
        """
        prompt = self.create_prompt(skeleton)

        payload = {
            # "model": "mistralai/mistral-7b-instruct:free",
            "model": "qwen/qwen3-4b:free",
            "messages": [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
            ],
            "temperature": 0.7
        }

        response = requests.post(
        url= self.url,
        headers={
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        },
        data=json.dumps(payload)
        )


        res_json = response.json()

        # Add error handling for API failures
        if "choices" in res_json:
            return res_json["choices"][0]["message"]["content"]
        else:
            print(f"Error: {res_json}")
            return ""

class DataValidator:
    """Ensures the generated response match the inteded logic"""

    @staticmethod
    def verify_answer(response: str, expected_answer: int) -> bool:
        """
        Use Regex to extract the 'Final Answer' from the response
        and compare it to the expected_answer.
        """
        # Pattern looks for "Final Answer:", optional whitespace,
        # an optional negative sign, and one or more digits.
        pattern = "Final Answer:\s*(-?\d+)"
        match = re.search(pattern, response, re.IGNORECASE)
        
        if match:
            try:
                # Extract the first capture group (the number)
                model_answer = int(match.group(1))
                return model_answer == expected_answer
            except ValueError:
                logging.error(f"Could not convert '{match.group(1)}' to an integer.")
                return False
        else:
            logging.warning(f"No 'Final Answer' pattern found in response: {response[:50]}...")
            return False


def main():
    # Configuration
    NUM_SAMPLES = 10
    OUTPUT_FILE = Path("seed_data.jsonl")

    generator = MathProbGenerator()
    synthesizer = TeacherSynthesizer(api_key=os.getenv('OPEN_ROUTER_API_KEY'))
    validator = DataValidator()

    dataset = []

    logging.info(f"Starting generation of {NUM_SAMPLES} samples...")

    for i in range(NUM_SAMPLES):
        # generate logic
        skeleton = generator.generate_skeleton()

        # syntehsize word problem
        prompt = synthesizer.create_prompt(skeleton=skeleton)
        raw_response = synthesizer.call_teacher(skeleton=skeleton)

        # validate
        if validator.verify_answer(raw_response, skeleton['answer']):
            entry = {
                "id": i,
                "instruction": raw_response.split("Reasoning:")[0].strip(),
                "reasoning": raw_response,
                "answer": skeleton['answer'],
                "metadata": skeleton
            }
            dataset.append(entry)
            logging.info(f"Sample {i} generated and validated.")
        else:
            logging.warning(f"Sample {i} failed validation. Skipping.")
        
    with open(OUTPUT_FILE, "w") as f:
        for entry in dataset:
            f.write(json.dumps(entry) + "\n")

    logging.info(f"Saved {len(dataset)} samples to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()

