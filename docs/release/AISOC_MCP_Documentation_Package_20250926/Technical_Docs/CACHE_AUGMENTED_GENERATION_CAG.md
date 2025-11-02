# Cache-Augmented Generation (CAG) in LLMs

## Ringkasan
Cache-Augmented Generation (CAG) adalah teknik untuk mempercepat dan menyederhanakan integrasi pengetahuan eksternal ke dalam Large Language Models (LLMs). Berbeda dengan Retrieval-Augmented Generation (RAG) yang melakukan pencarian data secara real-time, CAG memuat dokumen/pengetahuan ke dalam context model dan menyimpan state inferensi (Key-Value Cache/KV cache). Dengan ini, model dapat mengakses informasi secara instan tanpa latensi retrieval.

## Perbandingan CAG vs RAG
- **RAG**: Melakukan pencarian ke knowledge base setiap kali ada pertanyaan, sehingga ada latensi retrieval.
- **CAG**: Pengetahuan dimuat sekali ke context, cache disimpan, dan digunakan berulang kali untuk menjawab pertanyaan tanpa retrieval ulang.

## Kelebihan CAG
- Jawaban lebih cepat (tanpa retrieval loop)
- Efisien untuk knowledge base yang kecil/stabil
- Cache dapat disimpan dan digunakan lintas sesi

## Langkah-langkah Implementasi CAG

### 1. Prasyarat
- Akun HuggingFace & token akses
- File `document.txt` berisi pengetahuan yang ingin dimuat

### 2. Setup Project
- Install library: `torch`, `transformers`, `DynamicCache`
- Import library:
  ```python
  import torch
  from transformers import AutoTokenizer, AutoModelForCausalLM
  from transformers.cache_utils import DynamicCache
  import os
  ```

### 3. Load Model & Tokenizer
  ```python
  model_name = "mistralai/Mistral-7B-Instruct-v0.1"
  tokenizer = AutoTokenizer.from_pretrained(model_name, token="YOUR_HF_TOKEN", trust_remote_code=True)
  model = AutoModelForCausalLM.from_pretrained(
      model_name,
      torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
      device_map="auto",
      trust_remote_code=True,
      token="YOUR_HF_TOKEN")
  device = "cuda" if torch.cuda.is_available() else "cpu"
  model.to(device)
  ```

### 4. Buat Prompt Pengetahuan & KV Cache
  ```python
  with open("document.txt", "r", encoding="utf-8") as f:
      doc_text = f.read()
  system_prompt = f"""<|system|>You are an assistant who provides concise factual answers.<|user|>Context:{doc_text}Question:""".strip()
  def get_kv_cache(model, tokenizer, prompt: str) -> DynamicCache:
      device = model.model.embed_tokens.weight.device
      input_ids = tokenizer(prompt, return_tensors="pt").input_ids.to(device)
      cache = DynamicCache()
      with torch.no_grad():
          _ = model(
              input_ids=input_ids,
              past_key_values=cache,
              use_cache=True
          )
      return cache
  ronan_cache = get_kv_cache(model, tokenizer, system_prompt)
  origin_len = ronan_cache.key_cache[0].shape[-2]
  print("KV cache built.")
  ```

### 5. Menjawab Pertanyaan dengan Cache
  ```python
  def clean_up(cache: DynamicCache, origin_len: int):
      for i in range(len(cache.key_cache)):
          cache.key_cache[i] = cache.key_cache[i][:, :, :origin_len, :]
          cache.value_cache[i] = cache.value_cache[i][:, :, :origin_len, :]
  question1 = "Who is Ronan Takizawa?"
  clean_up(ronan_cache, origin_len)
  input_ids_q1 = tokenizer(question1 + "\n", return_tensors="pt").input_ids.to(device)
  def generate(model, input_ids: torch.Tensor, past_key_values, max_new_tokens: int = 50) -> torch.Tensor:
      device = model.model.embed_tokens.weight.device
      origin_len = input_ids.shape[-1]
      input_ids = input_ids.to(device)
      output_ids = input_ids.clone()
      next_token = input_ids
      with torch.no_grad():
          for _ in range(max_new_tokens):
              out = model(
                  input_ids=next_token,
                  past_key_values=past_key_values,
                  use_cache=True
              )
              logits = out.logits[:, -1, :]
              token = torch.argmax(logits, dim=-1, keepdim=True)
              output_ids = torch.cat([output_ids, token], dim=-1)
              past_key_values = out.past_key_values
              next_token = token.to(device)
              if model.config.eos_token_id is not None and token.item() == model.config.eos_token_id:
                  break
      return output_ids
  gen_ids_q1 = generate(model, input_ids_q1, ronan_cache)
  answer1 = tokenizer.decode(gen_ids_q1[0], skip_special_tokens=True)
  print("Q1:", question1)
  print("A1:", answer1)
  ```

### 6. Simpan & Muat Ulang Cache
  ```python
  import os
  cache_dir = "cag_cache"
  os.makedirs(cache_dir, exist_ok=True)
  torch.save(ronan_cache, os.path.join(cache_dir, "ronan_knowledge.cache"))
  loaded_cache = torch.load(os.path.join(cache_dir, "ronan_knowledge.cache"))
  # Gunakan loaded_cache untuk pertanyaan lain
  ```

## Kesimpulan
CAG menyederhanakan arsitektur AI dengan menyimpan knowledge base kecil langsung di context window model, menghilangkan kebutuhan retrieval loop seperti pada RAG, dan mengurangi latensi. Cocok untuk knowledge base yang stabil dan tidak terlalu besar.

---
Sumber: [Cache-Augmented Generation (CAG) in LLMs: A Step-by-Step Tutorial](https://blog.gopenai.com/cache-augmented-generation-cag-in-llms-a-step-by-step-tutorial-6ac35d415eec)
