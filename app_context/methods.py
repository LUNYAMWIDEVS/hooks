from django.http import JsonResponse
from moviepy.video.fx.all import resize, crop
from datetime import datetime
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, AudioFileClip, ColorClip, concatenate_videoclips
from tqdm import tqdm
import tempfile
import subprocess
import shutil
import requests
import re
import os
import pandas as pd
import random
import string
import threading
import os
import subprocess
import shutil
import glob
from tqdm import tqdm
from moviepy.editor import AudioFileClip
from PIL import Image
from threading import Lock
from .models import HookContent
from moviepy.config import change_settings

# Set the path to the ImageMagick binary (change to your actual path)
change_settings({"IMAGEMAGICK_BINARY": "magick"})

canceled_tasks = set()
API_KEY = 'AIzaSyBbU9f0mhNDZsUewCnyXHeUwSAtcbZSd_M'  # Replace this with your updated API key

def extract_spreadsheet_id(google_sheet_link):
    # Regular expression to extract the spreadsheet ID from the URL
    match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', google_sheet_link)
    if match:
        return match.group(1)
    else:
        raise ValueError("Invalid Google Sheets URL")
    

def generate_task_id():
    chars = string.ascii_letters + string.digits
    task_id = "task-"
    for _ in range(9):
        task_id += random.choice(chars)
    return task_id


def fetch_google_sheet_data(google_sheet_link):
    # Extract the spreadsheet ID from the provided Google Sheets URL
    spreadsheet_id = extract_spreadsheet_id(google_sheet_link)
    url = f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values:batchGet?ranges=Sheet1&key={API_KEY}'

    print(f"Debug: URL: {url}")

    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        print('data ->',data )
        # Extract the values from the first sheet in the response
        sheet_values = data['valueRanges'][0].get('values', [])
        return sheet_values
    else:
        print(f"Failed to fetch data: {response.status_code}, {response.text}")
        return None


 
def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def extract_word_color_data(google_sheet_link):
    spreadsheet_id = extract_spreadsheet_id(google_sheet_link)
    url = f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}?fields=sheets.data.rowData.values.effectiveValue,sheets.data.rowData.values.textFormatRuns&key={API_KEY}'

    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        rows = data['sheets'][0]['data'][0]['rowData']
        sheet_data = []

        for row in rows:
            row_data = []

            for cell in row['values']:
                formatted_text = cell.get('effectiveValue', {}).get('stringValue', '')
                text_format_runs = cell.get('textFormatRuns', [])

                word_data = []
                last_index = 0

                if not text_format_runs:
                    words = formatted_text.split()
                    for word in words:
                        word_data.append({
                            'text': word,
                            'color': (0, 0, 0)  # Default color black
                        })
                else:
                    for i, run in enumerate(text_format_runs):
                        start_index = run.get('startIndex', 0)
                        end_index = text_format_runs[i + 1]['startIndex'] if i + 1 < len(text_format_runs) else len(formatted_text)

                        # Add any text before the current run
                        if start_index > last_index:
                            pre_run_text = formatted_text[last_index:start_index]
                            pre_run_words = pre_run_text.split()
                            for word in pre_run_words:
                                word_data.append({
                                    'text': word,
                                    'color': (0, 0, 0)  # Default color black
                                })

                        # Add the text for the current run
                        run_text = formatted_text[start_index:end_index]
                        run_words = run_text.split()

                        text_format = run.get('format', {})
                        foreground_color = text_format.get('foregroundColor', {})
                        color_rgb = (
                            int(foreground_color.get('red', 0) * 255),
                            int(foreground_color.get('green', 0) * 255),
                            int(foreground_color.get('blue', 0) * 255)
                        )

                        for word in run_words:
                            word_data.append({
                                'text': word,
                                'color': color_rgb
                            })
                        last_index = end_index

                    # Add any trailing text after the last run
                    if last_index < len(formatted_text):
                        trailing_text = formatted_text[last_index:]
                        trailing_words = trailing_text.split()
                        for word in trailing_words:
                            word_data.append({
                                'text': word,
                                'color': (0, 0, 0)  # Default color black
                            })

                row_data.append(word_data)
            sheet_data.append(row_data)
            print(sheet_data)
        return sheet_data
    else:
        print(f"Failed to fetch data: {response.status_code}, {response.text}")
        return None
   

# def process_files(temp_dir, task_id):
#     hook_content_obj = HookContent.objects.filter(task_id=task_id)
#     if not hook_content_obj:
#         return JsonResponse({"error": "Invalid Task id"})
#     hook_content_obj = hook_content_obj.first()
#     video_files = hook_content_obj.hooks_content # request.FILES.getlist('video')
#     google_sheet_link = hook_content_obj.google_sheets_link # request.form.get('google_sheet_link')
#     range_name = 'Sheet1!A1:Z1'  # Replace this with the actual range if needed
#     voice_id = hook_content_obj.voice_id # request.form.get('voice_id')
#     api_key =  hook_content_obj.eleven_labs_api_key# request.form.get('api_key')
#     parallel_processing = hook_content_obj.parallel_processing # request.form.get('parallel_processing')
#     top_box_color_value =  hook_content_obj.main_box_color   # request.form.get('top_box_color')
#     main_box_color_value =  hook_content_obj.font_color  # request.form.get('text_color')

