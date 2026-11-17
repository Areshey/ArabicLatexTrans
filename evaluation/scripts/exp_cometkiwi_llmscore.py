import os
import json
#from streamlit import text
from tqdm import tqdm
import time
import requests
import re

#from comet import download_model, load_from_checkpoint

def calculate_cometkiwi():
    

    output_dir = "./evaluation/deepseek-v3"
    exp_dir = "./evaluation"

    model_path = download_model("Unbabel/wmt22-cometkiwi-da")
    model = load_from_checkpoint(model_path)

    cometkiwi_score = []
    score_path = os.path.join(exp_dir, "cometkiwi_score.json")

    for paper_folder in tqdm(os.listdir(output_dir), desc=f"Evaluating...", unit="paper"):
        paper_path = os.path.join(output_dir, paper_folder)
        data_path = os.path.join(paper_path, "merged_data.json")
        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        model_output = model.predict(data, batch_size=2, gpus=1)
        cometkiwi_score.append({
            "fold": paper_folder,
            "score": model_output["system_score"]
        })

        with open(score_path, 'w', encoding='utf-8') as f:
            json.dump(cometkiwi_score, f, ensure_ascii=False, indent=2)

def calculate_llmscore():
    
    outputs = "./outputs"

    scores_path = "./scores/llm_score.json"

    os.makedirs("./scores", exist_ok=True)
    # Adapted the evaluation prompt for English-to-Arabic translation.  Updated by Imaan Alkhanen
    prompt = """
    You are a professional translation evaluator. Given an English source paragraph and its Arabic translation, evaluate the translation quality according to the following criteria:

    - **Faithfulness**: How accurately and completely does the translation convey the meaning of the source text?

    - **Fluency**: Is the translation natural, idiomatic, and grammatically correct in Arabic?

    - **Terminology and Formatting Consistency**: Are all technical terms translated correctly and consistently throughout the paragraph? Is the formatting—such as emphasis, symbols, references, and structural markers—preserved where applicable?

    - **Contextual Coherence**: Does the translation maintain logical flow, appropriate pronoun/reference usage, and contextual consistency across sentences within the paragraph?

    Score each dimension from 0 to 10. Then, compute a final overall score (0 to 10), reflecting the overall translation quality, and round it to one decimal place.

    **Only return the final overall score as a number. Do not include explanations, sub-scores, or any additional content.**

    """
    api_key = os.environ["OPENAI_API_KEY"]
    base_url = "https://api.openai.com/v1/chat/completions"

    def extract_first_number(text: str):
        text = text.strip()
        if not re.fullmatch(r"(?:10(?:\.0+)?|[0-9](?:\.\d+)?)", text):
            return "N/A"
        return float(text)

    def request_gpt4o(src, tgt):
        """
        Evaluates English-to-Arabic translation quality using GPT-4o.
        """
        payload = {
            "model": "gpt-4o",
            "messages": [
                {
                    "role": "system", 
                    "content": f"{prompt}"
                },
                {
                    "role": "user", 
                    "content": f"<en source>:\n{src}\n<ar translation>:\n{tgt}"
                }
            ],
            "temperature": 0.2,
            # "max_length": 100000,
            # "max_new_tokens": 8192
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        for attempt in range(1, 4):
            try:
                response = requests.post(base_url, json=payload, headers=headers, timeout=100)
                response.raise_for_status()  
                result = response.json()
                score = extract_first_number(result["choices"][0]["message"]["content"])
                if score == "N/A":
                    return "N/A"
                if score < 0 or score > 10:
                    return "N/A"
                
                return score
            except requests.exceptions.RequestException as e:
                print(f"API request failed (attempt {attempt}/3): {e}")

                if attempt < 3:
                    time.sleep(3)  
                else:
                    return "N/A"


    gpt4o_score_val = []
    paper_folders = [
        folder for folder in os.listdir(outputs)
        if folder.startswith("ar_")
        and os.path.isdir(os.path.join(outputs, folder))
    ] 
    for paper_folder in tqdm(paper_folders, desc="Evaluating...", unit="paper"):
        paper_path = os.path.join(outputs, paper_folder)
        # Adapted input handling for ArabicLaTeXTrans translation outputs. Updated by Imaan Alkhanen
        data_path = os.path.join(paper_path, "sections_map.json")
        if not os.path.isfile(data_path):
            print(f"Skipping {paper_folder}: sections_map.json not found")
            continue
        gpt4o_scores = []

        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        data = [
                    item for item in data
                    if str(item.get("section")) not in ("-1", "0")
                    and item.get("content")
                    and item.get("trans_content")
                ]
        merged_items = []
        i = 0
        while i < len(data):
            item1 = data[i]
            item2 = data[i+1] if i + 1 < len(data) else None

            merged_src = item1["content"]
            merged_mt = item1["trans_content"]

            if item2:
                merged_src += "\n" + item2["content"]
                merged_mt += "\n" + item2["trans_content"]

            merged_items.append({
                "src": merged_src,
                "mt": merged_mt
            })

            i += 2  

        for item in tqdm(merged_items, desc=f"Evaluating {paper_folder}...", unit="item"):
            per_data_score = request_gpt4o(item["src"], item["mt"])
            gpt4o_scores.append(per_data_score)

        valid_scores = [float(score) for score in gpt4o_scores if score != "N/A"]
        avg_score_paper = (
            round(sum(valid_scores) / len(valid_scores), 2)
            if valid_scores else None
        )

        gpt4o_score_val.append({
            "fold": paper_folder,
            "score": avg_score_paper,
            "evaluated_items": len(valid_scores),
            "failed_items": len(gpt4o_scores) - len(valid_scores)
        })

        with open(scores_path, 'w', encoding='utf-8') as f:
            json.dump(gpt4o_score_val, f, ensure_ascii=False, indent=2)
# Updated by Imaan Alkhanen
# Disabled COMETKiwi execution; the function remains available.
# calculate_cometkiwi()           
if __name__ == "__main__":
    # calculate_cometkiwi()  # Disabled
    calculate_llmscore()