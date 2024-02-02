import tkinter as tk
from tkinter import filedialog
from datetime import datetime, timedelta
import os
import pysrt
from deep_translator import GoogleTranslator, MicrosoftTranslator, ChatGptTranslator, PonsTranslator
import logging
import threading
import pickle
from mtranslate import translate

os.environ["OPEN_API_KEY"] = ""
os.environ["MICROSOFT_API_KEY"] = ""

# Configure logging
logging.basicConfig(filename="translate.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger()

HISTORY_FILE = "translation_history.pkl"
TRANSLATIONS_DIR = "translations"

# Load translation history from file
try:
    with open(HISTORY_FILE, "rb") as history_file:
        translation_history = pickle.load(history_file)
except FileNotFoundError:
    translation_history = []

def save_history_to_file():
    with open(HISTORY_FILE, "wb") as history_file:
        pickle.dump(translation_history, history_file)

def on_history_select(event, history_listbox, file_info_label):
    selected_index = history_listbox.curselection()
    if selected_index:
        selected_index = int(selected_index[0])
        file_path, _, _ = translation_history[selected_index]
        file_info_label.config(text=f"Original File: {os.path.basename(file_path)}")

def translate_srt(filepath, target_lang, translation_service, source_lang, new_filename, status_label, file_info_label, history_listbox, root, info_status_label, original_text_label, translated_text_label, progress_label, progress_bar):
    subs = pysrt.open(filepath)
    total_rows = len(subs)
    start_time = datetime.now()
    success = True

    def update_status(idx, original_text, translated_text, remaining_time, file_info_label, progress_label, progress_bar):
        status_label.config(text=f"Translating row {idx}/{total_rows} - Original: '{original_text}' - Translated: '{translated_text}'")
        file_info_label.config(text=f"Original File: {os.path.basename(filepath)} - Total Rows: {total_rows} - Original Language: {source_lang} Target Language: {target_lang}")
        progress_label.config(text=f"Progress: {idx}/{total_rows} - Estimated Remaining Time: {remaining_time}")
        progress_bar["value"] = idx
        root.update_idletasks()

    def estimate_remaining_time(current_row, total_rows, start_time):
        elapsed_time = datetime.now() - start_time
        rows_per_second = current_row / max(elapsed_time.total_seconds(), 0.001)  # Ensure non-zero denominator
        remaining_rows = total_rows - current_row
        remaining_time_seconds = remaining_rows / rows_per_second
        remaining_time = timedelta(seconds=max(remaining_time_seconds, 0))  # Ensure non-negative remaining time
        return str(remaining_time)

    try:
        for idx, sub in enumerate(subs, start=1):
            if idx % 1 == 0:  # Update status every 1 rows
                remaining_time = estimate_remaining_time(idx, total_rows, start_time)
                update_status(idx, sub.text, "", remaining_time, file_info_label, progress_label, progress_bar)  # Update status

            if translation_service == 'google':
                result = GoogleTranslator(source=source_lang, target=target_lang).translate(sub.text)
            elif translation_service == 'microsoft':
                result = translate(sub.text, target_lang)
            elif translation_service == 'chatgpt':
                result = ChatGptTranslator(source=source_lang, target=target_lang, api_key='').translate(sub.text)
            elif translation_service == 'pons':
                result = PonsTranslator(source=source_lang, target=target_lang).translate(sub.text)
            else:
                raise ValueError(f"Invalid translation service: {translation_service}")

            logger.info(f"Translating subtitle from {source_lang} to {target_lang} - {sub.start} - {sub.end} in file: {filepath}")
            sub.text = result

            if idx % 1 == 0:  # Update status every 1 rows
                remaining_time = estimate_remaining_time(idx, total_rows, start_time)
                root.after(1, update_status, idx, sub.text, result, remaining_time, file_info_label, progress_label, progress_bar)  # Update status every 1 millisecond

    except Exception as e:
        logger.error(f"Translation failed: {e}")
        success = False

    finally:
        status_label.config(text=f"Translation completed for {os.path.basename(filepath)} - Total Rows: {total_rows}")
        root.update_idletasks()

        # Add entry to history
        history_entry = f"{os.path.basename(filepath)} - {source_lang} to {target_lang} - {'Success' if success else 'Failure'} - Duration: {datetime.now() - start_time}"
        translation_history.append((filepath, history_entry, success))
        save_history_to_file()

        history_listbox.insert(tk.END, history_entry)
        root.update_idletasks()

        # Ensure the translations directory exists
        if not os.path.exists(TRANSLATIONS_DIR):
            os.makedirs(TRANSLATIONS_DIR)

        if not new_filename:
            new_filename = os.path.basename(filepath)[:-4] + f"_{target_lang}.srt"
        else:
            new_filename += ".srt"

        new_filepath = os.path.join(TRANSLATIONS_DIR, new_filename)
        subs.save(new_filepath, encoding="utf-8")

        duration = datetime.now() - start_time
        duration_str = str(duration.total_seconds())
        logger.info(f"Translation completed for file: {filepath}, Duration: {duration_str} seconds, Source Language: {source_lang}, Target Language: {target_lang}, Output File: {new_filepath}")

# Tkinter GUI setup
root = tk.Tk()
root.title("Subtitle Translator by Lovsan")

# Variables for options
target_lang_var = tk.StringVar()
translation_service_var = tk.StringVar()
source_lang_var = tk.StringVar(value="en")
file_or_folder_var = tk.StringVar(value="file")

# Language options
source_lang_label = tk.Label(root, text="Source Language:")
source_lang_entry = tk.Entry(root, textvariable=source_lang_var)

# Target language options
target_lang_label = tk.Label(root, text="Target Language:")
target_lang_options = tk.OptionMenu(root, target_lang_var, "af", "sq", "am", "ar", "hy", "as", "ay", "az", "bm", "eu", "be", "bn", "bho", "bs", "bg", "ca", "ceb", "ny", "zh-CN", "zh-TW", "co", "hr", "cs", "da", "dv", "doi", "nl", "en", "eo", "et", "ee", "tl", "fi", "fr", "fy", "gl", "ka", "de", "el", "gn", "gu", "ht", "ha", "haw", "iw", "hi", "hmn", "hu", "is", "ig", "ilo", "id", "ga", "it", "ja", "jw", "kn", "kk", "km", "rw", "gom", "ko", "kri", "ku", "ckb", "ky", "lo", "la", "lv", "ln", "lt", "lg", "lb", "mk", "mai", "mg", "ms", "ml", "mt", "mi", "mr", "mni-Mtei", "lus", "mn", "my", "ne", "no", "or", "om", "ps", "fa", "pl", "pt", "pa", "qu", "ro", "ru", "sm", "sa", "gd", "nso", "sr", "st", "sn", "sd", "si", "sk", "sl", "so", "es", "su", "sw", "sv", "tg", "ta", "tt", "te", "th", "ti", "ts", "tr", "tk", "ak", "uk", "ur", "ug", "uz", "vi", "cy", "xh", "yi", "yo", "zu")

# Translation service options
translation_service_label = tk.Label(root, text="Translation Service:")
translation_service_dropdown = tk.OptionMenu(root, translation_service_var, "google", "microsoft", "chatgpt", "pons")

# Output filename
output_filename_label = tk.Label(root, text="Output Filename (optional):")
output_filename_entry = tk.Entry(root)

# File or folder selection
file_or_folder_label = tk.Label(root, text="Choose File or Folder:")
file_or_folder_radiobutton_file = tk.Radiobutton(root, text="File", variable=file_or_folder_var, value="file")
file_or_folder_radiobutton_folder = tk.Radiobutton(root, text="Folder", variable=file_or_folder_var, value="folder")

# Translate button
translate_button = tk.Button(root, text="Choose file to Translate", command=lambda: on_translate_button(root))

# Status label
status_label = tk.Label(root, text="", bd=1, relief=tk.SUNKEN, anchor=tk.W)

# File info label
file_info_label = tk.Label(root, text="", bd=1, relief=tk.SUNKEN, anchor=tk.W)

# Info status label
info_status_label = tk.Label(root, text="", bd=1, relief=tk.SUNKEN, anchor=tk.W)

# Original text label
original_text_label = tk.Label(root, text="Original Text:")
original_text_label.grid(row=9, column=0, columnspan=2, sticky=tk.W+tk.E)

# Translated text label
translated_text_label = tk.Label(root, text="Translated Text:")
translated_text_label.grid(row=10, column=0, columnspan=2, sticky=tk.W+tk.E)

# Progress label
progress_label = tk.Label(root, text="Progress:")
progress_label.grid(row=11, column=0, columnspan=2, sticky=tk.W+tk.E)

# Progress bar
progress_bar = tk.Progressbar(root, orient="horizontal", length=200, mode="determinate")
progress_bar.grid(row=12, column=0, columnspan=2, sticky=tk.W+tk.E)

# History label
history_label = tk.Label(root, text="Translation History")

# History listbox
history_listbox = tk.Listbox(root, selectmode=tk.SINGLE, width=140, height=10)
history_listbox.bind("<ButtonRelease-1>", lambda event: on_history_select(event, history_listbox, file_info_label))

def on_translate_button(root):
    target_lang = target_lang_var.get()
    translation_service = translation_service_var.get()
    source_lang = source_lang_var.get()
    file_or_folder = file_or_folder_var.get()
    new_filename = output_filename_entry.get()
    
    if file_or_folder == "file":
        filepath = filedialog.askopenfilename(title="Select Subtitle File", filetypes=[("Subtitle Files", "*.srt")])
    else:
        filepath = filedialog.askdirectory(title="Select Folder Containing Subtitle Files")

    if filepath:
        # Start translation in a separate thread
        threading.Thread(target=translate_srt, args=(filepath, target_lang, translation_service, source_lang, new_filename, status_label, file_info_label, history_listbox, root, info_status_label, original_text_label, translated_text_label, progress_label, progress_bar)).start()

# Layout
source_lang_label.grid(row=0, column=0)
source_lang_entry.grid(row=0, column=1)

target_lang_label.grid(row=1, column=0)
target_lang_options.grid(row=1, column=1)

translation_service_label.grid(row=2, column=0)
translation_service_dropdown.grid(row=2, column=1)

output_filename_label.grid(row=3, column=0)
output_filename_entry.grid(row=3, column=1)

file_or_folder_label.grid(row=4, column=0)
file_or_folder_radiobutton_file.grid(row=4, column=1)
# file_or_folder_radiobutton_folder.grid(row=4, column=2)

translate_button.grid(row=5, column=0, columnspan=2)

status_label.grid(row=6, column=0, columnspan=2, sticky=tk.W+tk.E)
file_info_label.grid(row=7, column=0, columnspan=2, sticky=tk.W+tk.E)
info_status_label.grid(row=8, column=0, columnspan=2, sticky=tk.W+tk.E)
original_text_label.grid(row=9, column=0, columnspan=2, sticky=tk.W+tk.E)
translated_text_label.grid(row=10, column=0, columnspan=2, sticky=tk.W+tk.E)
progress_label.grid(row=11, column=0, columnspan=2, sticky=tk.W+tk.E)
progress_bar.grid(row=12, column=0, columnspan=2, sticky=tk.W+tk.E)

history_label.grid(row=13, column=0, columnspan=2, sticky=tk.W+tk.E)
history_listbox.grid(row=14, column=0, columnspan=2, sticky=tk.W+tk.E)

# Load history into listbox
for entry in translation_history:
    history_listbox.insert(tk.END, entry[1])

# Set fixed width for listboxes
history_listbox.config(width=150)

root.mainloop()