#     # Convert hex colors to RGB
#     top_box_color = hex_to_rgb(top_box_color_value)
#     default_text_color = hex_to_rgb(main_box_color_value)

#     if not video_files or not google_sheet_link or not voice_id or not api_key or not parallel_processing:
#         return JsonResponse({"error": "Missing form data"}), 400

#     input_videos_folder = os.path.join(temp_dir, 'input', 'video')
#     output_audios_folder = os.path.join(temp_dir, 'output', 'audios')
#     output_videos_folder = os.path.join(temp_dir, 'output', 'videos')

#     os.makedirs(input_videos_folder, exist_ok=True)
#     os.makedirs(output_audios_folder, exist_ok=True)
#     os.makedirs(output_videos_folder, exist_ok=True)

#     video_files_paths = []
#     for video_file in video_files:
#         video_file_path = os.path.join(input_videos_folder, video_file.filename)
#         video_file.save(video_file_path)
#         video_files_paths.append(video_file_path)

#     # Fetch the data from Google Sheets
#     google_sheet_data = fetch_google_sheet_data(google_sheet_link)
#     # Fetch word and color data without affecting the existing flow
#     print("Fetching and printing word-color data:")
#     extract_word_color_data(google_sheet_link)

#     # Convert the Google Sheets data into a DataFrame
#     input_df = pd.DataFrame(google_sheet_data)

#     # Debugging: Print the DataFrame to understand its structure
#     print("Debug: DataFrame structure:")
#     print(input_df)

#     # Check if the DataFrame is empty or missing the 'Hook Text' column
#     if input_df.empty or ('Hook Text' not in input_df.columns and input_df.shape[1] > 0):
#         # Attempt to correct the structure if possible
#         if input_df.shape[1] == 1:
#             input_df.columns = ['Hook Text']
#         else:
#             return JsonResponse({"error": "Ensure the google sheet access is updated to anyone with link."})

#     # Continue processing...
#     # Creating a params dictionary to pass to the background task
#     params = {
#         "input_dir": os.path.join(temp_dir, 'input'),
#         "output_dir": os.path.join(temp_dir, 'output'),
#         "video_files_paths": video_files_paths,
#         "voice_id": voice_id,
#         "api_key": api_key,
#         "parallel_processing": parallel_processing,
#         "task_id": task_id,
#         "temp_dir": temp_dir,
#         "top_box_color": top_box_color,       # Now in RGB format
#         "default_text_color": default_text_color, # Now in RGB format
#         "input_df": input_df,                 # Pass the DataFrame directly
#         "google_sheet_link": google_sheet_link # Include the Google Sheets link in the params
#     }
#     print('params ->', params)

#     # Start the background task and pass params
#     # socketio.start_background_task(target=process, params=params)
#     return JsonResponse({"message": "Processing started", "task_id": task_id})


def process_files(temp_dir, task_id):
    from django.core.cache import cache
    hook_content_obj = HookContent.objects.filter(task_id=task_id).first()

    if not hook_content_obj:
        return JsonResponse({"error": "Invalid Task id"})

    # Extract necessary fields from the object
    video_files = hook_content_obj.hooks_content  # Assuming this is a FileField
    google_sheet_link = hook_content_obj.google_sheets_link
    voice_id = hook_content_obj.voice_id
    api_key = hook_content_obj.eleven_labs_api_key
    parallel_processing = hook_content_obj.parallel_processing
    top_box_color_value = hook_content_obj.main_box_color
    main_box_color_value = hook_content_obj.font_color

    # Convert hex colors to RGB
    top_box_color = hex_to_rgb(top_box_color_value)
    default_text_color = hex_to_rgb(main_box_color_value)

    if not video_files or not google_sheet_link or not voice_id or not api_key or not parallel_processing:
        return JsonResponse({"error": "Missing form data"})

    # Create directories for input/output files
    input_videos_folder = os.path.join(temp_dir, 'input', 'video')
    output_audios_folder = os.path.join(temp_dir, 'output', 'audios')
    output_videos_folder = os.path.join(temp_dir, 'output', 'videos')
    print('step 1')
    # Ensure the directories exist
    os.makedirs(input_videos_folder, exist_ok=True)
    os.makedirs(output_audios_folder, exist_ok=True)
    os.makedirs(output_videos_folder, exist_ok=True)
    print('step 2')
    # Handle video files (FieldFile object)
    video_files_paths = []
    
    # Save the file from FieldFile object
    video_file_name = os.path.basename(video_files.name)  # Get the file name from the FieldFile object
    video_file_path = os.path.join(input_videos_folder, video_file_name)
    print('step 3')
    # Ensure the parent directory for the file exists
    # import pdb;pdb.set_trace()
    os.makedirs(os.path.dirname(video_file_path), exist_ok=True)
    print('step 4')
    # Open the video file and write it to the new location
    with open(video_file_path, 'wb+') as destination:
        for chunk in video_files.chunks():  # Write file in chunks to handle large files
            destination.write(chunk)

    video_files_paths.append(video_file_path)
    print('step 5')
    # Fetch the data from Google Sheets
    google_sheet_data = fetch_google_sheet_data(google_sheet_link)
    print('step 6')
    # Fetch word and color data without affecting the existing flow
    extract_word_color_data(google_sheet_link)
    print('step 7')
    # Convert the Google Sheets data into a DataFrame
    input_df = pd.DataFrame(google_sheet_data)
    print('step 8')
    # Check if the DataFrame is empty or missing the 'Hook Text' column
    if input_df.empty or ('Hook Text' not in input_df.columns and input_df.shape[1] > 0):
        if input_df.shape[1] == 1:
            input_df.columns = ['Hook Text']
        else:
            return JsonResponse({"error": "Ensure the google sheet access is updated to anyone with link."})
    print('step 9', input_df)
    # Create a params dictionary to pass to the background task
    params = {
        "input_dir": os.path.join(temp_dir, 'input'),
        "output_dir": os.path.join(temp_dir, 'output'),
        "video_files_paths": video_files_paths,
        "voice_id": voice_id,
        "api_key": api_key,
        "parallel_processing": parallel_processing,
        "task_id": task_id,
        "temp_dir": temp_dir,
        "top_box_color": top_box_color,
        "default_text_color": default_text_color,
        "input_df": input_df,
        "google_sheet_link": google_sheet_link
    }   
    cache.set(task_id, temp_dir, timeout=600)
    # Debugging: Print the params to verify data
    print('params ->', params)
 
    # Start the background task (uncomment if needed)
    process(params) 
    # socketio.start_background_task(target=process, params=params)
    # socketio.start_background_task(target=process, params=params)
    return JsonResponse({"message": "Processing started", "task_id": task_id})


