import torch
from transformers import MT5Tokenizer, MT5ForConditionalGeneration

torch_device = 'cuda' if torch.cuda.is_available() else 'cpu'

USE_L1_LEVEL = False

#load the model
model_id = '/mnt/data/samdavid/projects/projects/dissertation/training_code/t5_finetune/' + 'cowsl2h_MT5_model'
tokenizer = MT5Tokenizer.from_pretrained('google/mt5-base')
model = MT5ForConditionalGeneration.from_pretrained(model_id).to(torch_device)

def correct_grammar(input_text,num_return_sequences):
  batch = tokenizer([input_text],truncation=True,padding='max_length',max_length=64, return_tensors="pt").to(torch_device)
  translated = model.generate(**batch,max_length=64,num_beams=4, num_return_sequences=num_return_sequences, temperature=1.5, do_sample=True)
  tgt_text = tokenizer.batch_decode(translated, skip_special_tokens=True)
  return tgt_text

if __name__ == "__main__":
  ## Testing the model on text
  text = 'Yo soy una hombre .'
  print(correct_grammar(text, num_return_sequences=2))