def process(params):
    task_id = params.get('task_id', None)  # Ensure task_id is set early
    try:
        input_df = params['input_df']
        print(f"Debug: Received input DataFrame:\n{input_df}")

        if 'Hook Text' not in input_df.columns:
            raise Exception("The column 'Hook Text' does not exist in the DataFrame.")

        google_sheet_link = params.get('google_sheet_link')
        if not google_sheet_link:
            raise Exception("Missing 'google_sheet_link' in params.")

        range_name = 'Sheet1!A1:Z1'  # Update as necessary
        word_color_data = extract_word_color_data(google_sheet_link)

        for idx, row in input_df.iterrows():
            hook_text = row['Hook Text']
            print(f"Debug: Processing hook text: {hook_text} (Row {idx})")

        global ELEVENLABS_API_KEY, no_of_parallel_executions

        ELEVENLABS_API_KEY = params['api_key']
        no_of_parallel_executions = params['parallel_processing']

        print(f"Debug: ELEVENLABS_API_KEY: {ELEVENLABS_API_KEY}")
        print(f"Debug: Parallel executions: {no_of_parallel_executions}")

        INPUT_DIR = params['input_dir']
        OUTPUT_DIR = params['output_dir']
        voice_id = params['voice_id']
        temp_dir = params['temp_dir']
        top_box_color = params['top_box_color']
        default_text_color = params['default_text_color']

        input_videos_folder = os.path.join(INPUT_DIR, 'video')
        output_audios_folder = os.path.join(OUTPUT_DIR, 'audios')
        output_videos_folder = os.path.join(OUTPUT_DIR, 'videos')

        OUT_VIDEO_DIM = '720x900'
        OUT_VIDEO_HEIGHT = int(OUT_VIDEO_DIM.split('x')[1])
        OUT_VIDEO_WIDTH = int(OUT_VIDEO_DIM.split('x')[0])

        if len(os.listdir(input_videos_folder)) == 0:
            raise Exception(f"input/videos folder {input_videos_folder} does not contain any videos")
        video_files = sorted([f for f in os.listdir(input_videos_folder) if f.endswith('.mp4') or f.endswith('.mov')])
        print(f"Debug: video_files: {video_files}")

        for col in ["Hook Video Filename", "Input Video Filename", "Audio Filename", "Voice"]:
            if col not in input_df.columns:
                input_df[col] = ''  # Ensure these columns are present

        l_unprocessed_rows = len(input_df[input_df['Hook Video Filename'] == ''])
        print(f"Debug: l_unprocessed_rows: {l_unprocessed_rows}")

        if l_unprocessed_rows == 0:
            print("Debug: No unprocessed rows found in Google Sheet.")

        all_hooks = []
        total_rows = len(input_df)
        current_row = 0

        for idx_1, row in tqdm(input_df.iterrows(), total=total_rows, desc="Processing rows"):
            hook_text = row['Hook Text']
            hook_number = idx_1 + 1

            print(f"Debug: Calling process_audios with idx: {idx_1}, hook_number: {hook_number}")
            try:
                process_audios(ELEVENLABS_API_KEY, row, hook_number, hook_text, input_df, idx_1, output_audios_folder, voice_id)
            except Exception as err:
                print(f"failled to process audio file---->{err}")

        current_thread_count = 0
        for idx, row in tqdm(input_df.iterrows(), total=total_rows, desc="Processing rows"):
            hook_text = row['Hook Text']
            hook_number = idx + 1

            if row['Hook Video Filename'] != '' and os.path.exists(os.path.join(output_videos_folder, row['Hook Video Filename'])):
                video_link = f"/download_output?video_path={os.path.join(output_videos_folder, row['Hook Video Filename'])}"
                print(f"Emitting video link with file name: {row['Hook Video Filename']}")

                continue

            audio_clip = AudioFileClip(os.path.join(output_audios_folder, row['Audio Filename']))
            video_index = idx % len(video_files)
            num_videos_to_use = int(round(audio_clip.duration / 2))

            video_file_size = len(video_files)
            if num_videos_to_use + video_index > video_file_size:
                num_videos_to_use = video_file_size - video_index

            last_video = video_index + num_videos_to_use
            video_files_to_use = [os.path.join(input_videos_folder, video_files[i]) for i in range(video_index, last_video)]

            if params['task_id'] in canceled_tasks:
                return handle_task_cancellation(temp_dir, task_id)

            print(os.path.join(output_audios_folder,row['Audio Filename']),'------------>audio file')
            try:
                process_audio_on_videos(row, video_files_to_use, idx, input_df, hook_number, hook_text, num_videos_to_use, audio_clip, OUT_VIDEO_WIDTH, OUT_VIDEO_HEIGHT, output_videos_folder, total_rows, task_id, top_box_color, default_text_color, word_color_data,audio_file=os.path.join(output_audios_folder,row['Audio Filename']))
            except Exception as err:
                print(f"check on following---->{err}")
            current_thread_count = 0

        for hook in all_hooks:
            try:
                hook.join()
            except Exception as err:
                print('failed to join all hooks')
        print(f"Debug: Task {task_id} completed.")

        # Load your video file
        print(os.path.join(output_videos_folder, 'hook_0.mp4'),'------------>video file')
        video = VideoFileClip(os.path.join(output_videos_folder, 'hook_0.mp4'))

        # Load your audio file
        audio = AudioFileClip(os.path.join(output_audios_folder,row['Audio Filename']))

        # Set the audio to the video
        video_with_audio = video.set_audio(audio)

        # Export the final video
        video_with_audio.write_videofile("media/final_video.mp4", codec="libx264", audio_codec="aac")

        v_file = os.path.join(output_videos_folder,'hook_0.mp4')
        a_file = os.path.join(output_audios_folder,row['Audio Filename'])
        command = [
            'ffmpeg',
            '-i', v_file,
            '-i', a_file,
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-strict', 'experimental',
            'media/hooks_content/final_video_test.mp4'
        ]
        subprocess.run(command)

    except Exception as e:
        print(f"Error during processing: {e}")
        delete_temp_dir(params.get('temp_dir', ''))

# def process(params):
#     # import pdb;pdb.set_trace()
#     task_id = params.get('task_id', None)  # Ensure task_id is set early
#     try:
#         input_df = params['input_df']
#         print(f"Debug: Received input DataFrame:\n{input_df}")

#         if 'Hook Text' not in input_df.columns:
#             raise Exception("The column 'Hook Text' does not exist in the DataFrame.")

#         # Ensure google_sheet_link is provided in params
#         google_sheet_link = params.get('google_sheet_link')
#         if not google_sheet_link:
#             raise Exception("Missing 'google_sheet_link' in params.")

#         range_name = 'Sheet1!A1:Z1'  # Update as necessary
#         word_color_data = extract_word_color_data(google_sheet_link)

#         for idx, row in input_df.iterrows():
#             hook_text = row['Hook Text']
#             print(f"Debug: Processing hook text: {hook_text} (Row {idx})")

#         global ELEVENLABS_API_KEY, no_of_parallel_executions

#         ELEVENLABS_API_KEY = params['api_key']
#         no_of_parallel_executions = params['parallel_processing']

#         print(f"Debug: ELEVENLABS_API_KEY: {ELEVENLABS_API_KEY}")
#         print(f"Debug: Parallel executions: {no_of_parallel_executions}")

#         INPUT_DIR = params['input_dir']
#         OUTPUT_DIR = params['output_dir']
#         voice_id = params['voice_id']
#         temp_dir = params['temp_dir']
#         top_box_color = params['top_box_color']
#         default_text_color = params['default_text_color']
#         # import pdb;pdb.set_trace()
#         input_videos_folder = os.path.join(INPUT_DIR, 'video')
#         output_audios_folder = os.path.join(OUTPUT_DIR, 'audios')
#         output_videos_folder = os.path.join(OUTPUT_DIR, 'videos')

#         OUT_VIDEO_DIM = '720x900'
#         OUT_VIDEO_HEIGHT = int(OUT_VIDEO_DIM.split('x')[1])
#         OUT_VIDEO_WIDTH = int(OUT_VIDEO_DIM.split('x')[0])

#         if len(os.listdir(input_videos_folder)) == 0:
#             raise Exception(f"input/videos folder {input_videos_folder} does not contain any videos")
#         video_files = sorted([f for f in os.listdir(input_videos_folder) if f.endswith('.mp4') or f.endswith('.mov')])
#         print(f"Debug: video_files: {video_files}")

#         for col in ["Hook Video Filename", "Input Video Filename", "Audio Filename", "Voice"]:
#             if col not in input_df.columns:
#                 input_df[col] = ''  # Ensure these columns are present

#         l_unprocessed_rows = len(input_df[input_df['Hook Video Filename'] == ''])
#         print(f"Debug: l_unprocessed_rows: {l_unprocessed_rows}")

#         if l_unprocessed_rows == 0:
#             print("Debug: No unprocessed rows found in Google Sheet.")

#         all_hooks = []
#         total_rows = len(input_df)
#         current_row = 0

#         # Emit initial progress step
#         # socketio.emit('progress', {'task_id': task_id, 'progress': 0, 'step': f"0/{total_rows}"})

#         for idx_1, row in tqdm(input_df.iterrows(), total=total_rows, desc="Processing rows"):
#             hook_text = row['Hook Text']
#             hook_number = idx_1 + 1

#             print(f"Debug: Calling process_audios with idx: {idx_1}, hook_number: {hook_number}")

#             process_audios(ELEVENLABS_API_KEY, row, hook_number, hook_text, input_df, idx_1, output_audios_folder, voice_id)

#         current_thread_count = 0
#         for idx, row in tqdm(input_df.iterrows(), total=total_rows, desc="Processing rows"):
#             hook_text = row['Hook Text']
#             hook_number = idx + 1

#             if row['Hook Video Filename'] != '' and os.path.exists(os.path.join(output_videos_folder, row['Hook Video Filename'])):
#                 video_link = f"/download_output?video_path={os.path.join(output_videos_folder, row['Hook Video Filename'])}"
#                 # socketio.emit('video_link', {'task_id': task_id, 'video_link': video_link, 'file_name': row['Hook Video Filename']})
#                 print(f"Emitting video link with file name: {row['Hook Video Filename']}")

#                 continue

#             audio_clip = AudioFileClip(os.path.join(output_audios_folder, row['Audio Filename']))
#             video_index = idx % len(video_files)
#             num_videos_to_use = int(round(audio_clip.duration / 2))

#             video_file_size = len(video_files)
#             if num_videos_to_use + video_index > video_file_size:
#                 num_videos_to_use = video_file_size - video_index

#             last_video = video_index + num_videos_to_use
#             video_files_to_use = [os.path.join(input_videos_folder, video_files[i]) for i in range(video_index, last_video)]

#             if params['task_id'] in canceled_tasks:
#                 return handle_task_cancellation(temp_dir, task_id)
#             # import pdb;pdb.set_trace()
#             # hook_job = threading.Thread(target=process_audio_on_videos, args=(row, video_files_to_use, idx, input_df, hook_number, hook_text, num_videos_to_use, audio_clip, OUT_VIDEO_WIDTH, OUT_VIDEO_HEIGHT, output_videos_folder, total_rows, task_id, top_box_color, default_text_color, word_color_data))
#             process_audio_on_videos(row, video_files_to_use, idx, input_df, hook_number, hook_text, num_videos_to_use, audio_clip, OUT_VIDEO_WIDTH, OUT_VIDEO_HEIGHT, output_videos_folder, total_rows, task_id, top_box_color, default_text_color, word_color_data)
#             # hook_job = threading.Thread(target=process_audio_on_videos, args=(row, video_files_to_use, idx, input_df, hook_number, hook_text, num_videos_to_use, audio_clip, OUT_VIDEO_WIDTH, OUT_VIDEO_HEIGHT, output_videos_folder, total_rows, task_id, top_box_color, default_text_color, word_color_data))
#             # hook_job.start()
#             # all_hooks.append(hook_job)
#             # current_thread_count += 1
#             # if current_thread_count == int(no_of_parallel_executions):
#             #     for hook in all_hooks:
#             #         hook.join()
#             #     all_hooks.clear()
#             current_thread_count = 0

#         for hook in all_hooks:
#             hook.join()

#         # calculate_total_hours(start_time)

#         # socketio.emit('task_complete', {'task_id': task_id})

#         print(f"Debug: Task {task_id} completed.")
#         # import pdb;pdb.set_trace()
#     except Exception as e:
#         # if task_id:
#             # socketio.emit('error', {'task_id': task_id, 'message': str(e)})
#         print(f"Error during processing: {e}")
#         delete_temp_dir(params.get('temp_dir', ''))

def handle_task_cancellation(temp_dir, task_id):
    delete_temp_dir(temp_dir)
    # socketio.emit('task_cancelled', {'task_id': task_id})

def process_audio_on_videos(row, video_files, idx, input_df, hook_number, hook_text, num_videos_to_use, audio_clip, OUT_VIDEO_WIDTH, OUT_VIDEO_HEIGHT, output_videos_folder, total_rows, task_id, top_box_color, default_text_color, word_color_data,audio_file=None):
    # Remove underscores from the hook text for display
    cleaned_hook_text = hook_text.replace('_', '')
    # import pdb;pdb.set_trace()

    row['Input Video Filename'] = [os.path.basename(considered_video) for considered_video in video_files]
    input_df.at[idx, 'Input Video Filename'] = row['Input Video Filename']

    each_video_duration = audio_clip.duration / num_videos_to_use
    video_clips = []

    for considered_vid in video_files:
        # import  pdb;pdb.set_trace()
        video_clip = VideoFileClip(considered_vid).subclip(0, each_video_duration)
        
        # Apply cropping to maintain aspect ratio without distortion
        video_clip = crop_to_aspect_ratio(video_clip, OUT_VIDEO_WIDTH, OUT_VIDEO_HEIGHT)

        video_clips.append(video_clip)

    final_video_clip = concatenate_videoclips(video_clips)

    # Automatically adjust the font size based on video dimensions and text length
    auto_font_size = max(int(OUT_VIDEO_WIDTH / len(cleaned_hook_text) * 1.5), 20)  # Simple logic to adjust font size

    # Ensure correct word color data is used
    if idx < len(word_color_data):
        specific_word_color_data = word_color_data[idx]
    else:
        specific_word_color_data = []  # Fallback to an empty list if out of range (for safety)

    # Pass specific_word_color_data to the custom text clip creation
    custom_text_clip = create_custom_text_clip(cleaned_hook_text, OUT_VIDEO_WIDTH, OUT_VIDEO_HEIGHT, top_box_color, default_text_color, auto_font_size, specific_word_color_data)

    final_clip = CompositeVideoClip([
        final_video_clip.audio_fadein(0.2).audio_fadeout(0.2),
        final_video_clip,
        custom_text_clip
    ]).set_audio(audio_clip).set_duration(audio_clip.duration)

    output_video_filename = os.path.join(output_videos_folder, f'hook_{idx}.mp4')
    print(output_videos_folder,'---------->output_videos_folder')
    final_clip.write_videofile(output_video_filename, temp_audiofile=os.path.join(output_videos_folder, f"temp-audio_{idx}.m4a"), remove_temp=False, codec='libx264', audio_codec="aac")
    # final_clip.write_videofile(output_video_filename, audio=audio_file, remove_temp=True, codec='libx264', audio_codec="aac")
    # import pdb;pdb.set_trace()
    # Emit video link after processing
    # socketio.emit('video_link', {'task_id': task_id, 'video_link': f"/download_output?video_path={output_video_filename}", 'file_name': os.path.basename(output_video_filename)})
    
    print(f"Emitting video link for {output_video_filename}")

def process_audios(api_key, row, hook_number, hook_text, input_df, idx, output_audios_folder, voice_id):
    print(voice_id)
    if row['Audio Filename'] in (None, '') or not os.path.exists(os.path.join(output_audios_folder, row['Audio Filename'])):
        print(f"Generating voiceover for hook {hook_number}...")
        audio_filename = os.path.join(output_audios_folder, f'hook_{hook_number}.mp3')
        # import pdb;pdb.set_trace()
        try:
            status, voice_name = text_to_speech_file(api_key, hook_text, audio_filename, voice_id)
            row['Voice'] = voice_name
            row['Audio Filename'] = os.path.basename(audio_filename)
            input_df.at[idx, 'Voice'] = voice_name
            input_df.at[idx, 'Audio Filename'] = row['Audio Filename']
        except Exception as err:
            print(f"failed to hook audio file --> {audio_filename}")


def calculate_total_hours(start_time):
    end_time = datetime.now()
    time_difference = end_time - start_time
    total_seconds = time_difference.total_seconds()
    total_hours = total_seconds / 3600
    print(f'total_hours={total_hours}')

def delete_temp_dir(temp_dir):
    try:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        print(f"Temporary directory {temp_dir} deleted successfully.")
    except Exception as e:
        print(f"Error deleting temporary directory {temp_dir}: {str(e)}")

def crop_to_aspect_ratio(video_clip, target_width, target_height):
    # import pdb;pdb.set_trace()
    original_width, original_height = video_clip.size
    target_aspect_ratio = target_width / target_height
    original_aspect_ratio = original_width / original_height

    if original_aspect_ratio > target_aspect_ratio:
        # Crop width to match the target aspect ratio
        new_width = int(target_aspect_ratio * original_height)
        x_center = original_width / 2
        x1 = int(x_center - new_width / 2)
        x2 = int(x_center + new_width / 2)
        y1, y2 = 0, original_height
    else:
        # Crop height to match the target aspect ratio
        new_height = int(original_width / target_aspect_ratio)
        y_center = original_height / 2
        y1 = int(y_center - new_height / 2)
        y2 = int(y_center + new_height / 2)
        x1, x2 = 0, original_width

    # Crop the video to the desired aspect ratio
    cropped_clip = crop(video_clip, x1=x1, y1=y1, x2=x2, y2=y2)

    # If the cropped video is not the exact target size, we adjust it
    if cropped_clip.size != (target_width, target_height):
        # This should not distort the video because we are just adjusting the cropped content
        cropped_clip = cropped_clip.resize((target_width, target_height))
    
    return cropped_clip

import colorgram
from PIL import Image

x11_color_names = {
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
    # ... other X11 color names and their RGB values
}

def rgb_to_color_name(rgb_tuple):
    """
    Converts an RGB color tuple to its closest X11 color name.

    Args:
        rgb_tuple: A tuple representing the RGB color values (r, g, b).

    Returns:
        The closest X11 color name to the given RGB tuple, or None if no close match is found.
    """

    try:
        # Create an image from the RGB tuple
        image = Image.new("RGB", (1, 1), rgb_tuple)

        # Extract the color from the image
        palette = colorgram.extract(image, 1)
        color_rgb = palette[0].rgb

        # Find the closest X11 color name
        closest_name = None
        closest_distance = float('inf')
        for name, color in x11_color_names.items():
            distance = sum((a - b) ** 2 for a, b in zip(color_rgb, color))
            if distance < closest_distance:
                closest_name = name
                closest_distance = distance

        return closest_name
    except Exception as e:
        print(f"Error converting RGB to color name: {e}")
        return None

# Example usage


def create_custom_text_clip(hook_text, OUT_VIDEO_WIDTH, OUT_VIDEO_HEIGHT, top_box_color, text_color, font_size, word_color_data):
    hook_text_parts = split_hook_text(hook_text)
    x_multiplier = OUT_VIDEO_WIDTH / 360
    y_multiplier = OUT_VIDEO_HEIGHT / 450
    min_red_area_h = int(round(40   * y_multiplier))
    fontsize1 = int(round(15 * x_multiplier))
    max_width = OUT_VIDEO_WIDTH - 100

    x_margin = 5

    # Setup Fontconfig for custom font
    font_path = os.path.abspath('dependencies/fonts/mu.otf')
    print(font_path)
    temp_fontconfig_dir = setup_fontconfig(font_path)

    # Build Pango-formatted text string with color for each word for the first part only
    pango_text = ""
    words_in_first_part = hook_text_parts[0].split()

    text_clips_ = []
    for word_data in word_color_data:
        for word_info in word_data:
            word = word_info['text'].capitalize()  # Capitalize the first letter of the word
            
            # Only add the word to pango_text if it is in the first part
            if word in words_in_first_part:
                color = word_info['color']
                print(color,'------------>color')

                # Override the color only if it's not black
                if color == (0, 0, 0):
                    color = text_color  # Use the front-end color if the color is black

                color_hex = "#{:02x}{:02x}{:02x}".format(*color)
                # fontsize1 = 20
                # Apply the font directly in Pango markup
                
                pango_text += f'<span font_desc="Mu Font {fontsize1}" foreground="{color_hex}">{word}</span> '

    print(f"Debug: Pango-formatted text: {pango_text}")

    # Create the text clip with Pango-formatted text for the first part
    # import pdb;pdb.set_trace()
    # pango_text = '<span font_desc="Arial 30" foreground="#ff0000">This is a test</span>'
    try:
        """
        magick -background blue -gravity center -size 612x95 pango:'<span font_desc="Mu Font 30" foreground="#ffffff"><b>This</b></span> <span font_desc="Mu Font 30" foreground="#ffffff"><b>Is</b></span> <span font_desc="Mu Font 30" foreground="#ffffff"><b>How</b></span> <span font_desc="Mu Font 30" foreground="#ffffff"><b>I</b></span> <span font_desc="Mu Font 30" foreground="#ffffff"><b>Fixed</b></span> <span font_desc="Mu Font 30" foreground="#ffffff"><b>The</b></span> <span font_desc="Mu Font 30" foreground="#ffffff"><b>Non</b></span> <span font_desc="Mu Font 30" foreground="#ff0000"><b>Stop</b></span> <span font_desc="Mu Font 30" foreground="#ff0000"><b>Pain</b></span> <span font_desc="Mu Font 30" foreground="#ff0000"><b>In</b></span> <span font_desc="Mu Font 30" foreground="#ff0000"><b>My</b></span> <span font_desc="Mu Font 30" foreground="#ff0000"><b>Neck</b></span>' output.png
        """
        text_clip1 = TextClip(
            # hook_text_parts[0],
            # pango_text.strip(),  # Pango-formatted string with word colors
            filename='/tmp/output.txt',
            size=( max_width , None),
            # size=(800,600),
            method='pangocairo',  # Enable Pango markup
            font='dependencies/fonts/mu.otf',
            fontsize=fontsize1,
            color='white',  # Default color, overridden by Pango markup
            align='center'
        )
        print(f"Debug: Created TextClip with size: {text_clip1.size}")
    except Exception as e:
        print(f"Error creating TextClip: {e}")
        raise

    (text_clip1_w, text_clip1_h) = text_clip1.size
    if text_clip1_h > (min_red_area_h - 10):
        min_red_area_h = text_clip1_h + 10

    bg_clip1 = ColorClip(size=(OUT_VIDEO_WIDTH, min_red_area_h), color=top_box_color)

    text_clip1_y_offset = ((min_red_area_h - text_clip1_h) / 2)

    final_clip = CompositeVideoClip([
        bg_clip1.set_position((0, 0)),
        text_clip1.set_position(("center", text_clip1_y_offset)),
    ], size=(OUT_VIDEO_WIDTH, OUT_VIDEO_HEIGHT))

    # Process the second part (after the hyphen) normally
    if len(hook_text_parts) > 1:
        min_white_area_h = int(round(30 * y_multiplier))
        fontsize2 = int(round(20 * 0.7 * x_multiplier))
        text_clip2 = TextClip(
            hook_text_parts[1],
            size=(OUT_VIDEO_WIDTH - (x_margin * 2), 0),
            method='caption',
            font='dependencies/fonts/mu.otf',
            fontsize=fontsize2,
            color=f"rgb{(0, 0, 0)}",
            align='center',
        )
        (text_clip2_w, text_clip2_h) = text_clip2.size
        if text_clip2_h > (min_white_area_h):
            min_white_area_h = text_clip2_h

        bg_clip2 = ColorClip(size=(OUT_VIDEO_WIDTH, min_white_area_h), color=(255, 255, 255))

        text_clip2_y_offset = min_red_area_h + ((min_white_area_h - text_clip2_h) / 2)

        final_clip = CompositeVideoClip([
            bg_clip1.set_position((0, 0)),
            bg_clip2.set_position((0, min_red_area_h)),
            text_clip1.set_position(('center', text_clip1_y_offset)),
            text_clip2.set_position((x_margin, text_clip2_y_offset)),
        ], size=(OUT_VIDEO_WIDTH, OUT_VIDEO_HEIGHT))

    # Clean up the temporary Fontconfig directory
    try:
        shutil.rmtree(temp_fontconfig_dir)
    except Exception as err:
        print(err)

    return final_clip

def text_to_speech_file(api_key, text: str, save_file_path: str, voice_id: str, remove_punctuation: bool = True) -> bool:
    if remove_punctuation:
        text = text.replace('-', ' ').replace('"', ' ').replace("'", ' ')
        text is re.sub(r'[^\w\s]', '', text)

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key
    }
    data = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }

    response = requests.post(url, json=data, headers=headers)

    if response.status_code != 200:
        raise Exception(f"API request failed with status code {response.status_code}: {response.text}")

    with open(save_file_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)

    return True, voice_id

def split_hook_text(hook_text):
    words = hook_text.split()
    hook_text = ' '.join(word.capitalize() for word in words)

    if ' - ' in hook_text:
        last_dash_index = hook_text.rfind('-')
        line1 = hook_text[:last_dash_index].strip()
        line2 = hook_text[last_dash_index + 1:].strip()
        return [line1, line2]
    else:
        line1 = hook_text
        return [line1]

def setup_fontconfig(font_path):
    # Step 1: Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    print(f"Debug: Created temporary directory at {temp_dir}")

    # Step 2: Prepare the Fontconfig configuration content
    fontconfig_content = f"""<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
    <dir>{os.path.dirname(font_path)}</dir>
    <match target="pattern">
        <test name="family" qual="any">
            <string>Mu Font</string>
        </test>
        <edit name="family" mode="assign" binding="strong">
            <string>Mu Font</string>
        </edit>
        <edit name="file" mode="assign" binding="strong">
            <string>{font_path}</string>
        </edit>
    </match>
</fontconfig>
"""
    print("Debug: Fontconfig content prepared:")
    print(fontconfig_content)

    # Step 3: Write the configuration to the temporary directory
    config_path = os.path.join(temp_dir, "fonts.conf")
    with open(config_path, "w") as f:
        f.write(fontconfig_content.strip())  # Ensure no leading/trailing spaces or newlines
    print(f"Debug: Fontconfig written to {config_path}")

    # Step 4: Set the FONTCONFIG_FILE environment variable
    os.environ["FONTCONFIG_FILE"] = config_path
    print(f"Debug: FONTCONFIG_FILE environment variable set to {config_path}")

    # Step 5: Verify the setup by listing the fonts recognized by Fontconfig
    result = subprocess.run(['fc-list'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print("Debug: Fontconfig available fonts after setup:")
    print(result.stdout.decode())
    
    # Step 6: Check if any errors were reported
    if result.stderr:
        print("Debug: Fontconfig error:")
        print(result.stderr.decode())

    return temp_dir


# def setup_fontconfig(font_path):
#     # Step 1: Create a temporary directory
#     temp_dir = tempfile.mkdtemp()
#     print(f"Debug: Created temporary directory at {temp_dir}")
#     import pdb;pdb.set_trace()
#     # Step 2: Prepare the Fontconfig configuration content
#     fontconfig_content = f"""<?xml version="1.0"?>
#             <!DOCTYPE fontconfig SYSTEM "fonts.dtd">
#             <fontconfig>
#                 <dir>{os.path.dirname(font_path)}</dir>
#                 <match target="pattern">
#                     <test name="family" qual="any">
#                         <string>Mu Font</string>
#                     </test>
#                     <edit name="family" mode="assign" binding="strong">
#                         <string>Mu Font</string>
#                     </edit>
#                     <edit name="file" mode="assign" binding="strong">
#                         <string>{font_path}</string>
#                     </edit>
#                 </match>
#             </fontconfig>
#             """
#     print("Debug: Fontconfig content prepared:")
#     print(fontconfig_content)

#     # Step 3: Write the configuration to the temporary directory
#     config_path = os.path.join(temp_dir, "fonts.conf")
#     with open(config_path, "w") as f:
#         f.write(fontconfig_content.strip())  # Ensure no leading/trailing spaces or newlines
#     print(f"Debug: Fontconfig written to {config_path}")

#     # Step 4: Set the FONTCONFIG_FILE environment variable
#     os.environ["FONTCONFIG_FILE"] = config_path
#     print(f"Debug: FONTCONFIG_FILE environment variable set to {config_path}")

#     # Step 5: Verify the setup by listing the fonts recognized by Fontconfig
#     result = subprocess.run(['fc-list'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
#     print("Debug: Fontconfig available fonts after setup:")
#     print(result.stdout.decode())
    
#     # Step 6: Check if any errors were reported
#     if result.stderr:
#         print("Debug: Fontconfig error:")
#         print(result.stderr.decode())

#     return temp_dir

def verify_fontconfig():
    result = subprocess.run(['fc-list'], stdout=subprocess.PIPE)
    print(f"Debug: Fontconfig available fonts:\n{result.stdout.decode()}")
